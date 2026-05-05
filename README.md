# ⚖️ Adhikar-Aina — Sovereign Rights Operating System

> *"We aren't building a search engine for schemes. We are building the Operating System for Citizen Rights. In Bharat, a right is never 'unclaimed' because it was 'unknown.'"*

---

## 🌟 What Is Adhikar-Aina?

**Adhikar-Aina** (अधिकार-आईना, "Mirror of Rights") is a **citizen-first, AI-powered welfare entitlement platform** built on a full-stack architecture spanning a **Databricks Lakehouse backend** and a **React + FastAPI frontend portal**. Its core thesis is simple but transformational:

> **Government schemes should find the citizen — not the other way around.**

Millions of Indians are unaware of welfare schemes they're entitled to. Schemes are scattered across dozens of websites, written in bureaucratic language, and effectively inaccessible to those with limited literacy, connectivity, or language skills. Adhikar-Aina solves this by acting as a sovereign rights mirror — reflecting every entitlement a citizen has, in their own language, delivered proactively to their phone.

The platform operates across two tightly integrated components:

| Component | Description |
|-----------|-------------|
| **Adhikar-Aina Lakehouse Engine** | A 7-notebook Databricks pipeline that ingests citizen records, matches them to 4,680+ government schemes, generates multilingual Adhikar Certificates, and dispatches proactive Telegram notifications |
| **Adhikar Web Portal** | A React + FastAPI web application with voice-first accessibility in 22+ Indian languages, real-time eligibility matching, and certificate download |

Together, they form a complete Operating System for Citizen Rights — from raw data to a citizen's fingertip.

---

## 📋 Table of Contents

