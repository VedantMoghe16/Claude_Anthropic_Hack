"""
Adhikar-Aina | ingest.py

Replaces: 01_bronze_citizens.py + 02_silver_processing.py + CSV loading from 03_schemes_engine.py
# DATABRICKS REMOVED: SparkSession, Delta tables, dbutils replaced with pandas + SQLite
# DATABRICKS REMOVED: spark.read.csv → pandas.read_csv
# DATABRICKS REMOVED: spark.createDataFrame → SQLite INSERT
# DATABRICKS REMOVED: df.write.format("delta").saveAsTable → sqlite3

Creates SQLite tables:
- citizens : 1,000 synthetic citizen records with silver-layer derived features
- schemes  : parsed government schemes from updated_data.csv
"""

from __future__ import annotations

import hashlib
import random
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import SCHEMES_CSV, DB_PATH, DATA_DIR

# ── Citizens constants (from 01_bronze_citizens.py) ──────────────────────────

FIRST_NAMES = ["Aarav","Vihaan","Reyansh","Ishaan","Aanya","Saanvi","Diya","Anaya",
               "Rohan","Meera","Nikhil","Pooja","Kavya","Rahul","Sneha","Arjun",
               "Priya","Kiran","Sunita","Mahesh"]
LAST_NAMES  = ["Patil","Shinde","Jadhav","Pawar","Kulkarni","Deshmukh","More","Chavan","Kale","Joshi"]
DISTRICTS   = ["Pune","Satara","Nashik","Kolhapur","Nagpur","Solapur","Ahmednagar"]


def _w(pairs: list) -> str:
    return random.choices([v for v, _ in pairs], weights=[w for _, w in pairs], k=1)[0]


def _generate_citizen(index: int) -> dict:
    """Mirrors 01_bronze_citizens._generate_record + 02_silver_processing features."""
    occupation = _w([("farmer",0.32),("worker",0.24),("entrepreneur",0.12),
                     ("student",0.16),("unemployed",0.16)])
    if occupation == "farmer":
        income = round(random.uniform(40000, 850000), 2)
        land   = round(random.uniform(0.1, 10.0), 2)
    elif occupation == "worker":
        income = round(random.uniform(30000, 600000), 2)
        land   = round(random.uniform(0.0, 1.2), 2)
    elif occupation == "entrepreneur":
        income = round(random.uniform(150000, 2000000), 2)
        land   = round(random.uniform(0.0, 3.0), 2)
    elif occupation == "student":
        income = round(random.uniform(0, 250000), 2)
        land   = round(random.uniform(0.0, 0.8), 2)
    else:
        income = round(random.uniform(0, 200000), 2)
        land   = round(random.uniform(0.0, 0.5), 2)

    caste    = _w([("OBC",0.42),("GEN",0.32),("SC",0.18),("ST",0.08)])
    age      = random.randint(18, 80)
    gender   = _w([("Male",0.52),("Female",0.48)])
    children = age >= 21 and random.random() < 0.58
    girl     = children and random.random() < 0.47
    hhsize   = random.randint(1, 8)
    bpl      = bool((income < 120000 and hhsize >= 4) or (income < 80000))
    housing  = (_w([("kutcha",0.50),("semi_pucca",0.35),("pucca",0.15)]) if bpl
                else _w([("kutcha",0.12),("semi_pucca",0.36),("pucca",0.52)]))
    emp_days = random.randint(0, 365)

    # Silver-layer derived features (from 02_silver_processing.py)
    income_bracket = ("EWS" if income < 100000 else
                      "LIG" if income < 300000 else
                      "MIG" if income < 1000000 else "HIG")
    land_category  = ("marginal" if land < 1 else
                      "small"    if land < 2 else
                      "medium"   if land < 5 else "large")
    tags = ",".join(filter(None, [
        occupation,
        "low_income"  if income < 300000 else "",
        "agriculture" if occupation == "farmer" else "",
        "education"   if occupation == "student" else "",
        "welfare"     if occupation == "unemployed" else "",
        "girl_child"  if girl else "",
    ]))

    aadhar = str(random.randint(100000000000, 999999999999))

    return {
        "citizen_id":          f"CIT-{index:04d}",
        "aadhar":              aadhar,
        "name":                f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "district":            random.choice(DISTRICTS),
        "state":               "Maharashtra",
        "age":                 age,
        "gender":              gender,
        "caste_category":      caste,
        "annual_income":       income,
        "occupation":          occupation,
        "land_acres":          land,
        "has_girl_child":      int(girl),
        "household_size":      hhsize,
        "has_bpl_card":        int(bpl),
        "housing_status":      housing,
        "employment_days":     emp_days,
        "income_bracket":      income_bracket,
        "land_category":       land_category,
        "occupation_category": occupation,
        "citizen_tags":        tags,
        "created_at":          datetime.utcnow().isoformat(),
    }


