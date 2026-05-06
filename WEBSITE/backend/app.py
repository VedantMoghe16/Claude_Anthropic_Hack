import json
import os
import sqlite3
import sys
import time
import uuid
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# DATABRICKS REMOVED: from databricks import sql
# Add adhikar_local to path so we can use local matching
_LOCAL_DIR = Path(__file__).parent.parent.parent / "adhikar_local"
if _LOCAL_DIR.exists():
    sys.path.insert(0, str(_LOCAL_DIR))

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)

# ENV VARIABLES
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SARVAM_API_KEY    = os.getenv("SARVAM_API_KEY", "")

LANGUAGE_NAME_BY_CODE = {
    "as":"Assamese","bn":"Bengali","bodo":"Bodo","doi":"Dogri","en":"English",
    "gu":"Gujarati","hi":"Hindi","kn":"Kannada","kok":"Konkani","ks":"Kashmiri",
    "mai":"Maithili","ml":"Malayalam","mni":"Manipuri (Meitei)","mr":"Marathi",
    "ne":"Nepali","or":"Odia","pa":"Punjabi","sa":"Sanskrit","sat":"Santhali",
    "sd":"Sindhi","ta":"Tamil","te":"Telugu","ur":"Urdu",
}

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# ── Local database path ───────────────────────────────────────────────────────

