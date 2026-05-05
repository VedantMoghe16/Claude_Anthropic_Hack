"""
Adhikar-Aina | match.py

Replaces: 04_eligibility_matching.py
# DATABRICKS REMOVED: Spark crossJoin + broadcast replaced with pandas boolean mask
# DATABRICKS REMOVED: Delta table reads replaced with SQLite + pandas

Matching strategy (two-stage):
  1. Rule-based filter  — income range, land cap, occupation, caste category (pandas)
  2. Semantic re-rank   — TF-IDF cosine similarity (sklearn) over the filtered set
"""

from __future__ import annotations

import pickle
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH, SCHEME_META_PATH, TOP_N_SCHEMES

# ── Lazy-loaded globals ───────────────────────────────────────────────────────

_meta:         Optional[List[Dict]]  = None
_vectorizer                          = None
_tfidf_matrix                        = None


def _load_index():
    global _meta, _vectorizer, _tfidf_matrix
    if _meta is not None:
        return _meta, _vectorizer, _tfidf_matrix
    if not Path(SCHEME_META_PATH).exists():
        raise FileNotFoundError(
            f"Index not found at {SCHEME_META_PATH}. "
            "Run `python pipeline.py --setup` first."
        )
    with open(SCHEME_META_PATH, "rb") as f:
        data = pickle.load(f)
    _meta         = data["scheme_dicts"]
    _vectorizer   = data["vectorizer"]
    _tfidf_matrix = data["tfidf_matrix"]
    return _meta, _vectorizer, _tfidf_matrix


# ── Citizen lookup ────────────────────────────────────────────────────────────

def get_citizen(aadhar_or_id: str) -> Optional[Dict[str, Any]]:
    """Look up citizen by 12-digit Aadhaar or citizen_id."""
    # DATABRICKS REMOVED: spark.table("silver_citizens") → SQLite
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM citizens WHERE aadhar=? OR citizen_id=? LIMIT 1",
            (str(aadhar_or_id), str(aadhar_or_id))
        ).fetchone()
    return dict(row) if row else None


def _load_schemes_df() -> pd.DataFrame:
    # DATABRICKS REMOVED: spark.table("schemes_clean") → pandas.read_sql
    with sqlite3.connect(str(DB_PATH)) as conn:
        return pd.read_sql("SELECT * FROM schemes", conn)


# ── Stage 1: rule-based filter ────────────────────────────────────────────────

def rule_match(citizen: Dict[str, Any], schemes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Deterministic eligibility filter — mirrors 04_eligibility_matching.py logic.
    Returns only schemes where ALL conditions pass.
    """
    income = float(citizen.get("annual_income", 0) or 0)
    land   = float(citizen.get("land_acres",    0) or 0)
    occ    = str(citizen.get("occupation_category",
                             citizen.get("occupation","")) or "").lower().strip()
    cat    = str(citizen.get("caste_category", "GEN") or "GEN").upper().strip()

    mask = (
        (schemes_df["min_income"].fillna(0)      <= income) &
        (schemes_df["max_income"].fillna(1e8)    >= income) &
        (schemes_df["max_land"].fillna(999_999)  >= land)   &
        (
            (schemes_df["occupation"].str.lower().fillna("any") == "any") |
            (schemes_df["occupation"].str.lower().fillna("any") == occ)
        ) &
        (
            (schemes_df["category"].str.upper().fillna("ANY") == "ANY") |
            (schemes_df["category"].str.upper().fillna("ANY") == cat)
        )
    )
    return schemes_df[mask].copy()


# ── Stage 2: TF-IDF semantic re-ranking ──────────────────────────────────────

def _citizen_query_text(citizen: Dict[str, Any]) -> str:
    """Build a query string from the citizen's profile for TF-IDF matching."""
    parts = [
        str(citizen.get("occupation", "")),
        str(citizen.get("occupation_category", "")),
        str(citizen.get("caste_category", "")),
        str(citizen.get("income_bracket", "")),
        str(citizen.get("land_category", "")),
        str(citizen.get("citizen_tags", "")),
        str(citizen.get("district", "")),
        str(citizen.get("state", "")),
    ]
    return " ".join(p for p in parts if p).strip().lower()


def _semantic_scores(citizen: Dict[str, Any],
                     scheme_ids: List[str]) -> Dict[str, float]:
    """
    Compute TF-IDF cosine similarity between citizen profile and every scheme.
    Returns {scheme_id: score} for the requested scheme_ids.
    """
    try:
        meta, vectorizer, tfidf_matrix = _load_index()
    except Exception:
        return {sid: 0.0 for sid in scheme_ids}

    query_text = _citizen_query_text(citizen)
    query_vec  = vectorizer.transform([query_text])          # sparse (1 × features)
    sims       = cosine_similarity(query_vec, tfidf_matrix)  # dense (1 × n_schemes)
    sims_flat  = sims[0]                                     # n_schemes array

    # Build scheme_id → score mapping from the full index
    id_to_score = {meta[i]["scheme_id"]: float(sims_flat[i]) for i in range(len(meta))}
    return {sid: id_to_score.get(sid, 0.0) for sid in scheme_ids}


# ── Public API ────────────────────────────────────────────────────────────────

def match_citizen(aadhar_or_id: str, top_n: int = TOP_N_SCHEMES) -> List[Dict[str, Any]]:
    """Full pipeline for a stored citizen (Aadhaar/citizen_id lookup → match)."""
    citizen = get_citizen(aadhar_or_id)
    if citizen is None:
        return []
    return match_profile(citizen, top_n=top_n)


def match_profile(profile: Dict[str, Any],
                  top_n: int = TOP_N_SCHEMES) -> List[Dict[str, Any]]:
    """
    Match any profile dict (no SQLite lookup).
    Used by FastAPI backend and test scripts.
    """
    schemes_df = _load_schemes_df()
    matched    = rule_match(profile, schemes_df)

    if matched.empty:
        return []

    # Semantic re-rank
    scores = _semantic_scores(profile, matched["scheme_id"].tolist())
    matched = matched.copy()
    matched["_score"] = matched["scheme_id"].map(scores).fillna(0.0)
    matched = matched.sort_values("_score", ascending=False)

    results = []
    for _, row in matched.head(top_n).iterrows():
        results.append({
            "scheme_id":        row["scheme_id"],
            "scheme_name":      row["scheme_name"],
            "benefit":          row["benefit"],
            "ministry":         row.get("ministry", "Government"),
            "scheme_category":  row.get("scheme_category", ""),
            "eligibility_text": row.get("eligibility_text", ""),
            "level":            row.get("level", ""),
            "tags":             row.get("tags", ""),
        })
    return results
