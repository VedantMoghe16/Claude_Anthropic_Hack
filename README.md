# ⚖️ Adhikar-Aina — Citizen Rights Operating System

> *"Government schemes should find the citizen — not the other way around."*

**Adhikar-Aina** (अधिकार-आईना, *Mirror of Rights*) is a full-stack platform that automatically matches Indian citizens to the government welfare schemes they are legally entitled to, generates official-looking eligibility certificates, and proactively pushes Telegram notifications when new policies arrive that match their profile.

It runs entirely **locally** — no cloud, no Databricks, no GPU required.

---

## Table of Contents

1. [What It Does](#1-what-it-does)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Prerequisites](#5-prerequisites)
6. [Installation](#6-installation)
7. [First-Time Setup](#7-first-time-setup)
8. [Running the Platform](#8-running-the-platform)
9. [Website — Usage Guide](#9-website--usage-guide)
10. [Telegram Bot — Command Reference](#10-telegram-bot--command-reference)
11. [Policy Notification Demo](#11-policy-notification-demo)
12. [Synthetic Citizen Dataset](#12-synthetic-citizen-dataset)
13. [Eligibility Matching Engine](#13-eligibility-matching-engine)
14. [REST API Reference](#14-rest-api-reference)
15. [Environment Variables](#15-environment-variables)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. What It Does

Most Indians never claim welfare benefits they are legally entitled to — not because they don't exist, but because the system is opaque, multilingual, and bureaucratically inaccessible. Adhikar-Aina flips this:

| Feature | Description |
|---|---|
| **Eligibility Matching** | Two-stage engine: rule-based filter (income, caste, land, occupation) + TF-IDF semantic re-ranking across 3,400+ real government schemes |
| **Adhikar Certificate** | PDF or HTML certificate listing matched schemes, legal rights, and the exact script to use when claiming benefits |
| **Voice-First Web Portal** | React app with voice input (STT) and text-to-speech (TTS) in 22+ Indian languages via Sarvam AI + OpenAI fallback |
| **Telegram Bot** | Citizens send their Aadhaar → bot replies with scheme list + downloadable PDF certificate |
| **Policy Notifications** | When a new scheme is added to the system, every eligible citizen with a linked Telegram account gets an instant notification |
| **Synthetic Dataset** | 5,000 realistic Indian citizen profiles across 16 states, proportionally distributed by population, with state-specific names, districts, caste distributions, and income patterns |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CITIZEN TOUCHPOINTS                      │
│                                                                 │
│   ┌──────────────────────┐      ┌─────────────────────────────┐ │
│   │   TELEGRAM BOT        │      │   WEB PORTAL                │ │
│   │   python-telegram-bot │      │   React 19 + Vite           │ │
│   │   Commands + PDF      │      │   Voice · 22 languages      │ │
│   │   Policy alerts       │      │   http://localhost:5173     │ │
│   └──────────┬────────────┘      └────────────┬────────────────┘ │
└──────────────┼─────────────────────────────────┼────────────────┘
               │ Telegram API                     │ HTTP/REST
               │                     ┌────────────▼──────────────┐
               │                     │   FastAPI BACKEND          │
               │                     │   Port 8000 · Uvicorn      │
               │                     │   /check-eligibility       │
               │                     │   /api/register-user       │
               │                     │   /api/get-results/:id     │
               │                     │   /api/add-scheme          │
               │                     │   /api/tts · /api/stt      │
               │                     └────────────┬──────────────┘
               │                                  │
               └──────────────────────────────────┘
                                   │
               ┌───────────────────▼────────────────────────────┐
               │              adhikar_local ENGINE               │
               │                                                 │
               │  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
               │  │ ingest.py│  │ match.py │  │ notifier.py │  │
               │  │ CSV→SQLite│  │ Rule +   │  │ Policy push │  │
               │  │ 5000     │  │ TF-IDF   │  │ via Telegram│  │
               │  │ citizens │  │ matching │  │ Bot API     │  │
               │  └────┬─────┘  └────┬─────┘  └─────────────┘  │
               │       │             │                           │
               │  ┌────▼─────────────▼──────────────────────┐   │
               │  │        SQLite  (adhikar.db)              │   │
               │  │  citizens · schemes · telegram_mapping   │   │
               │  └──────────────────────────────────────────┘   │
               │                                                 │
               │  ┌──────────────────────────────────────────┐   │
               │  │  TF-IDF Index (scheme_meta.pkl)          │   │
               │  │  sklearn TfidfVectorizer · 3,400 schemes │   │
               │  └──────────────────────────────────────────┘   │
               └─────────────────────────────────────────────────┘

External APIs:
  Sarvam AI  — Translation, TTS, STT (Indian languages)
  OpenAI     — TTS fallback (gpt-4o-mini-tts), STT (Whisper), GPT-4.1-mini
  Telegram   — Bot messaging + polling
```

---

## 3. Technology Stack

### Backend / Matching Engine

| Component | Technology |
|---|---|
| Web framework | FastAPI 0.116 + Uvicorn (ASGI) |
| Language | Python 3.12 |
| Database | SQLite (via `sqlite3` stdlib) |
| Semantic search | scikit-learn `TfidfVectorizer` + cosine similarity |
| PDF certificates | ReportLab |
| Data processing | pandas + numpy |
| Env management | python-dotenv |
| HTTP client | requests |

### Frontend

| Component | Technology |
|---|---|
| UI framework | React 19 |
| Build tool | Vite 8 |
| Routing | React Router 7 |
| Styling | Tailwind CSS 3 |
| HTTP client | Axios |
| i18n | Custom context + 22 JSON locale files |

### Telegram Bot

| Component | Technology |
|---|---|
| Bot framework | python-telegram-bot 21+ (async) |
| Translation | Sarvam AI (`mayura:v1`) |
| TTS | Sarvam AI (`bulbul:v1`) |

### External APIs

| API | Used For |
|---|---|
| Sarvam AI | Indian language translation, TTS (22 languages), STT |
| OpenAI | TTS fallback, Whisper STT, GPT-4.1-mini profile enrichment |
| Telegram Bot API | Bot messaging and polling |

---

## 4. Project Structure

```
Claude_Anthropic_Hack/
│
├── .env                          ← All API keys and tokens (root level)
├── start_backend.sh              ← Launch FastAPI backend
├── start_bot.sh                  ← Launch Telegram bot
├── start_frontend.sh             ← Launch React dev server
│
├── adhikar_local/                ← Core matching engine + bot
│   ├── config.py                 ← Paths, model names, API tokens
│   ├── dataset.py                ← 5,000-citizen synthetic generator (16 states)
│   ├── ingest.py                 ← CSV → SQLite (schemes + citizens)
│   ├── embed_schemes.py          ← Builds TF-IDF index over all schemes
│   ├── match.py                  ← Two-stage eligibility matching engine
│   ├── notifier.py               ← Policy notification engine
│   ├── certificate.py            ← PDF certificate generator (ReportLab)
│   ├── sarvam.py                 ← Sarvam AI client (translate / TTS / STT)
│   ├── bot.py                    ← Telegram bot (all handlers)
│   ├── pipeline.py               ← CLI orchestrator (--setup / --aadhar / --reset)
│   ├── requirements.txt
│   └── data/
│       ├── adhikar.db            ← SQLite database (auto-generated)
│       └── scheme_meta.pkl       ← TF-IDF index (auto-generated)
│
├── WEBSITE/
│   ├── data/
│   │   └── updated_data.csv      ← 3,400+ real Indian government schemes
│   │
│   ├── backend/
│   │   ├── app.py                ← FastAPI application (all endpoints)
│   │   └── requirements.txt
│   │
│   └── frontend/
│       ├── .env                  ← VITE_API_BASE_URL=http://127.0.0.1:8000
│       ├── package.json
│       ├── src/
│       │   ├── App.jsx
│       │   ├── pages/
│       │   │   ├── LandingPage.jsx
│       │   │   ├── LoginPage.jsx
│       │   │   ├── OnboardingPage.jsx   ← Voice-guided Q&A + eligibility check
│       │   │   └── DashboardPage.jsx    ← Scheme results + certificate download
│       │   ├── services/
│       │   │   └── api.js               ← All backend API calls
│       │   ├── components/
│       │   │   ├── VoiceQuestionCard.jsx
│       │   │   ├── SchemeCard.jsx
│       │   │   ├── AdhikarCertificateModal.jsx
│       │   │   └── ...
│       │   └── i18n/
│       │       └── locales/             ← 22 Indian language JSON files
│       └── ...
```

---

## 5. Prerequisites

- **Python 3.10+** (tested on 3.12)
- **Node.js 18+** and **npm**
- API keys (see [Environment Variables](#15-environment-variables)):
  - Telegram Bot token (from [@BotFather](https://t.me/BotFather))
  - Sarvam AI key (from [dashboard.sarvam.ai](https://dashboard.sarvam.ai))
  - OpenAI key (from [platform.openai.com](https://platform.openai.com))

---

## 6. Installation

### Python dependencies

```bash
# Install all Python dependencies from the matching engine
pip install -r adhikar_local/requirements.txt

# Install backend-specific deps
pip install -r WEBSITE/backend/requirements.txt
```

### Frontend dependencies

```bash
cd WEBSITE/frontend
npm install
```

---

## 7. First-Time Setup

Run the setup pipeline once to create the SQLite database, ingest the 3,400+ schemes from CSV, generate 5,000 synthetic citizens, and build the TF-IDF semantic index:

```bash
cd adhikar_local
python pipeline.py --setup
```

Expected output:
```
Setting up SQLite database...
Loading schemes from .../WEBSITE/data/updated_data.csv...
  3400 schemes ingested
Generating all-India citizen dataset (5,000 citizens across 16 states)...
  5000 citizens generated
Building TF-IDF index over 3400 schemes...
Saved → .../adhikar_local/data/scheme_meta.pkl
  Schemes : 3400
  Features: 20000

Setup complete.
Next: python pipeline.py --aadhar 999999999999
```

This creates two files that everything else depends on:
- `adhikar_local/data/adhikar.db` — SQLite database (citizens + schemes + Telegram mappings)
- `adhikar_local/data/scheme_meta.pkl` — Serialised TF-IDF vectorizer and matrix

To rebuild from scratch at any time:
```bash
python pipeline.py --reset   # delete DB + index
python pipeline.py --setup   # recreate everything
```

---

## 8. Running the Platform

The platform has three independent services. Open three terminal tabs:

### Terminal 1 — Backend API

```bash
./start_backend.sh
# or manually:
cd WEBSITE/backend && source ../../.env && uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Runs at: **http://127.0.0.1:8000**
Interactive API docs: **http://127.0.0.1:8000/docs**

### Terminal 2 — Frontend (React Dev Server)

```bash
./start_frontend.sh
# or manually:
cd WEBSITE/frontend && npm run dev
```

Runs at: **http://localhost:5173**

### Terminal 3 — Telegram Bot

```bash
./start_bot.sh
# or manually:
cd adhikar_local && source ../.env && python bot.py
```

> **Note:** Only one bot instance can run at a time. If you see a `409 Conflict` error, kill any other running instance with `pkill -9 -f "bot.py"` and restart.

---

## 9. Website — Usage Guide

Open **http://localhost:5173** in your browser.

### Flow

```
Landing Page → Login → Onboarding (Q&A) → Dashboard (Results + Certificate)
```

#### Step 1 — Landing Page
Introduction to the platform with language selection. Supports 22 Indian languages.

#### Step 2 — Login / Citizen Lookup
Enter an Aadhaar number to retrieve an existing citizen profile, or proceed as a new user.

**Demo Aadhaar numbers (pre-loaded in the database):**

| Aadhaar | Name | Profile |
|---|---|---|
| `999999999999` | Ramu Yadav, Varanasi, UP | Farmer · OBC · ₹1.2L/yr |
| `299223237613` | Devika Kumar, Shivamogga, KA | Entrepreneur · OBC · ₹1.26L/yr |
| `412933106111` | Kalyan Chamar, Madhubani, BR | Farmer · SC · ₹66.9K/yr |
| `898400899699` | Suresh Nayak, Mysuru, KA | Entrepreneur · GEN · ₹4.6L/yr |
| `547055029070` | Anita Srivastava, Bareilly, UP | Unemployed · OBC · ₹61.9K/yr |

#### Step 3 — Onboarding / Q&A
A voice-guided questionnaire collects:
- Support category (agriculture, education, social welfare, etc.)
- Annual income
- Occupation type
- Land holdings
- Caste category
- Girl child status

Each question has a speaker button — click it to hear the question read aloud in your selected language.

Voice input is also supported: click the microphone icon on any question to answer by speaking.

#### Step 4 — Dashboard
Displays all matched government schemes ranked by relevance. Each scheme card shows:
- Scheme name and ministry
- Benefit description
- Eligibility criteria
- "Get Certificate" button

#### Step 5 — Adhikar Certificate
Click "Get Certificate" on any scheme to generate an official eligibility certificate as an HTML document. The certificate includes:
- Citizen ID and scheme details
- Why you are eligible (income bracket, occupation, land category)
- Your legal rights (RTI, appeal process, legal aid contacts)
- Anti-corruption guidance (how to escalate if benefits are denied)

---

## 10. Telegram Bot — Command Reference

Find the bot on Telegram using the username registered with your token via @BotFather.

### Commands

| Command | Description |
|---|---|
| `/start` | Welcome message + language selection keyboard |
| `/language` | Change your language (10 supported: EN, HI, BN, MR, TA, TE, GU, KN, ML, PA) |
| `/demo` | Show 5 sample Aadhaar numbers you can test with |
| `/myid` | Show your Telegram Chat ID (needed for account linking) |
| `/link <citizen_id>` | Link your Telegram account to a citizen profile for notifications |
| `/help` | Full command reference |

### Aadhaar Lookup Flow

Send any 12-digit Aadhaar number as a plain message:

```
999999999999
```

The bot will:
1. Look up the citizen in the database
2. Run the eligibility matching engine
3. Send a summary of matched schemes
4. Attach a PDF Adhikar Certificate as a downloadable file

Example response:
```
Namaste Ramu Yadav!

You are eligible for 5 government scheme(s):
  1. OBC Agri Equipment Subsidy
  2. Small Farmer Income Support
  3. Agriculture Information Unit Scheme
  4. Floriculture Development Scheme
  5. State Rice Mission Scheme

Your certificate (with legal rights and claim script) is below.
Agar koi inkaar kare — yeh certificate legal proof hai.
```

### Multilingual Support

After `/start` or `/language`, a keyboard appears with 10 language options. Selecting a language translates all subsequent bot messages via Sarvam AI. The bot falls back to English if translation fails.

### Linking Your Account for Notifications

To receive proactive policy notifications:

```
/link CIT-00002
```

This links your current Telegram chat to the citizen with ID `CIT-00002` (Devika Kumar). When a new scheme is added that matches her profile, you will receive an automatic notification.

---

## 11. Policy Notification Demo

This demonstrates the core USP: when a new government policy is announced, every eligible citizen with a linked Telegram account receives an automatic notification.

### Step 1 — Link a Telegram account to a citizen

In Telegram, send:
```
/link CIT-00002
```

This links your chat to Devika Kumar (OBC entrepreneur, Shivamogga, Karnataka, income ₹1.26L).

### Step 2 — Add a new scheme and trigger notifications

```bash
cd adhikar_local
source ../.env
python notifier.py --demo
```

This injects the **"Karnataka OBC Women Entrepreneurship Grant"** scheme into the database and immediately notifies all eligible linked citizens.

Expected output:
```
Added scheme → Karnataka OBC Women Entrepreneurship Grant (SCH-DEMO-KARN-001)

Checking 5,000 citizens against: Karnataka OBC Women Entrepreneurship Grant
Telegram-linked citizens: 1
  → Notifying Devika Kumar (chat_id=<your_chat_id>)
    ✓ Sent

── Notification Summary ──────────────────
  Eligible citizens   : 44
  Notified via Telegram: 1
  No Telegram linked  : 43
  Failed to send      : 0
```

### Step 3 — Check Telegram

You receive:

> 🔔 **New Government Scheme Alert!**
>
> Namaste **Devika Kumar**!
>
> A new scheme has been added that you are eligible for:
>
> 📋 **Karnataka OBC Women Entrepreneurship Grant**
> 🏛 Karnataka State Government — OBC Development Corporation
>
> 💰 **Benefit:** One-time grant of Rs 50,000 for women OBC entrepreneurs to expand micro and small businesses. Includes free mentorship, subsidised GST registration, and priority access to government procurement tenders.
>
> *Send your Aadhaar number (2992XXXX7613) to get your Adhikar Certificate.*
>
> ⚖️ **Aapka Adhikar, Aapki Pehchaan**

### Via the Backend API

You can also add schemes and trigger notifications via the REST API:

```bash
curl -X POST http://127.0.0.1:8000/api/add-scheme \
  -H "Content-Type: application/json" \
  -d '{
    "scheme_name": "PM Ujjwala Yojana 3.0",
    "min_income": 0,
    "max_income": 200000,
    "occupation": "any",
    "category": "ANY",
    "benefit": "Free LPG connection and first refill for BPL households",
    "eligibility_text": "BPL households without existing LPG connection",
    "ministry": "Ministry of Petroleum and Natural Gas",
    "level": "Central",
    "tags": "lpg,fuel,women,bpl,central",
    "notify": true
  }'
```

### Dry Run (Preview Without Sending)

```bash
python notifier.py --demo --dry-run
```

Shows who would be notified without actually sending any Telegram messages.

### Notify for an Existing Scheme

```bash
python notifier.py --scheme-id SCH-DEMO-KARN-001
```

---

## 12. Synthetic Citizen Dataset

The 5,000 citizen dataset is generated by `dataset.py` using `generate_all(n=5000, seed=42)`. It covers 16 Indian states proportionally weighted by population:

| State | Pop. Weight | Districts (sample) |
|---|---|---|
| Uttar Pradesh | 16% | Lucknow, Varanasi, Agra, Kanpur |
| Maharashtra | 8.5% | Pune, Mumbai, Nashik, Nagpur |
| Bihar | 8% | Patna, Gaya, Muzaffarpur |
| West Bengal | 7% | Kolkata, Howrah, Malda |
| Madhya Pradesh | 5.5% | Bhopal, Indore, Jabalpur |
| Rajasthan | 5.5% | Jaipur, Jodhpur, Udaipur |
| Tamil Nadu | 5.5% | Chennai, Coimbatore, Madurai |
| Karnataka | 5% | Bengaluru, Mysuru, Hubballi |
| + 8 more states | remaining | ... |

Each citizen has state-specific first names, surnames, and district names. Economic attributes (income, land, occupation) are drawn from state-specific distributions — a farmer in Bihar has different income patterns than one in Maharashtra.

**Every generated field:**

| Field | Description |
|---|---|
| `citizen_id` | `CIT-00001` to `CIT-05000` |
| `aadhar` | 12-digit number (synthetic) |
| `name` | State-appropriate first name + surname |
| `district` | Real district within the state |
| `state` | One of 16 Indian states |
| `age` | 18–75 |
| `gender` | Male/Female (52/48 split) |
| `caste_category` | SC/ST/OBC/GEN (state-specific distribution) |
| `annual_income` | State-range specific, occupation-correlated |
| `occupation` | farmer/worker/entrepreneur/student/unemployed |
| `land_acres` | 0.0–10.0, occupation-correlated |
| `has_girl_child` | Boolean, age-gated |
| `household_size` | 2–8 |
| `has_bpl_card` | Correlated with income + household size |
| `housing_status` | kutcha/semi_pucca/pucca |
| `employment_days` | 0–300 |
| `income_bracket` | EWS/LIG/MIG/HIG (derived) |
| `land_category` | marginal/small/medium/large (derived) |
| `citizen_tags` | Comma-separated semantic tags |

The first record (`CIT-00001`) is always pinned to **Ramu Yadav** with Aadhaar `999999999999` — a predictable test record for demos.

---

## 13. Eligibility Matching Engine

The matching engine in `match.py` runs in two stages:

### Stage 1 — Rule-Based Filter (pandas)

Deterministic boolean mask on the full schemes table:

```
income >= scheme.min_income
income <= scheme.max_income
land   <= scheme.max_land
occupation == scheme.occupation OR scheme.occupation == "any"
caste      == scheme.category   OR scheme.category   == "ANY"
```

This typically reduces ~3,400 schemes to a few dozen candidates per citizen.

### Stage 2 — TF-IDF Semantic Re-ranking (scikit-learn)

The citizen's profile is serialised into a query string:
```
"farmer obc lig small varanasi uttar pradesh farmer,low_income,agriculture,obc"
```

This is transformed using the pre-fitted `TfidfVectorizer` and cosine-similarity-ranked against the TF-IDF matrix of all scheme texts (name × 2 + eligibility text + tags × 2 + category + details).

The top-N schemes (default 5) are returned, sorted by semantic relevance score.

### Scheme Data

The scheme database is sourced from `WEBSITE/data/updated_data.csv` — a curated dataset of 3,400+ real Indian government schemes at Central and State levels. Each scheme is parsed to extract:
- `min_income` / `max_income` (regex-parsed from eligibility text)
- `max_land` (regex-parsed)
- `occupation` (keyword match: farmer, student, artisan, etc.)
- `category` (SC/ST/OBC/GEN/ANY)

---

## 14. REST API Reference

Base URL: `http://127.0.0.1:8000`

Interactive docs (Swagger UI): `http://127.0.0.1:8000/docs`

---

### `POST /api/register-user`
Register a new citizen and get a citizen_id.

**Request body:**
```json
{
  "name": "Priya Sharma",
  "income": 180000,
  "occupation": "farmer",
  "land_acres": 2.5,
  "category": "OBC",
  "state": "Rajasthan",
  "district": "Jaipur",
  "age": 34,
  "gender": "Female",
  "household_size": 5,
  "has_girl_child": true
}
```

**Response:**
```json
{ "ok": true, "citizen_id": "TEST-a3f1c2" }
```

---

### `POST /check-eligibility`
Register citizen + immediately return matched schemes in one call.

**Request body:** same fields as `/api/register-user` plus optional `limit` (default 5).

**Response:**
```json
{
  "citizen_id": "TEST-a3f1c2",
  "eligible_schemes": [
    {
      "scheme_id": "SCH-XXXXXXXX",
      "scheme_name": "PM Kisan Samman Nidhi",
      "benefit": "Rs 6,000/year direct cash transfer",
      "ministry": "Central Government — Agriculture",
      "scheme_category": "Agriculture,Rural & Environment",
      "eligibility_text": "Small and marginal farmers...",
      "level": "Central"
    }
  ],
  "eligibility_explanation": {
    "income_bracket": "LIG",
    "occupation_category": "farmer",
    "land_category": "small"
  }
}
```

---

### `GET /api/get-results/{citizen_id}`
Return scheme matches for a previously registered citizen.

```bash
curl http://127.0.0.1:8000/api/get-results/CIT-00001
```

---

### `GET /api/citizen/{citizen_id}`
Retrieve full citizen profile.

```bash
curl http://127.0.0.1:8000/api/citizen/CIT-00001
```

---

### `GET /api/demo-citizens`
Returns 5–6 demo citizens with their Aadhaar numbers for testing.

```bash
curl http://127.0.0.1:8000/api/demo-citizens
```

---

### `POST /api/add-scheme`
Add a new scheme to the database. Set `notify: true` to immediately push Telegram notifications to all eligible linked citizens.

**Request body:**
```json
{
  "scheme_name": "PM Ujjwala Yojana 3.0",
  "min_income": 0,
  "max_income": 200000,
  "occupation": "any",
  "category": "ANY",
  "benefit": "Free LPG connection and first refill",
  "eligibility_text": "BPL households without LPG connection",
  "ministry": "Ministry of Petroleum and Natural Gas",
  "level": "Central",
  "tags": "lpg,bpl,women,central",
  "notify": true
}
```

**Response:**
```json
{
  "ok": true,
  "scheme_id": "SCH-AB12CD34EF",
  "scheme_name": "PM Ujjwala Yojana 3.0",
  "notification_stats": {
    "total_eligible": 312,
    "notified": 2,
    "failed": 0,
    "skipped_no_telegram": 310
  }
}
```

---

### `POST /api/tts`
Convert text to speech. Uses Sarvam AI for Indian languages; falls back to OpenAI TTS.

**Request body:**
```json
{ "text": "Namaste, aap PM Kisan ke liye paatra hain.", "language": "hi" }
```

**Response:** Audio bytes (`audio/wav` for Indian languages, `audio/mpeg` for OpenAI fallback).

---

### `POST /api/stt`
Convert speech to text. Uses Sarvam AI for Indian languages; falls back to OpenAI Whisper.

**Request:** `multipart/form-data` with a `file` field (WAV/MP3) and optional `language` query param (default `hi-IN`).

---

### `POST /api/adhikar-certificate`
Generate an HTML Adhikar Certificate for a specific scheme.

**Request body:**
```json
{
  "citizen_id": "CIT-00001",
  "scheme_name": "PM Kisan Samman Nidhi",
  "scheme_description": "Rs 6,000/year for small farmers",
  "language": "en",
  "eligibility_criteria": { "income_bracket": "LIG", "occupation_category": "farmer" },
  "citizen_profile": { "district": "Varanasi", "annual_income": 120000 }
}
```

---

### `POST /api/link-telegram`
Link a citizen_id to a Telegram chat_id for notifications.

```json
{ "citizen_id": "CIT-00002", "telegram_chat_id": "123456789" }
```

---

## 15. Environment Variables

All variables live in `.env` at the project root. Copy or edit this file before running.

```bash
# ── Telegram Bot ──────────────────────────────────────────────
TELEGRAM_TOKEN=<your-bot-token>
# Get from @BotFather on Telegram → /newbot

# ── OpenAI ───────────────────────────────────────────────────
OPENAI_API_KEY=<your-openai-key>
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
OPENAI_CHAT_MODEL=gpt-4.1-mini

# ── Sarvam AI (Indian language STT/TTS/Translation) ──────────
SARVAM_API_KEY=<your-sarvam-key>
# Get from https://dashboard.sarvam.ai
```

### Which keys are required?

| Key | Required For | Fallback |
|---|---|---|
| `TELEGRAM_TOKEN` | Telegram bot | Bot will not start without it |
| `SARVAM_API_KEY` | Indian language TTS/STT/translation | Falls back to browser TTS / OpenAI |
| `OPENAI_API_KEY` | TTS fallback, Whisper STT, GPT enrichment | Features degrade gracefully |

The eligibility matching engine, PDF generation, and core website flow all work with **no API keys** — they use only local SQLite + TF-IDF.

---

## 16. Troubleshooting

### Bot: `409 Conflict — terminated by other getUpdates request`

Two bot instances are running simultaneously. Kill them all and restart:
```bash
pkill -9 -f "bot.py"
./start_bot.sh
```

### Backend: `ModuleNotFoundError: No module named 'match'`

The `adhikar_local` directory is not on the Python path. Either run from the project root with the start script, or ensure `adhikar_local/data/adhikar.db` and `scheme_meta.pkl` exist:
```bash
cd adhikar_local && python pipeline.py --setup
```

### Backend: `No schemes found` / empty results

The TF-IDF index is missing. Rebuild it:
```bash
cd adhikar_local && python embed_schemes.py
```

### Frontend: blank page / network errors

1. Confirm the backend is running on port 8000: `curl http://127.0.0.1:8000/docs`
2. Check `WEBSITE/frontend/.env` contains `VITE_API_BASE_URL=http://127.0.0.1:8000`
3. Restart the Vite dev server after any `.env` change

### TTS/STT not working

- Check `SARVAM_API_KEY` is set: `echo $SARVAM_API_KEY`
- Check `OPENAI_API_KEY` is set as fallback
- The UI will silently fall back to browser-native `speechSynthesis` if both fail

### Database needs to be rebuilt

```bash
cd adhikar_local
python pipeline.py --reset   # wipes DB + index
python pipeline.py --setup   # regenerates everything (takes ~30s)
```

### Test a specific Aadhaar via CLI (no bot needed)

```bash
cd adhikar_local
python pipeline.py --aadhar 999999999999
```

---

## Demo Quickstart

```bash
# 1. Install deps
pip install -r adhikar_local/requirements.txt
pip install -r WEBSITE/backend/requirements.txt
cd WEBSITE/frontend && npm install && cd ../..

# 2. One-time DB + index setup
cd adhikar_local && python pipeline.py --setup && cd ..

# 3. Start everything (3 terminals)
./start_backend.sh    # Terminal 1 → http://127.0.0.1:8000
./start_frontend.sh   # Terminal 2 → http://localhost:5173
./start_bot.sh        # Terminal 3 → Telegram bot

# 4. Try the website
# Open http://localhost:5173 and enter Aadhaar: 999999999999

# 5. Try the bot
# Telegram → /start → /demo → send 999999999999

# 6. Demo policy notification
# Telegram → /link CIT-00002
# New terminal: cd adhikar_local && source ../.env && python notifier.py --demo
```

---

*Built for the Claude Hackathon by Anthropic. Adhikar-Aina is open infrastructure for citizen rights.*