def _db_path() -> str:
    # DATABRICKS REMOVED: Databricks SQL connector → SQLite
    # Prefer adhikar_local DB if it exists, fall back to a local fallback
    candidates = [
        _LOCAL_DIR / "data" / "adhikar.db",
        Path(__file__).parent / "adhikar.db",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # If neither exists, create a minimal one next to app.py
    path = str(Path(__file__).parent / "adhikar.db")
    _ensure_local_db(path)
    return path


def _ensure_local_db(path: str) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS citizens (
                citizen_id TEXT PRIMARY KEY, aadhar TEXT UNIQUE, name TEXT,
                district TEXT, state TEXT, age INTEGER, gender TEXT,
                caste_category TEXT, annual_income REAL, occupation TEXT,
                land_acres REAL, has_girl_child INTEGER, household_size INTEGER,
                has_bpl_card INTEGER, housing_status TEXT, employment_days INTEGER,
                income_bracket TEXT, land_category TEXT, occupation_category TEXT,
                citizen_tags TEXT, created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telegram_user_mapping (
                citizen_id TEXT, telegram_chat_id TEXT, telegram_username TEXT,
                updated_at TEXT, PRIMARY KEY (citizen_id)
            )
        """)
        conn.commit()


# ── Helper functions ──────────────────────────────────────────────────────────

def _normalize_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"true","1","yes","y"}: return True
    if text in {"false","0","no","n"}: return False
    return default


def _income_bracket(income: float) -> str:
    if income < 50000:  return "EWS"
    if income < 100000: return "LIG"
    if income < 200000: return "MIG"
    return "HIG"


def _land_category(land_acres: float) -> str:
    if land_acres < 1.0: return "marginal"
    if land_acres < 2.5: return "small"
    if land_acres < 5.0: return "medium"
    return "large"


def _occupation_category(occupation: str) -> str:
    text = str(occupation or "").strip().lower()
    if any(t in text for t in ["farmer","farm","agri","cultivator"]): return "farmer"
    if any(t in text for t in ["student","school","college"]):        return "student"
    if any(t in text for t in ["business","shop","trader","startup"]): return "entrepreneur"
    if any(t in text for t in ["worker","labour","daily"]):           return "worker"
    return "unemployed"


def build_eligibility_explanation(user: Dict[str, Any]) -> Dict[str, str]:
    income = float(user.get("annual_income", user.get("income", 0)) or 0)
    land   = float(user.get("land_acres", 0) or 0)
    occ    = str(user.get("occupation",""))
    return {
        "income_bracket":      _income_bracket(income),
        "occupation_category": _occupation_category(occ),
        "land_category":       _land_category(land),
    }


def _extract_response_text(data: Dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    for item in data.get("output", []):
        text = item.get("text") if isinstance(item, dict) else None
        if isinstance(text, str) and text.strip():
            return text.strip()
        for ci in item.get("content",[]) if isinstance(item,dict) else []:
            if isinstance(ci, dict):
                inner = ci.get("text") or ci.get("output_text")
                if isinstance(inner, str) and inner.strip():
                    return inner.strip()
    return ""


# ── Citizen / Telegram data layer (SQLite) ────────────────────────────────────

def retrieve_citizen_from_silver(citizen_id: str) -> Optional[Dict[str, Any]]:
    """DATABRICKS REMOVED: SELECT FROM silver_citizens → SQLite query."""
    try:
        with sqlite3.connect(_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM citizens WHERE citizen_id=? OR aadhar=? LIMIT 1",
                (citizen_id, citizen_id)
            ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"SQLite lookup error: {e}")
        return None


def append_user_to_bronze(user: Dict[str, Any]) -> str:
    """DATABRICKS REMOVED: INSERT INTO bronze_citizens → SQLite INSERT."""
    citizen_id   = str(user.get("citizen_id") or f"TEST-{uuid.uuid4().hex[:6]}").strip()
    income_value = float(user.get("income", user.get("annual_income", 0)) or 0)
    caste_value  = str(user.get("caste_category") or user.get("category") or "GEN").upper()
    occ          = str(user.get("occupation","") or "")
    land         = float(user.get("land_acres", 0) or 0)

    record = {
        "citizen_id":          citizen_id,
        "aadhar":              str(user.get("aadhar","")) or citizen_id,
        "name":                str(user.get("name","") or "Unknown"),
        "district":            str(user.get("district","Pune")),
        "state":               str(user.get("state","Maharashtra")),
        "age":                 int(user.get("age", 30) or 30),
        "gender":              str(user.get("gender","Unknown")),
        "caste_category":      caste_value,
        "annual_income":       income_value,
        "occupation":          occ,
        "land_acres":          land,
        "has_girl_child":      int(_normalize_bool(user.get("has_girl_child"))),
        "household_size":      int(user.get("household_size", 4) or 4),
        "has_bpl_card":        int(_normalize_bool(user.get("has_bpl_card"))),
        "housing_status":      str(user.get("housing_status","semi_pucca")),
        "employment_days":     int(user.get("employment_days", 0) or 0),
        "income_bracket":      _income_bracket(income_value),
        "land_category":       _land_category(land),
        "occupation_category": _occupation_category(occ),
        "citizen_tags":        "",
        "created_at":          time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    db = _db_path()
    _ensure_local_db(db)
    with sqlite3.connect(db) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO citizens VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, tuple(record.values()))
        conn.commit()
    return citizen_id


def save_telegram_mapping(citizen_id: str, telegram_chat_id: str,
                           telegram_username: Optional[str] = None) -> None:
    """DATABRICKS REMOVED: MERGE INTO telegram_user_mapping → SQLite INSERT OR REPLACE."""
    db = _db_path()
    _ensure_local_db(db)
    with sqlite3.connect(db) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO telegram_user_mapping
            (citizen_id, telegram_chat_id, telegram_username, updated_at)
            VALUES (?,?,?,?)
        """, (citizen_id, str(telegram_chat_id),
               telegram_username or "",
               time.strftime("%Y-%m-%dT%H:%M:%S")))
        conn.commit()


# ── Matching (local, replaces Databricks job trigger) ─────────────────────────

def run_local_matching(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    DATABRICKS REMOVED: trigger_databricks_job + wait_for_databricks_job
    Replaced with synchronous local match using match.match_profile().
    """
    try:
        from match import match_profile
        profile = {
            "annual_income":       float(user.get("annual_income", user.get("income",0)) or 0),
            "land_acres":          float(user.get("land_acres",0) or 0),
            "occupation_category": _occupation_category(str(user.get("occupation",""))),
            "occupation":          str(user.get("occupation","")),
            "caste_category":      str(user.get("caste_category") or user.get("category","GEN")).upper(),
            "income_bracket":      _income_bracket(float(user.get("annual_income",0) or 0)),
            "land_category":       _land_category(float(user.get("land_acres",0) or 0)),
            "district":            str(user.get("district","Pune")),
            "state":               str(user.get("state","Maharashtra")),
            "citizen_tags":        "",
        }
        return match_profile(profile, top_n=int(user.get("limit",5)))
    except ImportError:
        # adhikar_local not on path; return empty
        print("Warning: adhikar_local not found. Run `python pipeline.py --setup` first.")
        return []
    except Exception as e:
        print(f"Matching error: {e}")
        return []


def infer_bronze_fields_with_claude(user: Dict[str, Any]) -> Dict[str, Any]:
    fallback = {
        "district": "Satara", "taluka": "Karad", "village": "Umbraj",
        "ward_no": 1, "survey_no": "NA/1",
        "housing_status":  user.get("housing_status")  or "semi_pucca",
        "employment_days": user.get("employment_days") or 0,
        "is_tribal":    user.get("is_tribal")    or False,
        "has_bpl_card": False, "has_electricity": True,
        "has_water_source": True, "data_source": "frontend_claude_enriched",
    }
    if not anthropic_client:
        return fallback
    prompt = (
        "Given this citizen intake JSON, infer missing bronze-layer profile fields for Indian welfare data. "
        "Return ONLY a strict JSON object with keys: district, taluka, village, ward_no, survey_no, "
        "housing_status, employment_days, is_tribal, has_bpl_card, has_electricity, has_water_source, data_source. "
        "No explanation, no markdown fences, just the raw JSON object. "
        f"Input JSON: {json.dumps(user)}"
    )
    try:
        message = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {**fallback, **parsed}
    except Exception as e:
        print(f"Claude enrichment error: {e}")
    return fallback


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


class CheckEligibilityRequest(BaseModel):
    citizen_id:       Optional[str]   = None
    income:           Optional[float] = 0
    annual_income:    Optional[float] = None
    occupation:       Optional[str]   = ""
    land_acres:       Optional[float] = 0
    category:         Optional[str]   = "GEN"
    caste_category:   Optional[str]   = None
    has_girl_child:   Optional[bool]  = False
    state:            Optional[str]   = ""
    housing_status:   Optional[str]   = ""
    employment_days:  Optional[int]   = 0
    is_tribal:        Optional[bool]  = False
    limit:            Optional[int]   = 5


class TTSRequest(BaseModel):
    text:     str
    language: Optional[str] = "en"


class TelegramLinkRequest(BaseModel):
    citizen_id:        str
    telegram_chat_id:  str
    telegram_username: Optional[str] = None


@app.post("/check-eligibility")
def check_eligibility(payload: CheckEligibilityRequest):
    user  = payload.dict(exclude_none=True)
    limit = user.pop("limit", 5)
    if "caste_category" not in user and "category" in user:
        user["caste_category"] = user.get("category")
    if "annual_income" not in user:
        user["annual_income"] = user.get("income", 0)

    citizen_id = str(user.get("citizen_id") or "").strip()
    if citizen_id:
        existing = retrieve_citizen_from_silver(citizen_id)
        if existing:
            user = {**existing, **user}
    else:
        citizen_id = f"TEST-{uuid.uuid4().hex[:6]}"
    user["citizen_id"] = citizen_id
    user["limit"]      = limit
    explanation = build_eligibility_explanation(user)

    try:
        citizen_id = append_user_to_bronze(user)
        # DATABRICKS REMOVED: trigger_databricks_job + wait_for_databricks_job
        results = run_local_matching(user)
        return {
            "citizen_id":             citizen_id,
            "run_id":                 None,
            "eligible_schemes":       results,
            "eligibility_explanation": explanation,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {
            "citizen_id":             citizen_id,
            "run_id":                 None,
            "eligible_schemes":       [],
            "eligibility_explanation": explanation,
            "error":                  str(e),
        }


@app.get("/api/citizen/by-aadhaar/{aadhar}")
def get_citizen_by_aadhaar(aadhar: str, limit: int = 5):
    """Look up citizen by 12-digit Aadhaar and return matched schemes. Used by Telegram bot."""
    clean = "".join(c for c in aadhar if c.isdigit())
    if len(clean) != 12:
        raise HTTPException(status_code=400, detail="Aadhaar must be 12 digits")
    try:
        citizen = retrieve_citizen_from_silver(clean)
        if not citizen:
            return {"found": False, "citizen": None, "schemes": []}
        schemes = run_local_matching({**citizen, "limit": limit})
        return {"found": True, "citizen": citizen, "schemes": schemes}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citizen/{citizen_id}")
def get_citizen_info(citizen_id: str):
    """DATABRICKS REMOVED: spark.table("silver_citizens") → SQLite query."""
    try:
        data = retrieve_citizen_from_silver(citizen_id)
        if data:
            return {"found": True,  "citizen": data}
        return {"found": False, "message": f"No record found for citizen ID: {citizen_id}"}
    except Exception as e:
        return {"found": False, "error": str(e)}


@app.get("/api/schemes/{citizen_id}")
def get_citizen_schemes(citizen_id: str, limit: int = 5, offset: int = 0):
    """DATABRICKS REMOVED: SELECT FROM eligibility_results → run_local_matching."""
    try:
        citizen = retrieve_citizen_from_silver(citizen_id)
        if not citizen:
            return {"citizen_id": citizen_id, "total_schemes": 0,
                    "schemes": [], "returned_count": 0, "offset": offset, "limit": limit, "has_more": False}
        all_results = run_local_matching({**citizen, "limit": 100})
        total       = len(all_results)
        paginated   = all_results[offset:offset + limit]
        return {
            "citizen_id":     citizen_id,
            "total_schemes":  total,
            "returned_count": len(paginated),
            "offset":         offset,
            "limit":          limit,
            "has_more":       (offset + limit) < total,
            "schemes":        paginated,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"error": str(e), "schemes": []}


@app.post("/api/link-telegram")
def link_telegram(payload: TelegramLinkRequest):
    try:
        save_telegram_mapping(payload.citizen_id, payload.telegram_chat_id, payload.telegram_username)
        return {"ok": True, "citizen_id": payload.citizen_id,
                "telegram_chat_id": payload.telegram_chat_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RegisterUserRequest(BaseModel):
    name:            Optional[str]   = None
    income:          Optional[float] = 0
    annual_income:   Optional[float] = None
    occupation:      Optional[str]   = ""
    land_acres:      Optional[float] = 0
    category:        Optional[str]   = "GEN"
    caste_category:  Optional[str]   = None
    has_girl_child:  Optional[bool]  = False
    state:           Optional[str]   = ""
    district:        Optional[str]   = ""
    age:             Optional[int]   = 30
    gender:          Optional[str]   = ""
    household_size:  Optional[int]   = 4
    housing_status:  Optional[str]   = ""
    employment_days: Optional[int]   = 0


@app.post("/api/register-user")
def register_user(payload: RegisterUserRequest):
    """Register a new citizen profile. Returns citizen_id."""
    user = payload.dict(exclude_none=True)
    if "annual_income" not in user:
        user["annual_income"] = user.get("income", 0)
    if "caste_category" not in user and "category" in user:
        user["caste_category"] = user["category"]
    try:
        citizen_id = append_user_to_bronze(user)
        return {"ok": True, "citizen_id": citizen_id}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class AddSchemeRequest(BaseModel):
    scheme_id:        Optional[str]   = None
    scheme_name:      str
    min_income:       Optional[float] = 0.0
    max_income:       Optional[float] = 100_000_000.0
    occupation:       Optional[str]   = "any"
    max_land:         Optional[float] = 999_999.0
    category:         Optional[str]   = "ANY"
    benefit:          str
    eligibility_text: Optional[str]   = ""
    details:          Optional[str]   = ""
    scheme_category:  Optional[str]   = ""
    ministry:         Optional[str]   = "Government of India"
    level:            Optional[str]   = "Central"
    tags:             Optional[str]   = ""
    notify:           Optional[bool]  = True


@app.post("/api/add-scheme")
def add_scheme(payload: AddSchemeRequest):
    """Add a new scheme and optionally notify all eligible Telegram-linked citizens."""
    import hashlib, sqlite3

    scheme = payload.dict()
    notify_flag = scheme.pop("notify", True)

    if not scheme.get("scheme_id"):
        scheme["scheme_id"] = "SCH-" + hashlib.sha256(
            scheme["scheme_name"].encode()
        ).hexdigest()[:10].upper()

    db = _db_path()
    _ensure_local_db(db)
    with sqlite3.connect(db) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO schemes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            scheme["scheme_id"], scheme["scheme_name"],
            scheme.get("min_income", 0), scheme.get("max_income", 1e8),
            scheme.get("occupation", "any"), scheme.get("max_land", 1e6),
            scheme.get("category", "ANY"), scheme["benefit"],
            scheme.get("eligibility_text", ""), scheme.get("details", ""),
            scheme.get("scheme_category", ""), scheme.get("ministry", ""),
            scheme.get("level", ""), scheme.get("tags", ""),
        ))
        conn.commit()

    notification_stats = None
    if notify_flag:
        try:
            sys.path.insert(0, str(_LOCAL_DIR))
            from notifier import notify_new_scheme
            notification_stats = notify_new_scheme(scheme)
        except Exception as e:
            notification_stats = {"error": str(e)}

    return {
        "ok":                 True,
        "scheme_id":          scheme["scheme_id"],
        "scheme_name":        scheme["scheme_name"],
        "notification_stats": notification_stats,
    }


@app.get("/api/demo-citizens")
def get_demo_citizens():
    """Return a small set of demo citizens so the UI can show testable Aadhaar numbers."""
    try:
        with sqlite3.connect(_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT citizen_id, aadhar, name, district, state,
                       occupation, annual_income, caste_category, age, gender
                FROM citizens
                WHERE citizen_id IN ('CIT-00001','CIT-00002','CIT-00003','CIT-00004','CIT-00005')
                   OR aadhar = '999999999999'
                LIMIT 6
            """).fetchall()
        demos = [dict(r) for r in rows]
        # Mask Aadhaar: show first 4 + last 4
        for d in demos:
            aadhaar = str(d.get("aadhar", ""))
            d["aadhar_masked"] = aadhaar[:4] + "XXXX" + aadhaar[-4:] if len(aadhaar) == 12 else aadhaar
            d["aadhar_display"] = aadhaar  # full Aadhaar for copy-paste in demo
        return {"ok": True, "demo_citizens": demos}
    except Exception as e:
        return {"ok": False, "error": str(e), "demo_citizens": []}


@app.get("/api/get-results/{citizen_id}")
def get_results(citizen_id: str, limit: int = 5):
    """Return eligibility results for a registered citizen."""
    try:
        citizen = retrieve_citizen_from_silver(citizen_id)
        if not citizen:
            raise HTTPException(status_code=404, detail=f"Citizen {citizen_id} not found")
        schemes = run_local_matching({**citizen, "limit": limit})
        return {
            "citizen_id": citizen_id,
            "schemes":    schemes,
            "total":      len(schemes),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _sarvam_tts(text: str, lang: str) -> Optional[bytes]:
    """Try Sarvam TTS; return WAV bytes or None."""
    if not SARVAM_API_KEY:
        return None
    sarvam_lang_map = {
        "hi":"hi-IN","bn":"bn-IN","te":"te-IN","mr":"mr-IN","ta":"ta-IN",
        "gu":"gu-IN","kn":"kn-IN","ml":"ml-IN","pa":"pa-IN","or":"or-IN",
        "as":"as-IN","ur":"ur-IN","en":"en-IN",
    }
    target = sarvam_lang_map.get(lang.lower(), lang if "-" in lang else "hi-IN")
    try:
        import base64
        resp = requests.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
            json={
                "inputs": [text[:500]],
                "target_language_code": target,
                "speaker": "meera",
                "pitch": 0, "pace": 1.0, "loudness": 1.0,
                "speech_sample_rate": 8000,
                "enable_preprocessing": True,
                "model": "bulbul:v1",
            },
            timeout=30,
        )
        resp.raise_for_status()
        audios = resp.json().get("audios", [])
        if audios:
            return base64.b64decode(audios[0])
    except Exception:
        pass
    return None


@app.post("/api/tts")
def text_to_speech(payload: TTSRequest):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    lang = (payload.language or "en").lower()

    # Use Sarvam for all languages (en-IN for English)
    wav_bytes = _sarvam_tts(text, lang if lang != "en" else "en-IN")
    if wav_bytes:
        return Response(content=wav_bytes, media_type="audio/wav")

    raise HTTPException(
        status_code=503,
        detail="TTS unavailable. Set SARVAM_API_KEY to enable audio. Browser TTS will be used as fallback."
    )


@app.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...), language: str = "hi-IN"):
    try:
        audio_content = await file.read()
        if not audio_content:
            raise HTTPException(status_code=400, detail="Audio file is empty")

        # Try Sarvam STT first
        if SARVAM_API_KEY:
            try:
                sarvam_lang_map = {
                    "hi":"hi-IN","bn":"bn-IN","te":"te-IN","mr":"mr-IN","ta":"ta-IN",
                    "gu":"gu-IN","kn":"kn-IN","ml":"ml-IN","pa":"pa-IN","en":"en-IN",
                }
                target_lang = sarvam_lang_map.get(language.lower(), language if "-" in language else "hi-IN")
                resp = requests.post(
                    "https://api.sarvam.ai/speech-to-text",
                    headers={"api-subscription-key": SARVAM_API_KEY},
                    files={"file": (file.filename or "audio.wav", audio_content, "audio/wav")},
                    data={"language_code": target_lang, "model": "saarika:v1", "with_timestamps": "false"},
                    timeout=30,
                )
                if resp.status_code == 200:
                    transcript = resp.json().get("transcript", "")
                    if transcript:
                        return {"ok": True, "text": transcript, "transcript": transcript}
            except Exception:
                pass

        raise HTTPException(status_code=503, detail="STT unavailable — Sarvam API failed. Set SARVAM_API_KEY.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {e}")


