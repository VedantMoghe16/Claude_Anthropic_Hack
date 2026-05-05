import json
import os
import sqlite3
import sys
import time
import uuid
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

# DATABRICKS REMOVED: from databricks import sql
# Add adhikar_local to path so we can use local matching
_LOCAL_DIR = Path(__file__).parent.parent.parent / "adhikar_local"
if _LOCAL_DIR.exists():
    sys.path.insert(0, str(_LOCAL_DIR))

load_dotenv()

# ENV VARIABLES
# DATABRICKS REMOVED: DATABRICKS_INSTANCE, DATABRICKS_TOKEN, DATABRICKS_JOB_ID
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
OPENAI_TTS_MODEL  = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE  = os.getenv("OPENAI_TTS_VOICE", "alloy")
OPENAI_TTS_URL    = os.getenv("OPENAI_TTS_URL", "https://api.openai.com/v1/audio/speech")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
OPENAI_RESPONSES_URL = os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses")
SARVAM_API_KEY    = os.getenv("SARVAM_API_KEY", "")

LANGUAGE_NAME_BY_CODE = {
    "as":"Assamese","bn":"Bengali","bodo":"Bodo","doi":"Dogri","en":"English",
    "gu":"Gujarati","hi":"Hindi","kn":"Kannada","kok":"Konkani","ks":"Kashmiri",
    "mai":"Maithili","ml":"Malayalam","mni":"Manipuri (Meitei)","mr":"Marathi",
    "ne":"Nepali","or":"Odia","pa":"Punjabi","sa":"Sanskrit","sat":"Santhali",
    "sd":"Sindhi","ta":"Tamil","te":"Telugu","ur":"Urdu",
}

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

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


def infer_bronze_fields_with_gpt(user: Dict[str, Any]) -> Dict[str, Any]:
    fallback = {
        "district": "Satara", "taluka": "Karad", "village": "Umbraj",
        "ward_no": 1, "survey_no": "NA/1",
        "housing_status":  user.get("housing_status")  or "semi_pucca",
        "employment_days": user.get("employment_days") or 0,
        "is_tribal":    user.get("is_tribal")    or False,
        "has_bpl_card": False, "has_electricity": True,
        "has_water_source": True, "data_source": "frontend_gpt_enriched",
    }
    if not OPENAI_API_KEY:
        return fallback
    prompt = (
        "Given this citizen intake JSON, infer missing bronze-layer profile fields for Indian welfare data. "
        "Return strict JSON object only with keys: district, taluka, village, ward_no, survey_no, "
        "housing_status, employment_days, is_tribal, has_bpl_card, has_electricity, has_water_source, data_source. "
        f"Input JSON: {json.dumps(user)}"
    )
    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": OPENAI_CHAT_MODEL,
                "input": [
                    {"role":"system","content":[{"type":"input_text","text":"You are a strict JSON generator for welfare profile normalization."}]},
                    {"role":"user","content":[{"type":"input_text","text":prompt}]},
                ],
                "text": {"format": {"type": "json_object"}},
            },
            timeout=25,
        )
        response.raise_for_status()
        text   = _extract_response_text(response.json())
        parsed = json.loads(text) if text else {}
        if isinstance(parsed, dict):
            return {**fallback, **parsed}
    except Exception:
        pass
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

    # Try Sarvam first (supports Indian languages natively)
    if lang != "en":
        wav_bytes = _sarvam_tts(text, lang)
        if wav_bytes:
            return Response(content=wav_bytes, media_type="audio/wav")

    # Fallback to OpenAI TTS
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="No TTS provider configured (set SARVAM_API_KEY or OPENAI_API_KEY)")
    language_name = LANGUAGE_NAME_BY_CODE.get(lang, "English")
    response = requests.post(
        OPENAI_TTS_URL,
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": OPENAI_TTS_MODEL, "voice": OPENAI_TTS_VOICE,
              "input": f"Speak this in {language_name}: {text}", "format": "mp3"},
        timeout=45,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"OpenAI TTS failed: {response.text}")
    return Response(content=response.content, media_type="audio/mpeg")


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

        # Fallback to OpenAI Whisper
        if not OPENAI_API_KEY or openai_client is None:
            raise HTTPException(status_code=500, detail="No STT provider configured")
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=(file.filename or "audio.wav", audio_content, file.content_type or "audio/wav"),
            response_format="json",
            timeout=45.0,
        )
        text = transcript.text.strip() if transcript.text else ""
        return {"ok": True, "text": text, "transcript": text}
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


