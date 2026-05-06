"""
Adhikar-Aina | config.py

Central configuration — all paths, model name, token.
# DATABRICKS REMOVED: all dbfs:/ and workspace:/ paths replaced with local relative paths
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load root .env (two levels up from adhikar_local/)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=False)

BASE_DIR  = Path(__file__).parent
DATA_DIR  = BASE_DIR / "data"
CERTS_DIR = BASE_DIR / "certificates"

# ── Input data ────────────────────────────────────────────────────────────────
SCHEMES_CSV = BASE_DIR.parent / "WEBSITE" / "data" / "updated_data.csv"

# ── Storage (created automatically on first run) ──────────────────────────────
DB_PATH          = DATA_DIR / "adhikar.db"
SCHEME_META_PATH = DATA_DIR / "scheme_meta.pkl"   # TF-IDF vectorizer + matrix + scheme dicts

# ── Matching ──────────────────────────────────────────────────────────────────
TOP_N_SCHEMES      = 5
MIN_SEMANTIC_SCORE = 0.05  # cosine similarity floor (TF-IDF scores are lower than neural)

# ── Telegram ──────────────────────────────────────────────────────────────────
# Get token from @BotFather on Telegram, then set as env var or paste below
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")  # <-- FILL IN YOUR TOKEN HERE

# ── Sarvam AI (Indian language translation / TTS / STT) ───────────────────────
# Get key from https://dashboard.sarvam.ai
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")  # <-- FILL IN YOUR KEY HERE