# ── Certificate endpoint (unchanged — generates HTML, no Databricks dependency) ──

CERTIFICATE_TRANSLATIONS = {
    "hi": {
        "title": "⚖️ अधिकार प्रमाणपत्र", "subtitle": "पात्रता और अधिकार प्रमाणपत्र",
        "subsubtitle": "सरकारी कल्याण योजना लाभ", "cert_id": "प्रमाणपत्र ID",
        "generated": "जारी", "eligible": "पात्रता की पुष्टि",
        "certifies": "यह प्रमाणित करता है कि:", "citizen_id": "नागरिक ID",
        "scheme_name": "योजना का नाम", "district": "जिला",
        "status": "लाभार्थी स्थिति", "eligible_status": "✓ पात्र",
        "why_eligible": "आप पात्र क्यों हैं", "meet_criteria": "आप निम्नलिखित पात्रता मानदंडों को पूरा करते हैं:",
        "overview": "योजना विवरण", "profile_summary": "आपकी प्रोफाइल सारांश",
        "income_bracket": "आय स्तर", "annual_income": "वार्षिक आय",
        "category": "श्रेणी", "occupation": "व्यवसाय",
        "land_holding": "भूमि होल्डिंग्स", "acres": "एकड़",
        "legal_rights": "आपके अधिकार और कानूनी सहायता",
        "footer_line1": "यह अधिकार प्रमाणपत्र सरकारी कल्याण योजनाओं के लिए पात्रता का प्रमाण है।",
        "footer_line2": "प्रामाणिकता के लिए, जारी करने वाले प्राधिकरण के साथ प्रमाणपत्र ID सत्यापित करें।",
        "footer_line3": "द्वारा जेनरेट: अधिकार आइना", "footer_line4": "तारीख: {generated_date} | प्रमाणपत्र ID: {cert_id}",
    },
    "en": {
        "title": "⚖️ ADHIKAR CERTIFICATE", "subtitle": "Certificate of Eligibility & Rights",
        "subsubtitle": "Government Welfare Scheme Benefit", "cert_id": "Certificate ID",
        "generated": "Generated", "eligible": "ELIGIBILITY CONFIRMATION",
        "certifies": "This certifies that:", "citizen_id": "CITIZEN ID",
        "scheme_name": "SCHEME NAME", "district": "DISTRICT",
        "status": "BENEFICIARY STATUS", "eligible_status": "✓ ELIGIBLE",
        "why_eligible": "WHY YOU ARE ELIGIBLE", "meet_criteria": "You meet the following eligibility criteria:",
        "overview": "SCHEME OVERVIEW", "profile_summary": "YOUR PROFILE SUMMARY",
        "income_bracket": "Income Bracket", "annual_income": "Annual Income",
        "category": "Category", "occupation": "Occupation",
        "land_holding": "Land Holdings", "acres": "acres",
        "legal_rights": "YOUR RIGHTS & LEGAL RECOURSE",
        "footer_line1": "This Adhikar Certificate is generated as proof of eligibility for government welfare schemes.",
        "footer_line2": "For authenticity, verify Certificate ID with the issuing authority.",
        "footer_line3": "Generated by: ADHIKAR - Government Welfare Rights Platform",
        "footer_line4": "Date: {generated_date} | Certificate ID: {cert_id}",
    }
}