# ── Scheme parsing helpers (ported from 03_schemes_engine.py) ─────────────────

def _parse_income_max(text: str) -> Optional[float]:
    # DATABRICKS REMOVED: Spark UDF → plain Python function
    if not text:
        return None
    tl = text.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*lakh", tl)
    if m:
        return float(m.group(1)) * 100_000.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*l\b", tl)
    if m:
        return float(m.group(1)) * 100_000.0
    m = re.search(r"(\d{5,7})", tl)
    if m:
        return float(m.group(1))
    return None


def _parse_max_land(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:acre|acres)", text.lower())
    return float(m.group(1)) if m else None


def _parse_occupation(text: str) -> str:
    if not text:
        return "any"
    tl = text.lower()
    if any(t in tl for t in ["farmer","agri","kisan","cultivator"]): return "farmer"
    if any(t in tl for t in ["student","scholar"]):                   return "student"
    if any(t in tl for t in ["artisan","craft","vishwakarma"]):       return "artisan"
    if any(t in tl for t in ["unemployed","jobless"]):                return "unemployed"
    if any(t in tl for t in ["labor","labour","worker"]):             return "laborer"
    return "any"


def _parse_category(text: str) -> str:
    if not text:
        return "ANY"
    tl = text.lower()
    if "sc"  in tl:                         return "SC"
    if "st"  in tl or "tribal" in tl:       return "ST"
    if "obc" in tl:                         return "OBC"
    if "general" in tl or " gen " in tl:    return "GEN"
    return "ANY"


def _parse_scheme_row(row: pd.Series) -> dict:
    elig = str(row.get("eligibility","") or "")
    tags = str(row.get("tags","") or "")
    cat  = str(row.get("schemeCategory","") or "")
    combined = f"{elig} {tags} {cat}"

    max_inc  = _parse_income_max(combined)  or 100_000_000.0
    max_land = _parse_max_land(combined)    or 999_999.0
    occ      = _parse_occupation(combined)
    category = _parse_category(combined)
    benefit  = str(row.get("benefits","") or "Benefit details not provided").strip()[:1000]
    level    = str(row.get("level","")    or "").strip()
    ministry = f"{level} Government — {cat.split(',')[0].strip()}" if level else "Government of India"
    name     = str(row.get("scheme_name","") or "").strip()

    return {
        "scheme_id":        "SCH-" + hashlib.sha256(name.encode()).hexdigest()[:10].upper(),
        "scheme_name":      name,
        "min_income":       0.0,
        "max_income":       max_inc,
        "occupation":       occ,
        "max_land":         max_land,
        "category":         category,
        "benefit":          benefit,
        "eligibility_text": elig[:2000],
        "details":          str(row.get("details","") or "")[:2000],
        "scheme_category":  cat,
        "ministry":         ministry,
        "level":            level,
        "tags":             str(row.get("tags","") or ""),
    }


# ── SQLite schema ─────────────────────────────────────────────────────────────

_CREATE_CITIZENS = """
CREATE TABLE IF NOT EXISTS citizens (
    citizen_id          TEXT PRIMARY KEY,
    aadhar              TEXT UNIQUE,
    name                TEXT,
    district            TEXT,
    state               TEXT,
    age                 INTEGER,
    gender              TEXT,
    caste_category      TEXT,
    annual_income       REAL,
    occupation          TEXT,
    land_acres          REAL,
    has_girl_child      INTEGER,
    household_size      INTEGER,
    has_bpl_card        INTEGER,
    housing_status      TEXT,
    employment_days     INTEGER,
    income_bracket      TEXT,
    land_category       TEXT,
    occupation_category TEXT,
    citizen_tags        TEXT,
    created_at          TEXT
)
"""

