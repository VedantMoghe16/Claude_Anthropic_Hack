# ADHIKAR — Local Setup Guide

Citizen rights and government scheme eligibility system running **entirely locally** — no Spark, no Databricks, no cloud dependencies.

## What it does

1. Loads 1,000+ government schemes from `updated_data.csv`
2. Matches a citizen's profile (income, caste, occupation, land) to eligible schemes
3. Generates an **Adhikar Certificate** PDF with:
   - Entitled schemes + benefit amounts
   - Legal Act/Section that guarantees each scheme
   - Hindi + English claim script to use with officials
   - Grievance officer contacts
4. Delivers via Telegram bot or CLI

---

## Installation

```bash
cd adhikar_local
pip install -r requirements.txt
```

---

## One-Time Setup

Downloads the multilingual MiniLM model (~400 MB) and builds the FAISS index:

```bash
python pipeline.py --setup
```

---

## Usage

### CLI Test

```bash
python pipeline.py --aadhar 999999999999
```

Expected output: a PDF certificate in `adhikar_local/certificates/`

### Telegram Bot

1. Get a bot token from **@BotFather** on Telegram.
2. Set the token:
   ```bash
   export TELEGRAM_TOKEN="your-bot-token-here"
   ```
   *Or* edit `config.py` and set `TELEGRAM_TOKEN = "your-token"`.
3. Start the bot:
   ```bash
   python bot.py
   ```
4. Open Telegram, send the bot your 12-digit Aadhaar number.

### Backend API (FastAPI)

```bash
cd ../WEBSITE/backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

The API now uses SQLite instead of Databricks. The `/check-eligibility` endpoint runs matching locally.

---

## Quick Verification

```bash
# Step 1 — build index (one-time, ~2–5 min on first run)
python pipeline.py --setup

# Step 2 — test with fixed demo Aadhaar
python pipeline.py --aadhar 999999999999

# Step 3 — start Telegram bot
export TELEGRAM_TOKEN="your-token"
python bot.py
```

---

## File Reference

| File | Replaces | Purpose |
|------|----------|---------|
| `config.py` | — | All paths, model name, Telegram token |
| `ingest.py` | `01_bronze_citizens.py` + `02_silver_processing.py` | Load CSV + generate citizens → SQLite |
| `embed_schemes.py` | `03_schemes_engine.py` (ML part) | Build FAISS index from scheme embeddings |
| `match.py` | `04_eligibility_matching.py` | Match citizen → schemes (rule + semantic) |
| `certificate.py` | `05_adhikar_certificates.py` | Generate PDF certificate via ReportLab |
| `pipeline.py` | `06_automation_triggers.py` | CLI orchestration |
| `bot.py` | `telegram_bot/nb6.py` | Telegram bot |

### Generated at runtime

```
data/
├── adhikar.db          # SQLite — citizens + schemes
├── scheme_index.faiss  # FAISS cosine similarity index
└── scheme_meta.pkl     # Scheme metadata (Python pickle)

certificates/
└── adhikar_CIT-0001_20260101120000.pdf
```

---

## Databricks Removal Audit

Every Databricks-specific call is marked `# DATABRICKS REMOVED` in the source.

| Original | Replaced with |
|----------|---------------|
| `SparkSession`, `spark.table()` | `pandas.read_sql` + `sqlite3` |
| `df.write.format("delta").saveAsTable()` | `sqlite3` INSERT |
| Databricks Jobs API (`/api/2.1/jobs/run-now`) | Local function call |
| `dbfs:/`, workspace paths | `pathlib.Path` |
| `F.udf()` Spark UDFs | Plain Python functions on DataFrame rows |
| `spark.catalog.tableExists()` | `Path.exists()` |
| `MERGE INTO` SQL | `INSERT OR REPLACE INTO` SQLite |
| `pyspark.sql.functions as F` | `pandas` boolean masks |

---

## Embedding Model

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

Supports 50+ languages including **Hindi, Marathi, Tamil, Bengali, Gujarati**.
Downloaded automatically on first `--setup` run (~420 MB).