def _build_certificate_html(cert_data: Dict[str, Any]) -> str:
    lang = (cert_data.get("language","en") or "en").lower()
    if lang not in CERTIFICATE_TRANSLATIONS:
        lang = "en"
    t       = CERTIFICATE_TRANSLATIONS[lang]
    citizen = cert_data["citizen_profile"]
    elig    = cert_data["eligibility_criteria"]

    reasons = []
    if elig.get("income_bracket"):    reasons.append(f"Income Bracket: {elig['income_bracket']}")
    if elig.get("land_category"):     reasons.append(f"Land Category: {elig['land_category']}")
    if elig.get("occupation_category"): reasons.append(f"Occupation: {elig['occupation_category']}")
    elig_text = "</li><li>".join(reasons) if reasons else "Meets scheme eligibility criteria"

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
body{{font-family:Arial,sans-serif;line-height:1.6;color:#333;max-width:900px;margin:0 auto}}
.header{{text-align:center;border-bottom:3px solid #16a34a;padding:20px 0;margin-bottom:20px}}
.header h1{{color:#16a34a;margin:0;font-size:28px}}
.section{{margin:20px 0;padding:15px;background:#f9fafb;border-left:4px solid #16a34a;border-radius:4px}}
.section h2{{color:#16a34a;margin-top:0}}
.legal-section{{background:#fef3c7;border-left:4px solid #f59e0b;padding:15px;border-radius:4px;margin:20px 0}}
.footer{{margin-top:30px;padding-top:20px;border-top:1px solid #ddd;text-align:center;color:#666;font-size:12px}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}th,td{{padding:10px;text-align:left;border:1px solid #ddd}}
th{{background:#16a34a;color:white}}
</style></head><body>
<div class="header"><h1>{t['title']}</h1><p>{t['subtitle']}</p></div>
<div class="section"><h2>✅ {t['eligible']}</h2>
<p><strong>{t['certifies']}</strong></p>
<p><strong>{t['citizen_id']}:</strong> {cert_data['citizen_id']} &nbsp;|&nbsp;
<strong>{t['scheme_name']}:</strong> {cert_data['scheme_name']}</p>
<p><strong>{t['district']}:</strong> {citizen.get('district','N/A')} &nbsp;|&nbsp;
<strong>{t['status']}:</strong> <span style="color:#16a34a;font-weight:bold">{t['eligible_status']}</span></p>
</div>
<div class="section"><h2>📋 {t['why_eligible']}</h2>
<p><strong>{t['meet_criteria']}</strong></p><ul><li>{elig_text}</li></ul></div>
<div class="section"><h2>📄 {t['overview']}</h2>
<p><strong>{cert_data['scheme_name']}</strong></p><p>{cert_data['scheme_description']}</p></div>
<div class="legal-section"><h2>⚖️ {t['legal_rights']}</h2>
<p>You have the right to appeal, file RTI, seek free legal aid (DLSA: 1800-233-4415), and approach Lokayukta for corruption.
If benefits are denied: request written explanation within 7 days, escalate to District Collector, file in Consumer Court if needed.</p></div>
<div class="footer">
<p>{t['footer_line1']}</p><p>{t['footer_line2']}</p><p>{t['footer_line3']}</p>
<p>Date: {cert_data['generated_date']} | Certificate ID: {cert_data['certificate_id']}</p>
</div></body></html>"""