1. [System Architecture — Full Stack](#1-system-architecture--full-stack)
2. [Technology Stack](#2-technology-stack)
3. [Lakehouse Pipeline — Notebook by Notebook](#3-lakehouse-pipeline--notebook-by-notebook)
   - [NB01 — Bronze Layer: Citizen Data Ingestion](#nb01--bronze-layer-citizen-data-ingestion)
   - [NB02 — Silver Layer: PII Masking & Transformation](#nb02--silver-layer-pii-masking--transformation)
   - [NB03 — Schemes Bronze → Silver: Eligibility Rule Engine](#nb03--schemes-bronze--silver-eligibility-rule-engine)
   - [NB04 — Eligibility Matching Engine](#nb04--eligibility-matching-engine-tag-join)
   - [NB05 — Adhikar Certificate Generator](#nb05--adhikar-certificate-generator-ai-layer)
   - [NB06 — Sovereign Dispatcher: Proactive Notifications](#nb06--sovereign-dispatcher-proactive-notifications)
   - [NB07 — Proof-of-Right Dashboard](#nb07--proof-of-right-dashboard-databricks-showcase)
4. [Web Portal — Frontend & Backend](#4-web-portal--frontend--backend)
   - [Portal Architecture & Data Flow](#portal-architecture--data-flow)
   - [REST API Reference](#rest-api-reference)
   - [Voice (STT/TTS) Integration](#voice-stttts-integration)
5. [Telegram Bot](#5-telegram-bot)
   - [Bot Architecture & State Machine](#bot-architecture--state-machine)
   - [PDF Certificate Generation](#pdf-certificate-generation)
6. [PII Firewall & Sovereign Data Architecture](#6-pii-firewall--sovereign-data-architecture)
7. [Delta Lake Design Decisions](#7-delta-lake-design-decisions)
8. [Delta Tables Reference](#8-delta-tables-reference)
9. [Project Structure](#9-project-structure)
10. [Environment & Configuration](#10-environment--configuration)
11. [End-to-End Data Flow](#11-end-to-end-data-flow)
12. [Key Design Patterns & Fixes](#12-key-design-patterns--fixes)
13. [How to Run](#13-how-to-run)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. System Architecture — Full Stack

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         CITIZEN TOUCHPOINTS                                ║
║  ┌─────────────────────┐          ┌──────────────────────────────────────┐  ║
║  │  TELEGRAM BOT        │          │  WEB PORTAL (React 19 + Vite)        │  ║
║  │  python-telegram-bot │          │  Voice · Multilingual · Accessible   │  ║
║  │  Vector Search + LLM │          │  http://localhost:5173               │  ║
║  │  PDF (fpdf)          │          └──────────────────┬───────────────────┘  ║
║  └──────────┬───────────┘                             │ HTTPS/REST            ║
╚═════════════╪═══════════════════════════════════════╪════════════════════════╝
              │ Telegram API                           │
              │                           ┌────────────▼────────────────────┐
              │                           │  API GATEWAY (FastAPI 0.116)    │
              │                           │  Port 8000 · Uvicorn ASGI       │
              │                           │  /api/register · /api/stt       │
              │                           │  /api/tts · /api/get-results    │
              │                           └────────────┬────────────────────┘
              │                                        │
╔═════════════╪════════════════════════════════════════╪════════════════════════╗
║             │      DATABRICKS LAKEHOUSE              │                        ║
║  ┌──────────▼──────┐   ┌────────────┐   ┌───────────▼──────┐                 ║
║  │ NB01            │──▶│ NB02       │──▶│ NB03             │                 ║
║  │ Bronze Citizens │   │ Silver PII │   │ Schemes Rule Eng │                 ║
║  └─────────────────┘   └─────┬──────┘   └────────┬─────────┘                 ║
║                              │ CDF               │                            ║
║                              ▼                   ▼                            ║
║                         ┌─────────────────────────────┐                       ║
║                         │ NB04: Eligibility Match     │                       ║
║                         │ Tag-Based Join (No UDFs)    │                       ║
║                         └──────────────┬──────────────┘                       ║
║                                        │                                      ║
║                         ┌──────────────▼──────────────┐                       ║
║                         │ NB05: Certificate Generator  │                       ║
║                         │ OpenAI + Sarvam AI           │                       ║
║                         └──────────────┬──────────────┘                       ║
║                              ┌─────────┴──────────┐                           ║
║                              ▼                     ▼                           ║
║                    ┌──────────────────┐   ┌──────────────────┐                ║
║                    │ NB06: Dispatcher │   │ NB07: Dashboard  │                ║
║                    │ Telegram Push    │   │ Databricks HTML  │                ║
║                    └──────────────────┘   └──────────────────┘                ║
║                                                                               ║
║  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐    ║
║  │ OpenAI GPT-4     │  │ Sarvam AI        │  │ Meta LLaMA 3.3 70B       │    ║
║  │ Certificate JSON │  │ Marathi · Hindi  │  │ Databricks Serving EP    │    ║
║  └──────────────────┘  └──────────────────┘  └──────────────────────────┘    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Technology Stack

### Lakehouse & Data Platform

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Compute** | Databricks Serverless / Classic Clusters | All PySpark computation |
| **Storage** | Delta Lake (Unity Catalog: `workspace.default`) | ACID, time-travel, CDF |
| **Orchestration** | Databricks Notebooks (NB01–NB07) | Pipeline stages |
| **Data Processing** | PySpark (`pyspark.sql.functions`, `StructType`) | All transformations |
| **AI — Structuring** | OpenAI `gpt-4` via REST API | Certificate JSON generation |
| **AI — Translation** | Sarvam AI `/translate` endpoint | Marathi (`mr-IN`) & Hindi (`hi-IN`) |
| **AI — Q&A / LLM** | Databricks Meta LLaMA 3.3 70B Instruct | In-bot citizen query answering |
| **Semantic Search** | Databricks Vector Search Index | Scheme lookup from natural language |
| **Change Tracking** | Delta CDF (`delta.enableChangeDataFeed`) | Event-driven eligibility refresh |
| **Hashing** | `hashlib.sha256`, PySpark `sha2` | Aadhaar anonymization, scheme IDs |
| **Interactive UI** | `dbutils.widgets`, `displayHTML` | Databricks dashboard |
| **Source Data** | Kaggle welfare schemes dataset | Government scheme catalog |

### Web Portal — Frontend

| Library | Version | Purpose |
|---------|---------|---------|
| React | 19.2.4 | UI framework & component model |
| Vite | 8.0.3 | Build tool & dev server |
| React Router | 7.13.2 | SPA routing & navigation |
| Tailwind CSS | 3.4.17 | Utility-first CSS styling |
| Axios | 1.14.0 | HTTP client for API calls |
| PostCSS | 8.4.1 | CSS transformation tool |

### Web Portal — Backend

| Library | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.116.1 | Web framework & API server |
| Uvicorn | 0.35.0 | ASGI server implementation |
| Pydantic | 2.11.7 | Data validation & serialization |
| Python | 3.12+ | Runtime environment |
| OpenAI | ≥1.59.9 | STT (Whisper), TTS, Chat |
| databricks-sql-connector | 3.5.0 | Databricks database connector |
| python-dotenv | 1.0.1 | Environment variable management |

### Bot & PDF

| Library | Purpose |
|---------|---------|
| `python-telegram-bot` | Async citizen-facing chatbot |
| `fpdf` | Printable Adhikar Certificate PDF |
| `nest_asyncio` | Notebook-compatible async event loop |
| `databricks-sdk` | Serving endpoints, Vector Search |

---

## 3. Lakehouse Pipeline — Notebook by Notebook

### NB01 — Bronze Layer: Citizen Data Ingestion

**File:** `nb1.py`

**Purpose:** Generates 1,000 synthetic citizen records and writes them as a partitioned Delta Lake Bronze table.

The notebook defines a `StructType` schema with 22 fields covering all attributes needed for welfare eligibility:

- **Identity fields:** `citizen_id` (UUID), `full_name`, `aadhaar_hash` (SHA-256 — never the real Aadhaar number)
- **Location fields:** `district`, `taluka`, `village`, `ward_no`, `survey_no` — modelled on Maharashtra districts: Satara, Kolhapur, Sangli
- **Economic fields:** `land_acres`, `annual_income`, `has_bpl_card`, `housing_status`
- **Social fields:** `caste_category` (SC/ST/OBC/GEN), `is_tribal`, `has_girl_child`, `girl_child_dob`
- **Infrastructure fields:** `has_electricity`, `has_water_source`, `employment_days`

The `make_citizen(i)` function generates records with realistic correlations — tribal citizens are more likely when `caste == "ST"`, `has_bpl_card` correlates with `income < 80000`, housing quality correlates with income. `random.seed(42)` ensures reproducibility.

```python
df.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .partitionBy("district")
    .saveAsTable("workspace.default.aa_citizens_bronze")
```

**Output table:** `workspace.default.aa_citizens_bronze`

---

### NB02 — Silver Layer: PII Masking & Transformation

**File:** `nb2.py`

**Purpose:** Reads Bronze and produces a cleaned, anonymized Silver table with a separate LLM-safe view as a PII firewall.

The Silver transformation chain:

1. **Drops `aadhaar_hash`** — removed entirely, never passes to LLM or bot.
2. **Creates `income_bracket`** via `when/otherwise`: `EWS` (<50K) → `LIG` (<100K) → `MIG` (<200K) → `HIG`
3. **Creates `land_category`**: `marginal` (<1 acre) → `small` (<2.5) → `medium` (<5.0) → `large`
4. **Creates `girl_child_age_years`** from `datediff(current_date(), girl_child_dob)`
5. **Drops raw PII:** `annual_income`, `land_acres`, `girl_child_dob`
6. **Preserves `full_name`** in Silver for personalized greeting flow
7. **Enables Delta CDF** for event-driven downstream processing

```sql
ALTER TABLE workspace.default.aa_citizens_silver
SET TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
)
```

**PII Sovereign Firewall — `aa_citizens_for_llm` VIEW:**

```sql
CREATE OR REPLACE VIEW workspace.default.aa_citizens_for_llm AS
SELECT citizen_id, district, taluka, village, ward_no,
       caste_category, is_tribal, has_girl_child, girl_child_age_years,
       has_bpl_card, housing_status, has_electricity, has_water_source,
       employment_days, income_bracket, land_category
FROM workspace.default.aa_citizens_silver
-- full_name, aadhaar_hash, and all raw financials are intentionally excluded
```

The LLM only ever sees `citizen_id` + categorical attributes. Names are fetched from Silver only when needed for display — at a controlled layer.

**Output:** `workspace.default.aa_citizens_silver`, view `workspace.default.aa_citizens_for_llm`

---

### NB03 — Schemes Bronze → Silver: Eligibility Rule Engine

**File:** `nb3.py`

**Purpose:** Ingests 4,680+ government welfare schemes from a Kaggle dataset and auto-generates SQL eligibility predicates for each scheme using native Spark expressions — no Python UDFs.

**Eligibility Predicate Generation (Native Spark):**

| Keyword detected in scheme metadata | `eligibility_sql` assigned |
|-------------------------------------|---------------------------|
| `housing` | `housing_status IN ('kutcha', 'semi_pucca') AND has_bpl_card = true` |
| `agri` | `land_acres > 0 AND income_bracket IN ('EWS', 'LIG', 'MIG')` |
| `women` | `has_girl_child = true` |
| `tribal` | `is_tribal = true` |
| `employment` | `employment_days < 100` |
| `solar` | `has_electricity = false` |
| `health` | `has_bpl_card = true` |
| `sc` | `caste_category = 'SC'` |
| `st` | `caste_category = 'ST'` |
| *(default)* | `income_bracket IN ('EWS', 'LIG')` |

**Scheme ID generation** uses `sha2` for deterministic, collision-resistant IDs:

```python
F.concat(F.lit("SCH"), F.substring(F.sha2(F.col("scheme_name"), 256), 1, 6))
```

**Output table:** `workspace.default.aa_schemes`

---

### NB04 — Eligibility Matching Engine (Tag Join)

**File:** `nb4.py`

**Purpose:** Core citizen-to-scheme matching. Pure Spark tag-based inner join — no AI, no SQL execution, no Python UDFs.

`spark.conf.set("spark.sql.shuffle.partitions", "8")` tunes the shuffle for the 1,000-citizen dataset.

**Step 1 — Enrich Citizens with `citizen_tags`:**

Each citizen gets a comma-separated tag string built entirely with native `when` expressions and `concat_ws`:

```
"housing, health, women, nutrition, education, tribal, sc, employment, solar, agriculture, ews_lig"
```

**Step 2 — Tag each Scheme** based on its `eligibility_sql` content.

**Step 3 — Inner Join on substring containment:**

```python
df_citizens_enriched.alias("c").join(
    df_schemes_enriched.alias("s"),
    F.col("c.citizen_tags").contains(F.col("s.scheme_tag")),
    "inner"
)
```

Output is a flat `aa_eligibility_results` table: one row per `(citizen_id, scheme_id)` match, with `is_notified` defaulting to `False`, partitioned by `district`.

**Output table:** `workspace.default.aa_eligibility_results`

---

### NB05 — Adhikar Certificate Generator (AI Layer)

**File:** `nb5.py`

**Purpose:** For the top 10 citizens by eligibility count, generates a structured Adhikar Certificate using OpenAI (legal JSON structure) + Sarvam AI (Marathi and Hindi translations).

**Name join at a controlled layer:**

```python
df_sample = (
    df_results.alias("r")
    .join(df_silver.alias("s"), "citizen_id")
    .groupBy("citizen_id", "s.full_name", "r.district")
    .agg(
        F.count("scheme_id").alias("total_schemes"),
        F.collect_list("scheme_name").alias("scheme_names"),
    )
    .orderBy(F.desc("total_schemes")).limit(10)
)
```

**Sarvam AI (`get_multilingual_message`):** Calls `https://api.sarvam.ai/translate` with `source_language_code: "en-IN"` — supports `mr-IN` (Marathi) and `hi-IN` (Hindi).

**OpenAI (`generate_proper_certificate`):** Generates a certificate JSON with `certificate_id`, `citizen_summary`, `top_schemes` (each with `scheme_name`, `scheme_code`, `benefit`, `action_required`, `legal_basis`), `marathi_message`, `hindi_message`, `disclaimer`, and `legal_validity`.

**Output table:** `workspace.default.aa_adhikar_certificates`

---

### NB06 — Sovereign Dispatcher: Proactive Notifications

**File:** `nb6.py`

**Purpose:** Proactive notification engine. Runs an eligibility pulse with idempotent MERGE INTO, then dispatches personalized Telegram alerts to registered citizens.

**Phase 1 — `run_eligibility_pulse()`:**
1. Re-enriches citizens with normalized lowercase tags.
2. Fetches active schemes for targeted pulses (e.g., `PM-UJJWALA`).
3. Performs dynamic matching join.
4. Writes new matches via **MERGE INTO** — zero duplicates on rerun.

**Phase 2 — `async push_alerts()`:**
1. Reads `aa_user_registry` with `.dropDuplicates(["citizen_id", "chat_id"])` as anti-spam shield.
2. Joins with eligibility results and Silver (for `full_name`). Limits to 50 alerts per run.
3. Sends personalized Telegram message with Markdown formatting.
4. Retries with plain text on Markdown failure.
5. Updates sent records in bulk via second MERGE INTO, setting `is_notified = True`.

---

### NB07 — Proof-of-Right Dashboard (Databricks Showcase)

**File:** `nb7.py`

**Purpose:** Comprehensive Databricks-native presentation layer demonstrating 10 platform capabilities in a single notebook.

| Section | Databricks Feature | What it demonstrates |
|---------|-------------------|----------------------|
| 1 | `dbutils.widgets` | Interactive dropdown filters (district, trigger mode, scheme ID) |
| 2 | `DESCRIBE HISTORY` | Delta audit trail — every eligibility change is RTI-auditable |
| 3 | Delta CDF `readChangeFeed` | Reads only changed citizen rows — true event-driven governance |
| 4 | Trigger 1 — New Scheme Pulse | MERGE INTO-based idempotent scheme matching |
| 5 | Trigger 2 — Life Event | MERGE INTO triggered by life event (girl child born) |
| 6 | `OPTIMIZE + ZORDER` | Data layout optimization by `citizen_id` |
| 7 | `displayHTML` Certificate | Renders HTML Adhikar Certificate inline in notebook |
| 8 | Unity Catalog assertion | Runtime PII proof — `full_name` absent from LLM view |
| 9 | Structured Streaming Monitor | `foreachBatch` pattern, district-level notification counts |
| 10 | Delta Time-Travel | `versionAsOf=0` — baseline vs current eligibility comparison |

The final `displayHTML` renders a dark-mode dashboard showing live counts: total citizens, schemes, eligibility matches, certificates issued, life events, and the "Unnotified Gap."

---

## 4. Web Portal — Frontend & Backend

### Portal Architecture & Data Flow

```
USER REGISTRATION
Citizen Info → React Form → POST /api/register-user
→ Databricks (Bronze Layer) → SQL Storage → citizen_id returned

ELIGIBILITY MATCHING
citizen_id → GET /api/get-results/{id}
→ Databricks Eligibility Engine → Scheme matches returned → Dashboard rendered

VOICE INTERACTION
User speaks → Browser MediaRecorder → POST /api/stt
→ OpenAI Whisper API → Transcribed text → Form field updated

CERTIFICATE DOWNLOAD
citizen_id → POST /api/adhikar-certificate
→ Databricks aa_adhikar_certificates → PDF generated → Returned to browser
```

### Key Features

**Multilingual Voice Interface** — 22+ Indian languages supported including Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Odia, Punjabi, Urdu, Assamese, Nepali, Konkani, Maithili, Manipuri, Sanskrit, Santhali, Sindhi, Dogri, Kashmiri, and Bodo.

**Government Scheme Database** — 4,680+ schemes (650+ Central, 4,020+ State) covering Social Security, Health, Education, Employment, Agriculture, and more.

**Legal Rights & Protections** — Appeal procedures, Ombudsman contacts, RTI guidance, legal aid resources, and disability rights documentation.

**Comprehensive Accessibility** — Voice-only interface for illiterate users, large text and high contrast modes, screen reader compatibility, mobile-responsive design.

### REST API Reference

#### Register Citizen

```http
POST /api/register-user
Content-Type: application/json

{
  "phone": "9876543210",
  "name": "John Doe",
  "age": 35,
  "gender": "M",
  "state": "Karnataka",
  "annual_income": 250000,
  "family_size": 3,
  "education": "12th Pass",
  "employment_status": "self_employed"
}

Response:
{
  "ok": true,
  "citizen_id": "CITZ-1234567890",
  "message": "User registered successfully"
}
```

#### Get Eligibility Results

```http
GET /api/get-results/{citizen_id}

Response:
{
  "ok": true,
  "citizen_id": "CITZ-1234567890",
  "eligible_schemes": [
    {
      "scheme_id": "SCH-001",
      "scheme_name": "Pradhan Mantri Kisan Samman Nidhi",
      "eligible": true,
      "annual_benefit": 6000,
      "eligibility_reason": "Farmer with land holdings",
      "application_url": "https://pmksy.gov.in"
    }
  ],
  "total_eligible": 24,
  "total_annual_benefit": 450000
}
```

#### Speech-to-Text (STT)

```http
POST /api/stt
Content-Type: multipart/form-data

Form Data:
- file: <audio (WAV, MP3, M4A)>
- language: "hi" (optional, auto-detected)

Response: { "ok": true, "text": "मेरा नाम राज है", "language": "hi" }
```

#### Text-to-Speech (TTS)

```http
POST /api/tts
Content-Type: application/json

{ "text": "आपकी वार्षिक आय क्या है?", "language": "hi" }

Response: <MP3 Audio Stream>
```

#### Generate Adhikar Certificate

```http
POST /api/adhikar-certificate
Content-Type: application/json

{ "citizen_id": "CITZ-1234567890", "format": "pdf" }

Response: <PDF Document>
```

### Voice (STT/TTS) Integration

**Backend STT Implementation:**

```python
from openai import OpenAI

openai_client = OpenAI(api_key=OPENAI_API_KEY)

@app.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...)):
    audio_content = await file.read()
    transcript = openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=(file.filename or "audio.wav", audio_content),
        response_format="json",
        timeout=45.0,
    )
    return {"ok": True, "text": transcript.text.strip()}
```

**Frontend Recording Implementation:**

```javascript
const stream = await navigator.mediaDevices.getUserMedia({
  audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
});
const mediaRecorder = new MediaRecorder(stream);
mediaRecorder.onstop = async () => {
  const blob = new Blob(audioChunks, { type: "audio/webm" });
  const result = await requestSpeechToText(blob);
  onChange(result.text);
};
```

**STT Cost Reference:**

| Scenario | Duration | Monthly Cost |
|----------|----------|--------------|
| Single onboarding | 5 min | ~$0.10/user |
| 100 citizens | 500 min | ~$10.00 |
| 10,000 citizens | 50,000 min | ~$1,000.00 |

Recommended budget: **$50–100/month** for pilot deployments.

---

## 5. Telegram Bot

### Bot Architecture & State Machine

**Files:** `Telegram Bot - Adhikar Aina.py`, `08_telegram_final.py`

The bot implements a two-state conversation machine using `python-telegram-bot`'s `ConversationHandler`:

```
/start
  │
  ▼
LOGIN_STATE ──── citizen sends Citizen ID ──▶ register_user()
                                                  │
                                     ┌────────────┴──────────────┐
                                     │ found                     │ not found
                                     ▼                           ▼
                               ACTIVE_STATE               LOGIN_STATE (retry)
                                     │
                               any text message
                                     │
                                     ▼
                              handle_query()
                            Vector Search + LLaMA 3.3 70B
                                     │
                                     ▼
                          [📄 Download My Adhikar Certificate]
                                     │  (inline keyboard)
                                     ▼
                           button_callback("gen_cert")
                            → fetches certificate JSON from Delta
                            → create_pdf() → send_document()
```

**`handle_login(update, context)`:**
1. Queries `aa_citizens_silver` for the citizen by ID.
2. If found, writes `(citizen_id, chat_id, datetime.now())` to `aa_user_registry` using an explicit `StructType` schema — critical fix for Spark Connect's remote inference issue.
3. Returns `full_name` for personalized greeting; stores in `context.user_data`.

**`handle_query(update, context)`:**
1. Queries `workspace.bronze.welfare_schemes_index` via `w.vector_search_indexes.query_index()` with `num_results=3`.
2. Builds citizen-contextualized prompt and sends to **Meta LLaMA 3.3 70B Instruct**.
3. Replies with AI-generated explanation + inline keyboard for PDF download.

### PDF Certificate Generation

**Class `AdhikarPDF(FPDF)`** extends `FPDF` with:
- **Header:** Government of India header, blue text, gold divider line
- **Footer:** Page number, sovereign system attribution

**`create_pdf(cert_data)` renders:**
- Certificate ID and issued date (right-aligned, orange)
- Citizen Summary (multi-cell paragraph)
- Top Entitlements table: scheme code + name (blue), benefit (body), action required (orange), legal basis (italic grey) — bordered fill cells
- Regional Mandates: Marathi and Hindi translations
- Disclaimer footer

**Latin-1 safety:** `safe_text()` strips unencodable characters (₹ → Rs., emoji substitutions), preventing `UnicodeEncodeError` on PDF output.

---

## 6. PII Firewall & Sovereign Data Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ LAYER 1: aa_citizens_bronze                                          │
│ Contains: aadhaar_hash, full_name, annual_income, land_acres         │
│ Access: Internal pipeline only — never exposed to LLM or users       │
└──────────────────────────────────────────────────────────────────────┘
                         │
                         ▼ (NB02 transformation)
┌──────────────────────────────────────────────────────────────────────┐
│ LAYER 2: aa_citizens_silver                                          │
│ Contains: full_name, income_bracket (bucketed), land_category        │
│ Drops: aadhaar_hash, annual_income, land_acres, date of birth        │
│ Access: Bot greeting logic, certificate generation (controlled join) │
└──────────────────────────────────────────────────────────────────────┘
                         │
                         ▼ (NB02 view creation)
┌──────────────────────────────────────────────────────────────────────┐
│ LAYER 3: aa_citizens_for_llm  (VIEW — PII SOVEREIGN FIREWALL)        │
│ Excludes: full_name (and all above drops)                            │
│ The LLM NEVER sees a citizen's name, income number, or Aadhaar      │
│ Access: Eligibility engine, Vector Search, LLaMA — categorical only  │
└──────────────────────────────────────────────────────────────────────┘
```

NB07 Section 8 includes a **runtime Unity Catalog assertion** that programmatically verifies `full_name` is absent from the LLM view columns — proving the firewall, not just claiming it.

---

## 7. Delta Lake Design Decisions

### Idempotency via MERGE INTO

All write operations that may be triggered multiple times use `MERGE INTO` instead of `INSERT INTO` or `.mode("append")`:

- Running the pipeline 50 times produces the same final state as running it once.
- `is_notified` updates are surgical — only matched pairs are updated.
- Dashboard counts are always exact, never inflated.

### Partitioning

`aa_citizens_bronze`, `aa_citizens_silver`, and `aa_eligibility_results` are partitioned by `district`. All queries filter by district (bot, dashboard, dispatcher), so partition pruning eliminates full table scans.

### Change Data Feed (CDF)

Enabled on `aa_citizens_silver`. Instead of re-processing all 1,000 citizens on every eligibility run:

```python
spark.read.format("delta")
    .option("readChangeFeed", "true")
    .option("startingVersion", start_version)
    .table("workspace.default.aa_citizens_silver")
```

### Write-First, Count-Later

In NB03, the Silver schemes table is written first, then counted from the saved table — not from the in-memory DataFrame. This avoids double evaluation of the lazy Spark DAG.

### Shuffle Partition Tuning

```python
spark.conf.set("spark.sql.shuffle.partitions", "8")
```

Default 200 partitions is wasteful for a 1,000-citizen dataset. Setting to 8 removes unnecessary shuffle overhead.

---

## 8. Delta Tables Reference

| Table | Layer | Partitioned By | Key Columns | Purpose |
|-------|-------|----------------|-------------|---------|
| `aa_citizens_bronze` | Bronze | `district` | `citizen_id`, `aadhaar_hash`, `full_name`, raw financials | Raw synthetic citizen records |
| `aa_citizens_silver` | Silver | `district` | `citizen_id`, `full_name`, `income_bracket`, `land_category` | Transformed, PII-reduced citizens |
| `aa_citizens_for_llm` | View (Silver) | — | No `full_name`, no raw financials | PII Firewall — LLM-safe view |
| `aa_schemes_bronze` | Bronze | — | Raw Kaggle columns | Raw government schemes |
| `aa_schemes` | Silver | — | `scheme_id`, `short_code`, `eligibility_sql`, `benefit_type` | Structured scheme catalog (4,680+ schemes) |
| `aa_eligibility_results` | Gold | `district` | `citizen_id`, `scheme_id`, `is_notified`, `matched_at` | Citizen ↔ Scheme matches |
| `aa_adhikar_certificates` | Gold | — | `citizen_id`, `adhikar_certificate` (JSON), `generated_at` | AI-generated multilingual certificates |
| `aa_user_registry` | Operational | — | `citizen_id`, `chat_id`, `last_login` | Telegram ↔ Citizen ID mapping |
| `aa_life_events` | Operational | — | Life event triggers | NB07 life-event eligibility pulse |

---

## 9. Project Structure

```
adhikar-aina/
│
├── README.md                              # This file
├── .env                                   # Environment variables (GITIGNORED)
├── .env.example                           # Environment template
│
├── databricks/                            # Lakehouse Pipeline (NB01–NB07)
│   ├── nb1.py                             # Bronze: Citizen data ingestion
│   ├── nb2.py                             # Silver: PII masking + CDF + LLM view
│   ├── nb3.py                             # Schemes: Eligibility rule engine
│   ├── nb4.py                             # Matching: Tag-based join engine
│   ├── nb5.py                             # Certificates: OpenAI + Sarvam AI
│   ├── nb6.py                             # Dispatcher: Telegram push + MERGE
│   └── nb7.py                             # Dashboard: 10-feature Databricks showcase
│
├── telegram_bot/
│   ├── Telegram Bot - Adhikar Aina.py     # Main bot (ConvHandler + PDF)
│   └── 08_telegram_final.py               # Production bot with all fixes
│
├── backend/                               # FastAPI Application
│   ├── app.py                             # Main FastAPI app (all routes)
│   ├── requirements.txt                   # Python dependencies
│   └── venv/                              # Python virtual environment
│
├── frontend/                              # React Application
│   ├── src/
│   │   ├── main.jsx                       # React entry point
│   │   ├── App.jsx                        # Root component
│   │   ├── components/
│   │   │   ├── VoiceQuestionCard.jsx      # Voice input (STT)
│   │   │   ├── SchemeCard.jsx             # Scheme display
│   │   │   ├── SchemeDetailsModal.jsx     # Scheme detail modal
│   │   │   ├── AdhikarCertificateModal.jsx # Certificate display
│   │   │   ├── LanguageSwitcher.jsx       # Language selection
│   │   │   ├── LoadingPanel.jsx           # Loading indicator
│   │   │   └── ErrorBoundary.jsx          # Error fallback
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx            # Home / intro
│   │   │   ├── LoginPage.jsx              # Login
│   │   │   ├── OnboardingPage.jsx         # Citizen profile collection
│   │   │   └── DashboardPage.jsx          # Eligibility results
│   │   ├── services/api.js                # Axios API client
│   │   ├── context/                       # Zustand state management
│   │   └── i18n/                          # 22+ language translations
│   │       └── locales/                   # en, hi, ta, te, bn, mr, gu, kn, ml, or, pa, ur...
│   ├── public/
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
└── data/
    └── updated_data.csv                   # Kaggle welfare schemes dataset
```

---

## 10. Environment & Configuration

### Databricks

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | `https://dbc-8d79a655-2501.cloud.databricks.com` |
| `DATABRICKS_ACCESS_TOKEN` | Personal access token |
| `DATABRICKS_HTTP_PATH` | `/sql/1.0/warehouses/<warehouse-id>` |
| `DATABRICKS_CATALOG` | `workspace` |
| `DATABRICKS_SCHEMA` | `default` |
| `DATABRICKS_LLM_ENDPOINT` | `databricks-meta-llama-3-3-70b-instruct` |
| `DATABRICKS_VECTOR_INDEX` | `workspace.bronze.welfare_schemes_index` |

### External APIs

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Starts with `sk-proj-` — for GPT-4 certificates, Whisper STT, TTS |
| `SARVAM_API_KEY` | Sarvam AI subscription key for Marathi/Hindi translation |
| `TELEGRAM_BOT_TOKEN` | From @BotFather — for push notifications |

### Complete `.env` Template

```bash
# Databricks
DATABRICKS_SERVER_HOSTNAME=your-workspace.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_ACCESS_TOKEN=dapixxxxxxxxxxxxxxxxxxx
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=default
DATABRICKS_SCHEMES_TABLE=aa_schemes
DATABRICKS_CITIZENS_TABLE=aa_citizens_silver
DATABRICKS_RESULTS_TABLE=aa_eligibility_results

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
OPENAI_TTS_MODEL=gpt-4o-mini
OPENAI_CHAT_MODEL=gpt-4o-mini

# Sarvam AI
SARVAM_API_KEY=your-sarvam-key

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token

# Frontend
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Python Libraries

```
pyspark
python-telegram-bot
fpdf
requests
databricks-sdk
databricks-sql-connector==3.5.0
nest_asyncio
fastapi==0.116.1
uvicorn==0.35.0
pydantic==2.11.7
openai>=1.59.9
python-dotenv==1.0.1
uuid, hashlib, json, asyncio, io, datetime
```

---

## 11. End-to-End Data Flow

```
1.  NB01  → Generate 1,000 citizen records  → aa_citizens_bronze
2.  NB02  → PII mask + categorize           → aa_citizens_silver
                                            → aa_citizens_for_llm (firewall view)
                                            → CDF enabled
3.  NB03  → Kaggle schemes + rule engine    → aa_schemes (4,680+ schemes)
4.  NB04  → Tag-join citizens × schemes     → aa_eligibility_results
5.  NB05  → OpenAI + Sarvam AI             → aa_adhikar_certificates (top 10)
6.  NB06  → Eligibility pulse (MERGE)       → Telegram push notifications sent
7.  NB07  → Dashboard, CDF, time-travel     → Databricks interactive showcase

Web Portal (request-driven):
  Citizen fills form → POST /api/register-user → aa_citizens (Databricks write)
  Citizen views results → GET /api/get-results/{id} → aa_eligibility_results
  Citizen speaks → POST /api/stt → OpenAI Whisper → text returned
  Citizen downloads cert → POST /api/adhikar-certificate → PDF returned

Telegram Bot (always-on polling):
  /start → LOGIN_STATE → citizen sends ID → register_user() → aa_user_registry
  Citizen asks question → Vector Search + LLaMA 3.3 70B → text reply
  Citizen taps button → aa_adhikar_certificates → create_pdf() → document sent
```

---

## 12. Key Design Patterns & Fixes

### Fix 1 — Native Spark Instead of Python UDFs (NB03)

Python UDFs in Spark Connect (Serverless) carry serialization overhead and can fail unexpectedly. The eligibility predicate generation was refactored from `F.udf(map_eligibility, StringType())` to a native `F.when(...).when(...).otherwise(...)` chain — pure Catalyst, zero serialization.

### Fix 2 — Explicit StructType for Spark Connect (Telegram Bot)

`spark.createDataFrame(list_of_dicts)` in Serverless requires remote schema inference over gRPC, which fails with `DATA_SOURCE_NOT_FOUND`. The fix is an explicit `StructType` schema with list-of-tuples:

```python
mapping_data = [(str(citizen_id), str(chat_id), datetime.now())]
spark.createDataFrame(mapping_data, schema=USER_REGISTRY_SCHEMA)
```

### Fix 3 — Bot Session Stability (Telegram Bot)

Re-running the bot cell without stopping the old polling loop causes Telegram to return `409 Conflict`. A "Kill Old Sessions" cell explicitly calls:

```python
await app.updater.stop(); await app.stop(); await app.shutdown()
```

### Fix 4 — Schema Drift (NB07)

`ward_no` and `girl_child_age_years` caused `DELTA_FAILED_TO_MERGE_FIELDS` when defined as `IntegerType` in some places and inferred as `LongType` by Spark. NB07 declares them consistently as `LongType` everywhere.

### Fix 5 — MERGE Instead of Append (NB06, NB07)

All trigger-based writes use `MERGE INTO` with `ON target.citizen_id = source.citizen_id AND target.scheme_id = source.scheme_id` to guarantee idempotency. Re-runs on the same data produce zero new rows.

---

## 13. How to Run

### Prerequisites

- Databricks workspace with Unity Catalog enabled (`workspace.default` accessible)
- Kaggle welfare schemes dataset loaded into `workspace.default.updated_data`
- Vector Search index created at `workspace.bronze.welfare_schemes_index`
- Telegram Bot Token from @BotFather
- OpenAI API key
- Sarvam AI API key
- Node.js ≥ 18.0.0, Python ≥ 3.12.0

### Step 1 — Clone Repository

```bash
git clone https://github.com/your-org/adhikar-aina.git
cd adhikar-aina
cp .env.example .env
# Edit .env with your credentials
```

### Step 2 — Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3 — Frontend Setup

```bash
cd frontend
npm install
```

### Step 4 — Run the Lakehouse Pipeline (in order)

```bash
# In Databricks — run notebooks in sequence:
NB01 (nb1.py)     → Creates aa_citizens_bronze
NB02 (nb2.py)     → Creates aa_citizens_silver + aa_citizens_for_llm
NB03 (nb3.py)     → Creates aa_schemes
NB04 (nb4.py)     → Creates aa_eligibility_results
NB05 (nb5.py)     → Creates aa_adhikar_certificates
NB06 (nb6.py)     → Dispatches Telegram push alerts
NB07 (nb7.py)     → Interactive Databricks dashboard
```

### Step 5 — Start the Web Portal

**Terminal 1 — Backend:**

```bash
cd backend
source venv/bin/activate
python3 -c "
import uvicorn
from app import app
uvicorn.run(app, host='127.0.0.1', port=8000, reload=True, log_level='info')
"
```

**Terminal 2 — Frontend (Development):**

```bash
cd frontend
npm run dev
# Access at http://localhost:5173
```

**Terminal 2 — Frontend (Production Build):**

```bash
cd frontend
npm run build
cd dist
python3 -m http.server 5173
```

### Step 6 — Start the Telegram Bot

```bash
# Run in Databricks notebook or local Python:
python3 telegram_bot/"Telegram Bot - Adhikar Aina.py"
```

### Rerunning Safely

All notebooks are idempotent. Tables use `mode("overwrite")` for full refreshes and `MERGE INTO` for incremental updates. Re-run any notebook without duplicating data.

---

## 14. Troubleshooting

### Backend

**`ModuleNotFoundError: No module named 'openai'`**
```bash
source venv/bin/activate
pip install --upgrade openai>=1.59.9
python3 -c "from openai import OpenAI; print('OK')"
```

**`Port 8000 already in use`**
```bash
lsof -i :8000
kill -9 <PID>
```

**`Databricks connection refused`**
```bash
python3 -c "
from databricks import sql
conn = sql.connect(
    server_hostname='xxx.databricks.com',
    http_path='/sql/1.0/warehouses/xxx',
    personal_access_token='dapixxx'
)
print('Connection OK')
"
```

### Frontend

**`npm: command not found`** — Install Node.js from nodejs.org or `brew install node`

**Blank page / 404 errors** — Verify backend is running at port 8000, then rebuild frontend with `npm run build`

### Voice (STT/TTS)

**Microphone permission denied** — Click URL bar → Site Info → Microphone → Allow → Refresh

**Empty transcription** — Speak clearly for 2–3 seconds; check OpenAI API key is set in `.env`

**Quota exceeded** — Check billing at platform.openai.com/account/billing; set usage limits

### Telegram Bot

**`409 Conflict`** — Old polling loop still running. Run the Kill Old Sessions cell before restarting.

**`DATA_SOURCE_NOT_FOUND` on `createDataFrame`** — Ensure explicit `StructType` schema is passed; do not use `list_of_dicts` with Spark Connect.

---

## 📊 Scale & Impact Numbers

| Metric | Value |
|--------|-------|
| Citizen records (synthetic pilot) | 1,000 |
| Government schemes catalogued | 4,680+ |
| Central Government schemes | 650+ |
| State Government schemes | 4,020+ |
| Languages supported (voice) | 22+ |
| AI models integrated | 4 (GPT-4, LLaMA 3.3 70B, Whisper, Sarvam AI) |
| Delta tables in pipeline | 9 |
| Databricks platform features demonstrated | 10 |
| Certificate generation (top citizens) | 10 per pipeline run |
| Max Telegram alerts per run | 50 (anti-spam guard) |

---

*Built on Databricks Lakehouse · Delta Lake · Unity Catalog · Meta LLaMA 3.3 70B · Sarvam AI · OpenAI GPT-4 · OpenAI Whisper · React 19 · FastAPI · Telegram Bot API*

*A sovereign system where every citizen's entitlement is known, proven, and delivered — without them ever having to ask.*
