"""
Adhikar-Aina | embed_schemes.py

Builds a TF-IDF semantic index over all scheme texts.
No PyTorch, no sentence-transformers required.

Saves to SCHEME_META_PATH (pickle):
  {
    "scheme_dicts":  list[dict],        # full scheme records
    "vectorizer":    TfidfVectorizer,   # fitted sklearn vectorizer
    "tfidf_matrix":  scipy.sparse,      # (n_schemes × n_features)
  }
"""

from __future__ import annotations

import pickle
import sqlite3
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH, SCHEME_META_PATH, DATA_DIR


def _scheme_text(row: dict) -> str:
    """
    Combine all scheme text fields into one searchable string.
    Repeating scheme_name + tags boosts their weight in TF-IDF.
    """
    parts = [
        row.get("scheme_name", ""),
        row.get("scheme_name", ""),          # repeat for higher TF weight
        row.get("eligibility_text", ""),
        row.get("tags", ""),
        row.get("tags", ""),                 # repeat tags
        row.get("scheme_category", ""),
        row.get("details", "")[:300],        # limit details length
    ]
    return " ".join(p for p in parts if p).strip().lower()


def build_index() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM schemes").fetchall()

    if not rows:
        raise RuntimeError("No schemes found. Run `python ingest.py` first.")

    scheme_dicts = [dict(r) for r in rows]
    texts = [_scheme_text(r) for r in scheme_dicts]

    print(f"Building TF-IDF index over {len(texts)} schemes...")
    vectorizer = TfidfVectorizer(
        max_features=20_000,
        ngram_range=(1, 2),       # unigrams + bigrams
        min_df=1,
        sublinear_tf=True,        # log(1+tf) — reduces weight of very common terms
        strip_accents="unicode",
        analyzer="word",
        token_pattern=r"(?u)\b\w+\b",
    )
    tfidf_matrix = vectorizer.fit_transform(texts)  # sparse matrix (n × features)

    meta = {
        "scheme_dicts": scheme_dicts,
        "vectorizer":   vectorizer,
        "tfidf_matrix": tfidf_matrix,
    }
    with open(SCHEME_META_PATH, "wb") as f:
        pickle.dump(meta, f, protocol=4)

    print(f"Saved → {SCHEME_META_PATH}")
    print(f"  Schemes : {tfidf_matrix.shape[0]}")
    print(f"  Features: {tfidf_matrix.shape[1]}")


if __name__ == "__main__":
    build_index()