_CREATE_SCHEMES = """
CREATE TABLE IF NOT EXISTS schemes (
    scheme_id        TEXT PRIMARY KEY,
    scheme_name      TEXT UNIQUE,
    min_income       REAL,
    max_income       REAL,
    occupation       TEXT,
    max_land         REAL,
    category         TEXT,
    benefit          TEXT,
    eligibility_text TEXT,
    details          TEXT,
    scheme_category  TEXT,
    ministry         TEXT,
    level            TEXT,
    tags             TEXT
)
"""


def setup_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(_CREATE_CITIZENS)
        conn.execute(_CREATE_SCHEMES)
        conn.commit()


def ingest_schemes(csv_path: Path = SCHEMES_CSV) -> int:
    """Load CSV → parse eligibility rules → write to SQLite schemes table."""
    # DATABRICKS REMOVED: spark.read.csv → pandas.read_csv
    df = pd.read_csv(str(csv_path), on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]

    records, seen = [], set()
    for _, row in df.iterrows():
        parsed = _parse_scheme_row(row)
        if not parsed["scheme_name"] or parsed["scheme_name"] in seen:
            continue
        seen.add(parsed["scheme_name"])
        records.append(parsed)

    # Baseline schemes (from 03_schemes_engine.py SCH-BASE-* rows)
    baselines = [
        ("SCH-BASE-001","Small Farmer Income Support",         0.0, 500000.0,"farmer",  2.0,"ANY","Direct assistance up to Rs 6,000/year","Small and marginal farmers","PM-KISAN style support","Agriculture,Rural & Environment","Central Government","Central","farmer,agriculture,income support"),
        ("SCH-BASE-002","OBC Agri Equipment Subsidy",          0.0, 400000.0,"farmer",  3.0,"OBC","Subsidy for farm equipment purchase","OBC farmers with land up to 3 acres","Equipment subsidy for OBC agricultural workers","Agriculture,Rural & Environment","State Government","State","farmer,obc,equipment,subsidy"),
        ("SCH-BASE-003","Universal Rural Livelihood Grant",    0.0, 350000.0,"any",     5.0,"ANY","Livelihood support for rural households","Rural households with low income","Integrated livelihood support program","Social welfare & Empowerment","Central Government","Central","rural,livelihood,welfare"),
    ]
    for b in baselines:
        if b[1] not in seen:
            records.append(dict(zip(
                ["scheme_id","scheme_name","min_income","max_income","occupation","max_land",
                 "category","benefit","eligibility_text","details","scheme_category","ministry","level","tags"],
                b
            )))

    # DATABRICKS REMOVED: Delta table write → SQLite INSERT
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("DELETE FROM schemes")
        conn.executemany(
            "INSERT OR REPLACE INTO schemes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(r["scheme_id"],r["scheme_name"],r["min_income"],r["max_income"],r["occupation"],
              r["max_land"],r["category"],r["benefit"],r["eligibility_text"],r["details"],
              r["scheme_category"],r["ministry"],r["level"],r["tags"]) for r in records]
        )
        conn.commit()
    return len(records)


def generate_citizens(n: int = 5000, seed: int = 42) -> int:
    """Generate all-India citizen dataset (16 states, state-proportional) → SQLite."""
    # DATABRICKS REMOVED: SparkSession.createDataFrame + Delta table → SQLite INSERT
    from dataset import generate_all
    records = generate_all(n=n, seed=seed)

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("DELETE FROM citizens")
        conn.executemany(
            "INSERT OR REPLACE INTO citizens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(r["citizen_id"],r["aadhar"],r["name"],r["district"],r["state"],r["age"],r["gender"],
              r["caste_category"],r["annual_income"],r["occupation"],r["land_acres"],r["has_girl_child"],
              r["household_size"],r["has_bpl_card"],r["housing_status"],r["employment_days"],
              r["income_bracket"],r["land_category"],r["occupation_category"],r["citizen_tags"],
              r["created_at"]) for r in records]
        )
        conn.commit()
    return len(records)


def run() -> None:
    print("Setting up SQLite database...")
    setup_database()
    print(f"Loading schemes from {SCHEMES_CSV}...")
    n_schemes = ingest_schemes()
    print(f"  {n_schemes} schemes ingested")
    print("Generating all-India citizen dataset (5,000 citizens across 16 states)...")
    n_citizens = generate_citizens(5000)
    print(f"  {n_citizens} citizens generated")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    run()
