# ⚖️ Adhikar-Aina — Sovereign Rights Operating System

> *"We aren't building a search engine for schemes. We are building the Operating System for Citizen Rights. In Bharat, a right is never 'unclaimed' because it was 'unknown.'"*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [Technology Stack](#3-technology-stack)
4. [Data Pipeline — Notebook by Notebook](#4-data-pipeline--notebook-by-notebook)
   - [NB01 — Bronze Layer: Citizen Data Ingestion](#nb01--bronze-layer-citizen-data-ingestion)
   - [NB02 — Silver Layer: PII Masking & Transformation](#nb02--silver-layer-pii-masking--transformation)
   - [NB03 — Schemes Bronze → Silver: Eligibility Rule Engine](#nb03--schemes-bronze--silver-eligibility-rule-engine)
   - [NB04 — Eligibility Matching Engine (Tag Join)](#nb04--eligibility-matching-engine-tag-join)
   - [NB05 — Adhikar Certificate Generator (AI Layer)](#nb05--adhikar-certificate-generator-ai-layer)
   - [NB06 — Sovereign Dispatcher: Proactive Notifications](#nb06--sovereign-dispatcher-proactive-notifications)
   - [NB07 — Proof-of-Right Dashboard (Databricks Showcase)](#nb07--proof-of-right-dashboard-databricks-showcase)
5. [Telegram Bot](#5-telegram-bot)
   - [Bot Architecture & State Machine](#bot-architecture--state-machine)
   - [Key Handler Functions](#key-handler-functions)
   - [PDF Certificate Generation](#pdf-certificate-generation)
6. [Delta Lake Design Decisions](#6-delta-lake-design-decisions)
7. [PII Firewall & Sovereign Data Architecture](#7-pii-firewall--sovereign-data-architecture)
8. [Delta Tables Reference](#8-delta-tables-reference)
9. [Environment & Configuration](#9-environment--configuration)
10. [End-to-End Data Flow](#10-end-to-end-data-flow)
11. [Key Design Patterns & Fixes](#11-key-design-patterns--fixes)
12. [How to Run](#12-how-to-run)

---

## 1. Project Overview

**Adhikar-Aina** (अधिकार-आईना, "Mirror of Rights") is a **citizen-first, AI-powered welfare entitlement platform** built entirely on **Databricks Lakehouse**. Its core thesis is simple but transformational: government schemes should find the citizen, not the other way around.

The system:

- **Ingests** synthetic citizen records (modelled on Maharashtra districts: Satara, Kolhapur, Sangli) into a Bronze Delta Lake table.
- **Transforms** data through a Bronze → Silver pipeline with PII masking, income bucketing, land classification, and Change Data Feed (CDF) enabled tracking.
- **Maps** government welfare schemes from a Kaggle dataset, auto-generating SQL eligibility predicates for each scheme using native Spark expressions.
- **Matches** citizens to schemes through a high-performance tag-based join (no Python UDFs in the hot path).
- **Generates** multilingual "Adhikar Certificates" — formal Proof-of-Right documents — using OpenAI for structuring and Sarvam AI for Marathi/Hindi translation.
- **Notifies** citizens proactively via a Telegram Bot, eliminating the need for citizens to know about, search for, or apply for schemes on their own.
- **Stores** everything in auditable, versioned Delta Lake tables — enabling RTI (Right to Information) compliance, time-travel queries, and idempotent reruns.

---

## 2. Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATABRICKS LAKEHOUSE                             │
│                                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────────────┐ │
│  │ NB01     │───▶│ NB02     │───▶│ NB03     │───▶│ NB04              │ │
│  │ Bronze   │    │ Silver   │    │ Schemes  │    │ Eligibility Match │ │
│  │ Citizens │    │ PII Mask │    │ Rule Eng │    │ Tag-Based Join    │ │
│  └──────────┘    └──────────┘    └──────────┘    └───────────────────┘ │
│                       │                                  │              │
│                       │ CDF (Change Data Feed)           ▼              │
│                       │                         ┌──────────────────┐   │
│                       └────────────────────────▶│ NB05             │   │
│                                                 │ Certificate Gen  │   │
│                                                 │ OpenAI + Sarvam  │   │
│                                                 └──────────────────┘   │
│                                                          │              │
│         ┌───────────────────────────────────────────────┘              │
│         ▼                           ▼                                  │
│  ┌──────────────┐          ┌──────────────────┐                        │
│  │ NB06         │          │ NB07             │                        │
│  │ Dispatcher   │          │ Dashboard        │                        │
│  │ Telegram Push│          │ Databricks HTML  │                        │
│  └──────────────┘          └──────────────────┘                        │
│         │                                                               │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌────────────────────┐
 │  TELEGRAM BOT      │
 │  python-telegram-  │
 │  bot + ConvHandler │
 │  Vector Search LLM │
 │  PDF (fpdf)        │
 └────────────────────┘
```

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Compute** | Databricks Serverless / Classic Clusters | All PySpark computation |
| **Storage** | Delta Lake (Unity Catalog: `workspace.default`) | All tables — ACID, time-travel, CDF |
| **Orchestration** | Databricks Notebooks (NB01–NB07) | Pipeline stages |
| **Data Processing** | PySpark (`pyspark.sql.functions`, `StructType`) | All transformations |
| **AI — Structuring** | OpenAI (`gpt-4` via REST API) | Certificate JSON generation |
| **AI — Translation** | Sarvam AI (`/translate` endpoint) | Marathi (`mr-IN`) & Hindi (`hi-IN`) |
| **AI — Q&A / LLM** | Databricks Meta LLaMA 3.3 70B Instruct | In-bot citizen query answering |
| **Semantic Search** | Databricks Vector Search Index | Scheme lookup from natural language |
| **Bot Framework** | `python-telegram-bot` (async) | Citizen-facing chatbot |
| **PDF Generation** | `fpdf` (`FPDF` class) | Printable Adhikar Certificate |
| **Data Catalog** | Databricks Unity Catalog | Governance, lineage, PII firewall |
| **Hashing** | `hashlib.sha256`, PySpark `sha2` | Aadhaar anonymization, scheme IDs |
| **Change Tracking** | Delta CDF (`delta.enableChangeDataFeed`) | Event-driven eligibility refresh |
| **Interactive UI** | `dbutils.widgets`, `displayHTML` | Databricks dashboard widgets |
| **Source Data** | Kaggle welfare schemes dataset | Government scheme catalog |

---

## 4. Data Pipeline — Notebook by Notebook

### NB01 — Bronze Layer: Citizen Data Ingestion

**File:** `nb1.py`

**Purpose:** Generates 1,000 synthetic citizen records and writes them as a partitioned Delta Lake Bronze table.

**What it does:**

The notebook first sets the active catalog and schema (`USE CATALOG workspace; USE default`). It then defines a `StructType` schema with 22 fields covering all attributes needed for welfare eligibility:

- **Identity fields:** `citizen_id` (UUID), `full_name`, `aadhaar_hash` (SHA-256 of a synthetic ID string — never the real Aadhaar number)
- **Location fields:** `district`, `taluka`, `village`, `ward_no`, `survey_no`
- **Economic fields:** `land_acres`, `annual_income`, `has_bpl_card`, `housing_status`
- **Social fields:** `caste_category` (SC/ST/OBC/GEN), `is_tribal`, `has_girl_child`, `girl_child_dob`
- **Infrastructure fields:** `has_electricity`, `has_water_source`, `employment_days`
- **Metadata:** `created_at`, `updated_at`, `data_source`

The `make_citizen(i)` function generates one record with realistic correlations — e.g., tribal citizens are more likely when `caste == "ST"`, `has_bpl_card` is more likely if `income < 80000`, housing quality correlates with income, etc. `random.seed(42)` ensures reproducibility.

All 1,000 records are collected into a Python list, converted via `spark.createDataFrame(records, schema=citizen_schema)`, and written as a Delta table partitioned by `district`:

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

**Purpose:** Reads the Bronze layer and produces a cleaned, anonymized Silver table. Critically, it creates a separate **LLM-safe view** that acts as a PII firewall.

**What it does:**

The Silver transformation performs the following steps in a single PySpark chain:

1. **Drops `aadhaar_hash`** — the Aadhaar-derived hash is removed entirely and never passes to the LLM or bot.

2. **Creates `income_bracket`** using a `when/otherwise` chain:
   - `< 50,000` → `EWS` (Economically Weaker Section)
   - `< 100,000` → `LIG` (Low Income Group)
   - `< 200,000` → `MIG` (Middle Income Group)
   - else → `HIG` (High Income Group)

3. **Creates `land_category`:**
   - `< 1.0 acres` → `marginal`
   - `< 2.5 acres` → `small`
   - `< 5.0 acres` → `medium`
   - else → `large`

4. **Creates `girl_child_age_years`** using `datediff` from `current_date()`, only when `has_girl_child = true` and `girl_child_dob` is not null.

5. **Drops raw PII columns:** `annual_income`, `land_acres`, `girl_child_dob` — replaced by their categorized equivalents.

6. **Preserves `full_name`** intentionally in the Silver table for the bot's personalized greeting flow (e.g., "Namaste, Rajesh Patil").

7. **Enables Delta Change Data Feed (CDF)** on the Silver table:
   ```python
   ALTER TABLE ... SET TBLPROPERTIES (
       'delta.enableChangeDataFeed' = 'true',
       'delta.autoOptimize.optimizeWrite' = 'true',
       'delta.autoOptimize.autoCompact' = 'true'
   )
   ```
   This allows downstream processes to read only changed rows — making the eligibility engine event-driven rather than full-batch.

8. **Creates `aa_citizens_for_llm` VIEW** — this is the PII Sovereign Firewall:
   ```sql
   CREATE OR REPLACE VIEW workspace.default.aa_citizens_for_llm AS
   SELECT citizen_id, district, taluka, village, ward_no,
          caste_category, is_tribal, has_girl_child, girl_child_age_years,
          has_bpl_card, housing_status, has_electricity, has_water_source,
          employment_days, income_bracket, land_category, ...
   FROM workspace.default.aa_citizens_silver
   ```
   This view **excludes `full_name`**, `aadhaar_hash`, and all raw numeric PII. The LLM only ever sees `citizen_id` + categorical attributes. The name is fetched separately from Silver only when needed for display.

**Output tables:** `workspace.default.aa_citizens_silver`, view `workspace.default.aa_citizens_for_llm`

---

### NB03 — Schemes Bronze → Silver: Eligibility Rule Engine

**File:** `nb3.py`

**Purpose:** Ingests a raw government schemes dataset (from Kaggle, stored in `workspace.default.updated_data`) and transforms it into a structured `aa_schemes` table with auto-generated SQL eligibility predicates for each scheme.

**What it does:**

**Eligibility Predicate Generation (Native Spark, No Python UDFs):**

The notebook uses a native Spark `when/otherwise` chain (not a Python UDF) to derive an `eligibility_sql` string column for each scheme. It inspects a concatenation of `schemeCategory`, `tags`, `details`, and `eligibility` columns to detect keywords:

| Keyword detected | `eligibility_sql` assigned |
|---|---|
| `housing` | `housing_status IN ('kutcha', 'semi_pucca') AND has_bpl_card = true` |
| `agri` | `land_acres > 0 AND income_bracket IN ('EWS', 'LIG', 'MIG')` |
| `women` | `has_girl_child = true` |
| `tribal` | `is_tribal = true` |
| `employment` | `employment_days < 100` |
| `solar` | `has_electricity = false` |
| `health` | `has_bpl_card = true` |
| ` sc` | `caste_category = 'SC'` |
| ` st` | `caste_category = 'ST'` |
| *(default)* | `income_bracket IN ('EWS', 'LIG')` |

This approach avoids the Python UDF shuffle overhead on Spark Serverless Connect — it's a pure catalyst expression.

**Scheme ID generation** uses `sha2` hash for deterministic, collision-resistant IDs:
```python
F.concat(F.lit("SCH"), F.substring(F.sha2(F.col("scheme_name"), 256), 1, 6))
```

The Silver output selects: `scheme_id`, `scheme_name`, `short_code`, `benefit_type`, `benefit_amount`, `eligibility_sql`, `required_docs`, `is_active`, `created_at`. Duplicates on `scheme_name` are dropped. The write order is: **write first, then count from saved table** — this avoids double-evaluation of the lazy Spark DAG.

**Output table:** `workspace.default.aa_schemes`

---

### NB04 — Eligibility Matching Engine (Tag Join)

**File:** `nb4.py`

**Purpose:** Performs the core citizen-to-scheme matching. No AI, no SQL execution — a pure Spark tag-based inner join between enriched citizens and tagged schemes.

**What it does:**

`spark.conf.set("spark.sql.shuffle.partitions", "8")` tunes the shuffle for the 1,000-citizen dataset (default 200 is wasteful).

**Step 1 — Enrich Citizens with a `citizen_tags` string column:**

Each citizen gets a comma-separated tag string derived from their attributes:
```
housing, health, women,nutrition,education, tribal, sc, st, employment, solar, agriculture, ews_lig, ews_lig_mig
```
This is built entirely with native `when` expressions and `concat_ws`.

**Step 2 — Tag each Scheme:**

Each scheme gets a `scheme_tag` string derived from its `eligibility_sql` content (e.g., if `eligibility_sql` contains `housing_status`, the scheme gets tag `housing`).

**Step 3 — Inner Join on substring containment:**
```python
df_citizens_enriched.alias("c").join(
    df_schemes_enriched.alias("s"),
    F.col("c.citizen_tags").contains(F.col("s.scheme_tag")),
    "inner"
)
```

This produces a flat `aa_eligibility_results` table with one row per `(citizen_id, scheme_id)` match, plus `district`, `taluka`, `village`, `income_bracket`, `scheme_name`, `benefit`, `required_docs`, `is_notified` (default `False`), and `matched_at` timestamp. The table is partitioned by `district`.

**Output table:** `workspace.default.aa_eligibility_results`

---

### NB05 — Adhikar Certificate Generator (AI Layer)

**File:** `nb5.py`

**Purpose:** For each of the top 10 citizens by eligibility count, generates a structured Adhikar Certificate using OpenAI (for legal JSON structure) and Sarvam AI (for Marathi and Hindi translations).

**What it does:**

**Data loading with name join:** The top 10 citizens are selected by joining `aa_eligibility_results` (PII-free) with `aa_citizens_silver` (which holds `full_name`) — the join is done only at this controlled layer, not exposed to the LLM directly.

```python
df_sample = (
    df_results.alias("r")
    .join(df_silver.alias("s"), "citizen_id")
    .groupBy("citizen_id", "s.full_name", "r.district", ...)
    .agg(
        F.count("scheme_id").alias("total_schemes"),
        F.collect_list("scheme_name").alias("scheme_names"),
        ...
    )
    .orderBy(F.desc("total_schemes")).limit(TOP_N_CITIZENS)
)
```

**Sarvam AI Integration (`get_multilingual_message`):** Calls `https://api.sarvam.ai/translate` with `source_language_code: "en-IN"` and a target (`mr-IN` for Marathi, `hi-IN` for Hindi). The API key is passed via `api-subscription-key` header.

**OpenAI Integration (`generate_proper_certificate`):** Sends a structured prompt to generate a certificate JSON containing: `certificate_id`, `citizen_summary`, `top_schemes` (each with `scheme_name`, `scheme_code`, `benefit`, `action_required`, `legal_basis`), `marathi_message`, `hindi_message`, `disclaimer`, and `legal_validity`.

**Certificate storage:** The JSON is serialized with `json.dumps()` and stored in the `adhikar_certificate` STRING column of `aa_adhikar_certificates`, making it portable for the Telegram bot to fetch and render.

**Output table:** `workspace.default.aa_adhikar_certificates`

---

### NB06 — Sovereign Dispatcher: Proactive Notifications

**File:** `nb6.py`

**Purpose:** The proactive notification engine. Runs an eligibility pulse (re-matching with MERGE INTO for idempotency) and then dispatches Telegram messages to registered citizens for new scheme matches.

**What it does:**

The script is structured as an `async main()` function with two phases:

**Phase 1 — `run_eligibility_pulse()`:**

1. Refreshes table metadata (handles Databricks Serverless's `NOT_SUPPORTED_WITH_SERVERLESS` gracefully).
2. Re-enriches citizens with `citizen_tags` using normalized lowercase tags (e.g., `"skills & employment"`, `"women & child"`, `"financial aid"`).
3. Fetches active schemes filtered to a specific `short_code` (e.g., `PM-UJJWALA`) for targeted pulses.
4. Performs a dynamic matching join.
5. Writes new matches using a **MERGE INTO** to avoid duplicate rows on rerun:
   ```sql
   MERGE INTO workspace.default.aa_eligibility_results AS target
   USING _dynamic_staging AS source
   ON target.citizen_id = source.citizen_id AND target.scheme_id = source.scheme_id
   WHEN NOT MATCHED THEN INSERT *
   ```

**Phase 2 — `async push_alerts()`:**

1. Reads `aa_user_registry` (citizen → Telegram chat_id mapping) with `.dropDuplicates(["citizen_id", "chat_id"])` as an anti-spam shield.
2. Joins with `aa_eligibility_results` (unnotified) and `aa_citizens_silver` (for `full_name`). Limits to 50 alerts per run for stability.
3. For each pending alert, sends a personalized Telegram message with Markdown formatting (escaping `_` and `*` characters).
4. On Markdown failure, retries with plain text (`parse_mode=None`).
5. Updates sent records in bulk via a second MERGE INTO, setting `is_notified = True`.

**Async event loop handling:** The entry point handles both clean `asyncio.run()` and notebook environments (where the loop already exists) using `nest_asyncio.apply()`.

---

### NB07 — Proof-of-Right Dashboard (Databricks Showcase)

**File:** `nb7.py`

**Purpose:** A comprehensive Databricks-native presentation layer that showcases all 8 Databricks platform features in a single notebook, with a full interactive HTML dashboard.

**10 Sections:**

| Section | Databricks Feature | What it demonstrates |
|---|---|---|
| 1 | `dbutils.widgets` | Interactive dropdown filters (district, trigger mode, scheme ID) |
| 2 | `DESCRIBE HISTORY` | Delta audit trail — every eligibility change is RTI-auditable by version |
| 3 | Delta CDF `readChangeFeed` | Reads only changed citizen rows since last version — true event-driven governance |
| 4 | Trigger 1 — New Scheme Pulse | MERGE INTO-based idempotent scheme matching for a new scheme ID |
| 5 | Trigger 2 — Life Event | MERGE INTO-based matching triggered by a life event (girl child born) |
| 6 | `OPTIMIZE + ZORDER` | Data layout optimization by `citizen_id` for 50× faster lookups at scale |
| 7 | `displayHTML` Certificate | Renders an HTML Adhikar Certificate inline in the Databricks notebook |
| 8 | Unity Catalog assertion | Runtime PII proof — confirms `full_name` is absent from the LLM view |
| 9 | Structured Streaming Monitor | `foreachBatch` pattern showing district-level pending notification counts |
| 10 | Delta Time-Travel | Reads `versionAsOf=0` to compare baseline vs current eligibility count |

**Final HTML Dashboard (`displayHTML`):** Renders a styled dark-mode dashboard with Space Mono / Sora fonts showing live counts: total citizens, schemes, eligibility matches, certificates issued, life events, and the "Unnotified Gap" (citizens eligible but not yet notified).

---

## 5. Telegram Bot

### Bot Architecture & State Machine

**Files:** `Telegram Bot - Adhikar Aina.py`, `08_telegram_final.py`

The bot uses `python-telegram-bot` with a `ConversationHandler` implementing a two-state state machine:

```
/start
  │
  ▼
LOGIN_STATE ──── user sends Citizen ID ──▶ register_user()
                                               │
                                    ┌──────────┴──────────┐
                                    │ found               │ not found
                                    ▼                     ▼
                              ACTIVE_STATE           LOGIN_STATE
                                    │                (retry)
                              any text message
                                    │
                                    ▼
                             handle_query()
                           (Vector Search + LLM)
                                    │
                                    ▼
                         [📄 Download My Adhikar Certificate]
                                    │  (inline keyboard)
                                    ▼
                          button_callback("gen_cert")
                           → fetches certificate JSON
                           → creates PDF bytes
                           → sends as document
```

### Key Handler Functions

**`start()`:** Greets the citizen and requests their Unique Citizen ID. Returns `LOGIN_STATE`.

**`handle_login(update, context)`:**
- Calls `register_user(cid, chat_id)` which:
  1. Queries `aa_citizens_silver` for the citizen by ID.
  2. If found, writes a `(citizen_id, chat_id, datetime.now())` tuple to `aa_user_registry` using an explicit `StructType` schema (critical fix for Spark Connect's remote inference issue).
  3. Returns `full_name` for the personalized greeting.
- Stores `citizen_id` and `name` in `context.user_data` for the session.

**`handle_query(update, context)`:**
1. Calls `w.vector_search_indexes.query_index()` on `workspace.bronze.welfare_schemes_index` with `num_results=3`.
2. Builds a prompt: `"Citizen {name} asked: {query}\nMatched schemes: {json}\nExplain why these schemes match..."`.
3. Sends to **Meta LLaMA 3.3 70B Instruct** via `w.serving_endpoints.query()`.
4. Replies with the AI-generated explanation and an **inline keyboard button** to download the PDF certificate.

**`button_callback(update, context)` — `gen_cert`:**
1. Fetches the latest certificate row for `citizen_id` from `aa_adhikar_certificates`.
2. Deserializes the JSON with `json.loads()`.
3. Calls `create_pdf(cert_data)` to generate PDF bytes.
4. Sends via `context.bot.send_document()` as a named file: `Adhikar_Certificate_{cert_id}.pdf`.

### PDF Certificate Generation

**Class `AdhikarPDF(FPDF)`:**

Extends `FPDF` with a custom `header()` (Government of India header, blue text, gold divider line) and `footer()` (page number, sovereign system attribution).

**`create_pdf(cert_data)`** renders:
- Certificate ID and issued date (right-aligned, orange)
- Citizen Summary (multi-cell paragraph)
- Top Entitlements table — for each scheme: scheme code + name (blue header), benefit (body), action required (orange), legal basis (italic grey) — all in bordered fill cells
- Regional Mandates: Marathi and Hindi translations
- Disclaimer footer

**Latin-1 safety:** A `safe_text()` helper strips characters that `latin-1` cannot encode (₹ → Rs., emoji substitutions), preventing `UnicodeEncodeError` on the PDF output stream.

---

## 6. Delta Lake Design Decisions

### Idempotency via MERGE INTO

All write operations that may be triggered multiple times (NB06 dispatcher, NB07 triggers) use `MERGE INTO` instead of `INSERT INTO` or `.mode("append")`. This means:

- Running the pipeline 50 times produces the same final state as running it once.
- `is_notified` updates are surgical — only matched pairs are updated.
- Counts in the dashboard are always exact, not inflated.

### Partitioning

`aa_citizens_bronze`, `aa_citizens_silver`, and `aa_eligibility_results` are all partitioned by `district`. Since all queries filter by district (the Telegram bot, the dashboard widgets, the notification dispatcher), partition pruning eliminates full table scans.

### Change Data Feed (CDF)

Enabled on `aa_citizens_silver`. Instead of re-processing all 1,000 citizens on every eligibility run, the engine can read only rows that changed since the last version using:
```python
spark.read.format("delta")
    .option("readChangeFeed", "true")
    .option("startingVersion", start_version)
    .table(TABLE_NAME)
```

### Write-First, Count-Later

In NB03, the Silver schemes table is written first and then counted from the saved table — not from the in-memory DataFrame. This avoids double evaluation of the lazy Spark DAG (which would run all transformations twice).

---

## 7. PII Firewall & Sovereign Data Architecture

The PII architecture has three distinct layers:

```
┌──────────────────────────────────────────────────────────────┐
│ LAYER 1: aa_citizens_bronze                                  │
│ Contains: aadhaar_hash, full_name, annual_income, land_acres │
│ Access: Internal pipeline only                               │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼ (NB02 transformation)
┌──────────────────────────────────────────────────────────────┐
│ LAYER 2: aa_citizens_silver                                  │
│ Contains: full_name, income_bracket, land_category           │
│ Drops: aadhaar_hash, annual_income, land_acres, dob          │
│ Access: Bot greeting logic, certificate generation           │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼ (NB02 view creation)
┌──────────────────────────────────────────────────────────────┐
│ LAYER 3: aa_citizens_for_llm (VIEW — PII FIREWALL)          │
│ Excludes: full_name (and everything dropped above)           │
│ Access: LLM matching, Vector Search, eligibility engine      │
│         The LLM NEVER sees a citizen's name or income        │
└──────────────────────────────────────────────────────────────┘
```

NB07 Section 8 includes a **runtime Unity Catalog assertion** that programmatically verifies `full_name` is NOT in the LLM view columns — proving the firewall, not just claiming it.

---

## 8. Delta Tables Reference

| Table | Layer | Partitioned By | Key Columns | Purpose |
|---|---|---|---|---|
| `aa_citizens_bronze` | Bronze | `district` | `citizen_id`, `aadhaar_hash`, `full_name`, raw financials | Raw synthetic citizen records |
| `aa_citizens_silver` | Silver | `district` | `citizen_id`, `full_name`, `income_bracket`, `land_category` | Transformed, PII-reduced citizens |
| `aa_citizens_for_llm` | View (Silver) | — | No `full_name`, no raw financials | PII Firewall — LLM-safe view |
| `aa_schemes_bronze` | Bronze | — | Raw Kaggle columns | Raw government schemes |
| `aa_schemes` | Silver | — | `scheme_id`, `short_code`, `eligibility_sql`, `benefit_type` | Structured scheme catalog |
| `aa_eligibility_results` | Gold | `district` | `citizen_id`, `scheme_id`, `is_notified`, `matched_at` | Citizen↔Scheme matches |
| `aa_adhikar_certificates` | Gold | — | `citizen_id`, `adhikar_certificate` (JSON), `generated_at` | AI-generated certificates |
| `aa_user_registry` | Operational | — | `citizen_id`, `chat_id`, `last_login` | Telegram↔Citizen ID mapping |
| `aa_life_events` | Operational | — | Life event triggers | NB07 life-event pulse |

---

## 9. Environment & Configuration

### Databricks
- **Catalog:** `workspace`
- **Schema:** `default`
- **Host:** `https://dbc-8d79a655-2501.cloud.databricks.com` (main) / `https://dbc-bedd193d-10dc.cloud.databricks.com` (alt)
- **LLM Endpoint:** `databricks-meta-llama-3-3-70b-instruct`
- **Vector Search Index:** `workspace.bronze.welfare_schemes_index`
- `spark.sql.shuffle.partitions` = 8 (tuned for 1,000-citizen dataset)

### External APIs
- **OpenAI:** `gpt-4` via `https://api.openai.com/v1/chat/completions` — certificate JSON structuring
- **Sarvam AI:** `https://api.sarvam.ai/translate` — Marathi/Hindi translation (`mr-IN`, `hi-IN`)
- **Telegram Bot API:** Token-based polling via `python-telegram-bot`

### Python Libraries
```
pyspark
python-telegram-bot
fpdf
requests
databricks-sdk
nest_asyncio
uuid, hashlib, json, asyncio, io, datetime
```

---

## 10. End-to-End Data Flow

```
1. NB01: Generate 1,000 citizen records → aa_citizens_bronze
2. NB02: PII mask + categorize → aa_citizens_silver
          ├── Enable CDF on silver
          └── Create aa_citizens_for_llm (PII firewall view)
3. NB03: Kaggle schemes → eligibility SQL predicates → aa_schemes
4. NB04: Tag-join citizens × schemes → aa_eligibility_results
5. NB05: Top 10 citizens → OpenAI + Sarvam AI → aa_adhikar_certificates
6. NB06: Eligibility pulse (MERGE) + Telegram push notifications
7. NB07: Interactive dashboard, CDF demo, time-travel, OPTIMIZE, displayHTML

Telegram Bot (always-on):
  Citizen sends ID → register_user() → aa_user_registry
  Citizen asks question → Vector Search + LLaMA 3.3 70B → text reply
  Citizen taps button → aa_adhikar_certificates → create_pdf() → document sent
```

---

## 11. Key Design Patterns & Fixes

### Fix 1 — Native Spark Instead of Python UDFs (NB03)
Python UDFs in Spark Connect (Serverless) carry serialization overhead and can fail unexpectedly. The eligibility predicate generation was refactored from `F.udf(map_eligibility, StringType())` to a native `F.when(...).when(...).otherwise(...)` chain — pure catalyst, zero serialization.

### Fix 2 — Explicit StructType for Spark Connect (Telegram Bot)
`spark.createDataFrame(list_of_dicts)` in Serverless requires remote schema inference over gRPC, which fails with `DATA_SOURCE_NOT_FOUND` / "unsupported" errors. The fix is to supply a `StructType` schema and pass a list-of-tuples (not list-of-dicts):
```python
mapping_data = [(str(citizen_id), str(chat_id), datetime.now())]
spark.createDataFrame(mapping_data, schema=USER_REGISTRY_SCHEMA)
```

### Fix 3 — Bot Session Stability (Telegram Bot)
Re-running the bot cell without stopping the old polling loop causes Telegram to return `409 Conflict`. A "Kill Old Sessions" cell explicitly calls:
```python
await app.updater.stop(); await app.stop(); await app.shutdown()
```
before each restart.

### Fix 4 — Schema Drift (NB07)
`ward_no` and `girl_child_age_years` were causing `DELTA_FAILED_TO_MERGE_FIELDS` because they were defined as `IntegerType` in some places and inferred as `LongType` by Spark. NB07 declares them consistently as `LongType` everywhere.

### Fix 5 — MERGE Instead of Append (NB06, NB07)
All trigger-based writes use `MERGE INTO` with `ON target.citizen_id = source.citizen_id AND target.scheme_id = source.scheme_id` to guarantee idempotency. Re-runs on the same data produce zero new rows.

---

## 12. How to Run

### Prerequisites
- Databricks workspace with Unity Catalog enabled (`workspace.default` accessible)
- Telegram Bot Token (create via @BotFather)
- OpenAI API key
- Sarvam AI API key
- Kaggle welfare schemes dataset loaded into `workspace.default.updated_data`
- Vector Search index created at `workspace.bronze.welfare_schemes_index`

### Execution Order

```bash
# Step 1 — Set up the Citizen data
Run NB01 (nb1.py)          → Creates aa_citizens_bronze

# Step 2 — Transform & build PII firewall
Run NB02 (nb2.py)          → Creates aa_citizens_silver + aa_citizens_for_llm

# Step 3 — Build the Schemes catalog
Run NB03 (nb3.py)          → Creates aa_schemes

# Step 4 — Match citizens to schemes
Run NB04 (nb4.py)          → Creates aa_eligibility_results

# Step 5 — Generate certificates
Run NB05 (nb5.py)          → Creates aa_adhikar_certificates

# Step 6 — Start proactive notifications
Run NB06 (nb6.py)          → Dispatches Telegram push alerts

# Step 7 — View the dashboard
Run NB07 (nb7.py)          → Interactive Databricks presentation layer

# Step 8 — Start the bot
Run Telegram Bot notebook  → Bot starts polling, citizens can interact
```

### Rerunning Safely
All notebooks are idempotent. Tables use `mode("overwrite")` for full refreshes and `MERGE INTO` for incremental updates. You can re-run any notebook without duplicating data.

---

*Built on Databricks Lakehouse · Delta Lake · Unity Catalog · Meta LLaMA 3.3 · Sarvam AI · OpenAI · Telegram Bot API*