class AdhikarCertificateRequest(BaseModel):
    citizen_id:          str
    scheme_name:         str
    scheme_description:  str
    language:            Optional[str]       = "en"
    eligibility_criteria: Dict[str, Any]
    citizen_profile:     Dict[str, Any]


@app.post("/api/adhikar-certificate")
def generate_adhikar_certificate(payload: AdhikarCertificateRequest):
    try:
        cert_data = {
            "citizen_id":          payload.citizen_id,
            "scheme_name":         payload.scheme_name,
            "scheme_description":  payload.scheme_description,
            "eligibility_criteria": payload.eligibility_criteria,
            "citizen_profile":     payload.citizen_profile,
            "language":            payload.language or "en",
            "generated_date":      time.strftime("%Y-%m-%d"),
            "certificate_id":      f"ADHIKAR-{payload.citizen_id}-{int(time.time())}",
        }
        html_content = _build_certificate_html(cert_data)
        return {
            "ok":             True,
            "certificate_id": cert_data["certificate_id"],
            "html":           html_content,
            "citizen_id":     payload.citizen_id,
            "scheme_name":    payload.scheme_name,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _sarvam_translate(text: str, lang: str) -> str:
    """Translate text to lang using Sarvam. Falls back to original on any error."""
    if not text or lang in ("en", ""):
        return text
    if not SARVAM_API_KEY:
        return text
    lang_map = {
        "hi":"hi-IN","bn":"bn-IN","mr":"mr-IN","ta":"ta-IN","te":"te-IN",
        "gu":"gu-IN","kn":"kn-IN","ml":"ml-IN","pa":"pa-IN","or":"or-IN",
        "as":"as-IN","ur":"ur-IN",
    }
    target = lang_map.get(lang.lower(), lang if "-" in lang else None)
    if not target:
        return text
    try:
        r = requests.post(
            "https://api.sarvam.ai/translate",
            headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
            json={
                "input": text[:1000], "source_language_code": "en-IN",
                "target_language_code": target, "speaker_gender": "Female",
                "mode": "formal", "model": "mayura:v1", "enable_preprocessing": False,
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("translated_text", text) or text
    except Exception:
        return text


def _build_certificate_html(cert_data: Dict[str, Any]) -> str:
    lang    = (cert_data.get("language", "en") or "en").lower()
    citizen = cert_data["citizen_profile"]
    elig    = cert_data["eligibility_criteria"]

    def T(text: str) -> str:
        return _sarvam_translate(text, lang)

    # Translate dynamic content
    scheme_name  = cert_data["scheme_name"]
    scheme_desc  = T(cert_data["scheme_description"])
    citizen_name = citizen.get("name") or citizen.get("citizen_id", "Citizen")
    district     = citizen.get("district", "N/A")
    category     = citizen.get("caste_category", citizen.get("category", "N/A"))
    occupation   = citizen.get("occupation", citizen.get("occupation_category", "N/A"))
    income_br    = elig.get("income_bracket", citizen.get("income_bracket", "N/A"))
    land_cat     = elig.get("land_category",  citizen.get("land_category",  ""))
    occ_cat      = elig.get("occupation_category", occupation)

    cert_id   = cert_data["certificate_id"]
    gen_date  = cert_data["generated_date"]

    elig_rows = ""
    for label, val in [
        (T("Income Bracket"), income_br),
        (T("Occupation"),     occ_cat),
        (T("Land Category"),  land_cat),
        (T("Category"),       category),
    ]:
        if val and val != "N/A":
            elig_rows += f"<tr><td>{label}</td><td><span class='badge'>✓ {val}</span></td></tr>"

    legal_text = T(
        "You have the right to: (1) Appeal any rejection in writing within 30 days. "
        "(2) File an RTI application under RTI Act 2005. "
        "(3) Seek free legal aid — DLSA Helpline: 1800-233-4415 (toll-free). "
        "(4) Approach the District Collector or Lokayukta if benefits are wrongfully denied. "
        "(5) File a complaint in Consumer Court under Consumer Protection Act 2019."
    )
    warning  = T("If anyone denies your rights — this certificate is legal proof. "
                 "Demand a written explanation within 7 days.")
    claim_en = (
        f"I am {citizen_name}. My Citizen ID is {cert_data['citizen_id']}.\n"
        f"I am legally entitled to '{scheme_name}'.\n"
        f"Please process my application immediately."
    )
    claim = T(claim_en)

    footer_line1 = T("This Adhikar Certificate is official proof of eligibility for government welfare schemes.")
    footer_line2 = T("Generated by ADHIKAR — Sovereign Citizen Rights Platform | Claude Hackathon by Anthropic")

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Georgia', 'Times New Roman', serif; background: #f4f1eb; color: #1a1a2e; }}
  .page {{ max-width: 860px; margin: 24px auto; background: #fff; }}
  .frame-outer {{ border: 3px double #1a3a6b; margin: 14px; padding: 3px; }}
  .frame-inner {{ border: 1px solid #c8a44e; padding: 28px 32px; position: relative; }}
  .corner {{ position: absolute; color: #c8a44e; font-size: 18px; line-height: 1; }}
  .corner-tl {{ top: 6px; left: 8px; }} .corner-tr {{ top: 6px; right: 8px; }}
  .corner-bl {{ bottom: 6px; left: 8px; }} .corner-br {{ bottom: 6px; right: 8px; }}

  /* HEADER */
  .header {{ text-align: center; padding-bottom: 18px; margin-bottom: 0; border-bottom: 2px solid #1a3a6b; }}
  .emblem {{ font-size: 36px; margin-bottom: 4px; }}
  .gov-line {{ font-size: 10px; letter-spacing: 5px; text-transform: uppercase; color: #555; margin-bottom: 6px; }}
  .cert-title {{ font-size: 32px; font-weight: 900; color: #1a3a6b; letter-spacing: 3px; margin: 4px 0 2px; }}
  .cert-subtitle {{ font-size: 12px; color: #c8a44e; font-style: italic; letter-spacing: 1px; }}

  /* CERT ID BANNER */
  .id-banner {{ background: #1a3a6b; color: #fff; text-align: center; padding: 8px 16px;
                font-size: 11px; letter-spacing: 2px; margin: 16px -32px; }}
  .verified {{ display: inline-block; background: #14532d; color: #fff; padding: 2px 10px;
               border-radius: 20px; font-size: 10px; letter-spacing: 1px; font-weight: bold; }}

  /* SECTIONS */
  .section {{ margin: 18px 0; }}
  .section-header {{ background: #1a3a6b; color: #fff; padding: 7px 14px; font-size: 10px;
                     letter-spacing: 2px; text-transform: uppercase; font-weight: bold; font-family: Arial, sans-serif; }}
  .section-body {{ border: 1px solid #dde; border-top: none; padding: 14px 16px; font-size: 13px; line-height: 1.7; }}

  /* INFO GRID */
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }}
  .info-item label {{ display: block; font-size: 9px; text-transform: uppercase; letter-spacing: 1px;
                      color: #888; margin-bottom: 2px; font-family: Arial, sans-serif; }}
  .info-item span {{ font-size: 13px; font-weight: 700; color: #1a1a2e; }}

  /* TABLE */
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{ background: #1a3a6b; color: #fff; padding: 9px 12px; text-align: left;
        font-size: 10px; letter-spacing: 1px; font-family: Arial, sans-serif; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #eee; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f8f9fc; }}
  .badge {{ display: inline-block; background: #14532d; color: #fff; padding: 2px 10px;
            border-radius: 12px; font-size: 10px; font-weight: bold; font-family: Arial, sans-serif; }}

  /* CLAIM SCRIPT */
  .claim-box {{ background: #f8f9fc; border-left: 3px solid #1a3a6b; padding: 14px 16px;
                font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.8;
                white-space: pre-wrap; color: #1a3a6b; }}

  /* LEGAL BOX */
  .legal-box {{ background: #fffbeb; border: 1px solid #c8a44e; padding: 14px 16px; font-size: 12px; line-height: 1.7; }}
  .legal-box strong {{ color: #b45309; }}

  /* FOOTER */
  .footer {{ display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px; align-items: center;
             margin-top: 20px; padding-top: 14px; border-top: 2px solid #1a3a6b; }}
  .footer-left, .footer-right {{ font-size: 9px; color: #888; font-family: Arial, sans-serif; line-height: 1.6; }}
  .footer-right {{ text-align: right; }}
  .seal {{ width: 76px; height: 76px; border: 2px solid #1a3a6b; border-radius: 50%;
           display: flex; flex-direction: column; align-items: center; justify-content: center;
           margin: 0 auto; text-align: center; font-size: 9px; color: #1a3a6b;
           font-weight: bold; letter-spacing: 1px; font-family: Arial, sans-serif; }}
  .seal-icon {{ font-size: 20px; margin-bottom: 2px; }}

  /* WARNING */
  .warning {{ background: #7f1d1d; color: #fff; text-align: center; padding: 10px 20px;
              font-weight: bold; font-size: 12px; letter-spacing: 0.5px; margin-top: 18px;
              font-family: Arial, sans-serif; }}
  @media print {{
    body {{ background: #fff; }}
    .page {{ margin: 0; box-shadow: none; }}
  }}
</style>
</head>
<body>
<div class="page">
  <div class="frame-outer"><div class="frame-inner">
    <span class="corner corner-tl">✦</span><span class="corner corner-tr">✦</span>
    <span class="corner corner-bl">✦</span><span class="corner corner-br">✦</span>

    <div class="header">
      <div class="emblem">⚖</div>
      <div class="gov-line">Government of India &nbsp;·&nbsp; भारत सरकार</div>
      <div class="cert-title">ADHIKAR</div>
      <div class="cert-subtitle">Certificate of Entitlement &amp; Citizen Rights — अधिकार प्रमाणपत्र</div>
    </div>

    <div class="id-banner">
      CERTIFICATE ID: {cert_id} &nbsp;·&nbsp; DATE: {gen_date}
      &nbsp;·&nbsp; <span class="verified">✓ VERIFIED ELIGIBLE</span>
    </div>

    <div class="section">
      <div class="section-header">&#x1F464; {T("Citizen Information")}</div>
      <div class="section-body">
        <div class="info-grid">
          <div class="info-item"><label>{T("Full Name")}</label><span>{citizen_name}</span></div>
          <div class="info-item"><label>{T("Citizen ID")}</label><span>{cert_data['citizen_id']}</span></div>
          <div class="info-item"><label>{T("District")}</label><span>{district}</span></div>
          <div class="info-item"><label>{T("Occupation")}</label><span>{occupation}</span></div>
          <div class="info-item"><label>{T("Category")}</label><span>{category}</span></div>
          <div class="info-item"><label>{T("Income Bracket")}</label><span>{income_br}</span></div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">&#x1F4CB; {T("Scheme Eligibility")}</div>
      <div class="section-body">
        <table>
          <tr><th>{T("Scheme Name")}</th><th>{T("Status")}</th></tr>
          <tr>
            <td><strong>{scheme_name}</strong></td>
            <td><span class="badge">✓ {T("Eligible")}</span></td>
          </tr>
        </table>
      </div>
    </div>

    <div class="section">
      <div class="section-header">&#x2714; {T("Why You Are Eligible")}</div>
      <div class="section-body">
        <table>{elig_rows}</table>
      </div>
    </div>

    <div class="section">
      <div class="section-header">&#x1F4C4; {T("Scheme Overview & Benefits")}</div>
      <div class="section-body">{scheme_desc}</div>
    </div>

    <div class="section">
      <div class="section-header">&#x1F5E3; {T("Claim Script — What to Say to Officials")}</div>
      <div class="section-body"><div class="claim-box">{claim}</div></div>
    </div>

    <div class="section">
      <div class="section-header">&#x2696; {T("Your Legal Rights & Recourse")}</div>
      <div class="section-body">
        <div class="legal-box"><strong>⚖ {T("Know Your Rights")}:</strong><br/>{legal_text}</div>
      </div>
    </div>

    <div class="footer">
      <div class="footer-left">
        {footer_line1}<br/>
        RTI Act 2005 · NSAP · Consumer Protection Act 2019<br/>
        Legal Services Authorities Act 1987
      </div>
      <div class="seal">
        <div class="seal-icon">⚖</div>
        ADHIKAR<br/>VERIFIED
      </div>
      <div class="footer-right">
        {footer_line2}<br/>
        {T("Certificate ID")}: {cert_id}<br/>
        {T("Date")}: {gen_date}
      </div>
    </div>

    <div class="warning">⚖ {warning}</div>

  </div></div>
</div>
</body></html>"""
