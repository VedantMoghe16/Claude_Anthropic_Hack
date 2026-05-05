# Adhikar: Government Scheme Eligibility Assistant

> A comprehensive, multilingual citizen-centric portal for discovering and accessing government welfare schemes with voice-enabled accessibility across 22+ Indian languages.

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Voice (STT/TTS) Integration](#voice-stttts-integration)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

**Adhikar** is a government welfare scheme eligibility assistant designed to democratize access to citizen benefits across India. The platform leverages advanced AI and natural language processing to:

- **Identify Eligible Schemes**: Match citizen profiles against 4,680+ government schemes
- **Voice-First Accessibility**: Support voice input/output in 22+ Indian languages
- **Intelligent Matching**: Use Databricks and AI to determine scheme eligibility
- **Multilingual Support**: Complete UI and documentation in Indian languages
- **Legal Empowerment**: Provide detailed eligibility certificates and legal rights information

### Problem Statement
Millions of Indians are unaware of welfare schemes they're entitled to. Government schemes are scattered across multiple websites, lack unified information, and are often inaccessible to those with limited literacy or internet skills.

### Solution
Adhikar provides a single platform where citizens can:
1. Answer questions about their profile via voice
2. Instantly discover eligible government schemes
3. Access scheme details in their preferred language
4. Understand their legal rights and appeal procedures
5. Receive certificates of eligibility

---

## ✨ Key Features

### 1. Multilingual Voice Interface
- **Speech-to-Text (STT)** using OpenAI Whisper API
- **Text-to-Speech (TTS)** for question narration
- **Real-time transcription** with language detection
- Support for 22+ Indian languages:
  - Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati
  - Kannada, Malayalam, Odia, Punjabi, Urdu, Assamese
  - Nepali, Konkani, Maithili, Manipuri, Sanskrit
  - Santhali, Sindhi, Dogri, Kashmiri, Bodo

### 2. Government Scheme Database
- **4,680+ schemes** in centralized database
- **650+ Central Government schemes**
- **4,020+ State Government schemes**
- Real-time scheme database from official sources
- Scheme categories: Social Security, Health, Education, Employment, Agriculture, etc.

### 3. Intelligent Eligibility Matching
- AI-powered eligibility engine using Databricks
- Matches citizen profiles against scheme criteria
- Real-time eligibility determination
- Detailed eligibility explanations
- Scheme benefit amount calculations

### 4. Legal Rights & Protections
- Appeal procedures documentation
- Ombudsman contact information
- RTI (Right to Information) guidance
- Legal aid resources
- Disability rights information

### 5. Comprehensive Accessibility
- Voice-only interface for illiterate users
- Large text and high contrast modes
- Screen reader compatibility
- Mobile-responsive design
- Offline documentation support

---

## 🏗️ System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                              │
│  Web Browser (React 19.2.4 + Vite 8.0.3)                        │
└──────────────────┬──────────────────────────────────────────────┘
                   │ HTTPS/REST API (Port 5173)
                   ↓
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                            │
│  FastAPI 0.116.1 (Python 3.12+) - Port 8000                     │
│  Uvicorn ASGI Server                                            │
└──────────────────┬──────────────────────────────────────────────┘
                   │
        ┌──────────┼──────────┬────────────┬──────────┐
        ↓          ↓          ↓            ↓          ↓
    ┌────────────────────────────────┐  ┌──────────────────┐
    │  DATABRICKS PLATFORM            │  │  OpenAI APIs     │
    │  - Schemes Database             │  │  - STT           │
    │  - Citizens Registry            │  │  - TTS           │
    │  - Eligibility Engine           │  │  - Chat/GPT      │
    │  - Results Storage              │  │                  │
    └────────────────────────────────┘  └──────────────────┘
```

### Data Flow

```
1. USER REGISTRATION
   Citizen Info → Frontend Form → Backend /api/register-user
   → Databricks (Bronze Layer) → SQL Storage

2. ELIGIBILITY MATCHING
   Citizen Profile → Eligibility Engine → Databricks Query
   → Match against Schemes Table → Return Results

3. VOICE INTERACTION
   User speaks → Browser captures audio → /api/stt endpoint
   → OpenAI Whisper API → Transcribed text → Form update

4. CERTIFICATE GENERATION
   Matched Schemes → Backend processing → PDF Generation
   → /api/adhikar-certificate endpoint → Return certificate
```

### Component Architecture

| Layer | Components | Technology | Purpose |
|-------|-----------|-----------|---------|
| **Presentation** | React Components, Pages, UI | React 19, Vite, Tailwind CSS | User interface & interaction |
| **API Gateway** | FastAPI app, Routes, Middleware | FastAPI 0.116, Uvicorn | Request routing & processing |
| **Business Logic** | Eligibility Engine, Matching Algorithm | Python 3.12, Pandas | Core application logic |
| **Data Access** | Databricks SQL Connector | databricks-sql-connector 3.5 | Database operations |
| **External Services** | OpenAI Client, STT/TTS APIs | openai>=1.59.9 | AI services integration |
| **Storage** | Databricks Lakehouse | Delta Lake, SQL Tables | Persistent data storage |

---

## 🛠️ Technology Stack

### Frontend Stack

| Library | Version | Purpose |
|---------|---------|---------|
| React | 19.2.4 | UI framework & component model |
| Vite | 8.0.3 | Build tool & dev server |
| React Router | 7.13.2 | SPA routing & navigation |
| Tailwind CSS | 3.4.17 | Utility-first CSS styling |
| Axios | 1.14.0 | HTTP client for API calls |
| PostCSS | 8.4.1 | CSS transformation tool |

### Backend Stack

| Library | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.116.1 | Web framework & API server |
| Uvicorn | 0.35.0 | ASGI server implementation |
| Pydantic | 2.11.7 | Data validation & serialization |
| Python | 3.12+ | Runtime environment |
| python-dotenv | 1.0.1 | Environment variable management |
| OpenAI | ≥1.59.9 | AI/ML APIs (STT, TTS) |
| databricks-sql-connector | 3.5.0 | Databricks database connector |

### Data & Orchestration

| Service | Purpose |
|---------|---------|
| Databricks | Data warehouse & ETL platform |
| Delta Lake | ACID transactions on data lake |
| Databricks SQL | SQL query engine on Delta Lake |
| Spark | Distributed processing (implicit) |

---

## 📋 Prerequisites

### System Requirements

- **OS**: macOS 12+, Ubuntu 20+, or Windows 11+
- **CPU**: 4+ cores (8+ cores recommended for development)
- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 20GB free space
- **Network**: Internet connection for APIs and Databricks access

### Software Dependencies

```bash
# Check versions
python3 --version       # Must be ≥ 3.12.0
node --version          # Must be ≥ 18.0.0
npm --version           # Must be ≥ 8.0.0
```

### Required API Keys & Credentials

#### 1. OpenAI API Key
- **URL**: https://platform.openai.com/api-keys
- **Cost**: ~$0.02/min STT, ~$0.015/1000 chars TTS
- **Budget**: $50-100/month recommended
- **Format**: Key starts with `sk-proj-`

#### 2. Databricks Credentials
- **Workspace URL**: `https://your-instance.databricks.com`
- **Access Token**: Personal access token from Databricks UI
- **Warehouse ID**: SQL warehouse identifier
- **Catalog**: Usually `workspace` or `main`
- **Schema**: Default schema for tables

---

## 🚀 Installation & Setup

### Step 1: Clone Repository

```bash
# Navigate to desktop or desired directory
cd ~/Desktop

# Clone the repository
git clone https://github.com/your-org/bharatbricks-hackathon.git

# Navigate into project
cd bharatbricks_hackathon
pwd  # Verify you're in the right directory
```

### Step 2: Backend Setup

```bash
# Enter backend directory
cd backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or for Windows:
# venv\Scripts\activate

# Upgrade pip to latest version
pip install --upgrade pip setuptools wheel

# Install all dependencies
pip install -r requirements.txt

# Verify critical packages installed
pip list | grep -E "fastapi|openai|databricks"
```

**Expected Output**:
```
databricks-sql-connector    3.5.0
fastapi                     0.116.1
openai                      1.59.9 (or higher)
```

### Step 3: Frontend Setup

```bash
# From project root, navigate to frontend
cd ../frontend  # Go back to root, then into frontend

# Install npm packages from package.json
npm install

# Verify critical packages
npm list react vite tailwindcss

# Clear cache if needed
npm cache clean --force
```

### Step 4: Environment Configuration

```bash
# From project root directory
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use VS Code: code .env

# Verify all required variables are set
grep -E "OPENAI|DATABRICKS" .env | grep -v "^#"
```

**Complete .env Configuration**:

```bash
# ============================================
# OPENAI CONFIGURATION (Required for STT/TTS)
# ============================================
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
OPENAI_TTS_MODEL=gpt-4o-mini
OPENAI_CHAT_MODEL=gpt-4o-mini

# ============================================
# DATABRICKS CONFIGURATION
# ============================================
DATABRICKS_SERVER_HOSTNAME=your-workspace.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_ACCESS_TOKEN=dapi1234567890abcdef
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=adhikar

# ============================================
# TABLE NAMES
# ============================================
DATABRICKS_SCHEMES_TABLE=schemes_clean
DATABRICKS_CITIZENS_TABLE=citizens_registry
DATABRICKS_RESULTS_TABLE=eligibility_results

# ============================================
# FRONTEND CONFIGURATION
# ============================================
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## ▶️ Running the Application

### Method 1: Production Build (Recommended)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python3 << 'PYSCRIPT'
import uvicorn
from app import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
PYSCRIPT
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run build  # This takes ~30-60 seconds

# Serve the built files
cd dist
python3 -m http.server 5173
```

**Verify Both Services Are Running:**
```bash
# Terminal 3: Verify backend
curl -s http://127.0.0.1:8000/docs | head -5

# Terminal 3: Verify frontend
curl -s http://localhost:5173/ | grep -o "<title>.*</title>"

# Open in browser
open http://localhost:5173
```

### Method 2: Development Mode

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python3 << 'PYSCRIPT'
import uvicorn
from app import app
uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
PYSCRIPT
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev  # Starts Vite dev server with hot module replacement
```

**Access:**
- Frontend (with hot reload): http://localhost:5173
- API Documentation: http://127.0.0.1:8000/docs

### Method 3: Docker (Future)

```dockerfile
# Coming soon!
```

---

## 📚 API Documentation

### Interactive Swagger UI
**URL**: http://127.0.0.1:8000/docs

### Core REST Endpoints

#### 1. Register Citizen

```http
POST /api/register-user
Content-Type: application/json

Request Body:
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

#### 2. Get Eligibility Results

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
    },
    {
      "scheme_id": "SCH-002",
      "scheme_name": "PM-JAY Health Insurance",
      "eligible": true,
      "annual_benefit": "Full coverage",
      "eligibility_reason": "Income below threshold"
    }
  ],
  "total_eligible": 24,
  "total_annual_benefit": 450000
}
```

#### 3. Speech-to-Text (STT)

```http
POST /api/stt
Content-Type: multipart/form-data

Form Data:
- file: <audio file (WAV, MP3, M4A)>
- language: "hi" (optional, auto-detected)

Response:
{
  "ok": true,
  "text": "मेरा नाम राज है",
  "language": "hi",
  "confidence": 0.95
}
```

#### 4. Text-to-Speech (TTS)

```http
POST /api/tts
Content-Type: application/json

Request Body:
{
  "text": "आपकी वार्षिक आय क्या है?",
  "language": "hi"
}

Response: <MP3 Audio Stream>
```

#### 5. Generate Adhikar Certificate

```http
POST /api/adhikar-certificate
Content-Type: application/json

Request Body:
{
  "citizen_id": "CITZ-1234567890",
  "format": "pdf"
}

Response: <PDF Document>
```

---

## 🎤 Voice (STT/TTS) Integration

### Speech-to-Text (STT) - OpenAI Whisper API

#### How It Works

```
User speaks into microphone
        ↓
Browser Web Audio API captures audio
        ↓
Sends audio to /api/stt endpoint
        ↓
Backend sends to OpenAI Whisper API
        ↓
Whisper transcribes audio to text
        ↓
Returns text to frontend
        ↓
Text updates form field
```

#### Supported Languages
English, Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Odia, Punjabi, Urdu, Assamese, Nepali, Konkani, Maithili, Manipuri, Sanskrit, Santhali, Sindhi, Dogri, Kashmiri, Bodo

#### Backend Implementation

**File**: [backend/app.py](backend/app.py#L722-L768)

```python
from openai import OpenAI

openai_client = OpenAI(api_key=OPENAI_API_KEY)

@app.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """Convert speech to text using OpenAI Whisper."""
    try:
        audio_content = await file.read()
        
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=(file.filename or "audio.wav", audio_content),
            response_format="json",
            timeout=45.0,
        )
        
        return {
            "ok": True,
            "text": transcript.text.strip()
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

#### Frontend Implementation

**File**: [frontend/src/components/VoiceQuestionCard.jsx](frontend/src/components/VoiceQuestionCard.jsx)

```javascript
const startRecording = async () => {
  if (!isAudioSupported()) {
    setError("Your browser doesn't support audio recording");
    return;
  }
  
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    
    const mediaRecorder = new MediaRecorder(stream);
    const audioChunks = [];
    
    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      const result = await requestSpeechToText(blob);
      onChange(result.text);
    };
    
    mediaRecorder.start();
    setIsRecording(true);
  } catch (err) {
    setError("Microphone access denied. Please allow microphone access.");
  }
};
```

#### Cost Analysis

| Usage Scenario | Duration | Frequency | Monthly Cost |
|---|---|---|---|
| Single Question | 30 sec | 1x | $0.01 |
| Full Onboarding | 5 min | 1x/user | $0.10 |
| 100 Citizens | 500 min | N/A | $10.00 |
| 10,000 Citizens | 50,000 min | N/A | $1,000.00 |

**Monthly Budget Recommendation**: $50-100

---

## 📁 Project Structure

```
bharatbricks_hackathon/
│
├── README.md                          # Project documentation
├── .env                               # Environment variables (GITIGNORE)
├── .env.example                       # Environment template
│
├── backend/                           # FastAPI Application
│   ├── app.py                         # Main FastAPI application
│   ├── requirements.txt               # Python dependencies
│   ├── venv/                          # Python virtual environment
│   │   └── lib/python3.12/site-packages/
│   └── __pycache__/
│
├── frontend/                          # React Application
│   ├── src/
│   │   ├── main.jsx                   # React entry point
│   │   ├── App.jsx                    # Root React component
│   │   ├── App.css                    # Root styles
│   │   ├── index.css                  # Global styles
│   │   │
│   │   ├── components/                # Reusable components
│   │   │   ├── VoiceQuestionCard.jsx  # Voice input component with STT
│   │   │   ├── SchemeCard.jsx         # Scheme display component
│   │   │   ├── SchemeDetailsModal.jsx # Scheme details modal
│   │   │   ├── CitizenInfoModal.jsx   # Citizen profile modal
│   │   │   ├── AdhikarCertificateModal.jsx  # Certificate display
│   │   │   ├── LanguageSwitcher.jsx   # Language selection
│   │   │   ├── LoadingPanel.jsx       # Loading indicator
│   │   │   └── ErrorBoundary.jsx      # Error fallback
│   │   │
│   │   ├── pages/                     # Page components
│   │   │   ├── LandingPage.jsx        # Home/intro page
│   │   │   ├── LoginPage.jsx          # Login page
│   │   │   ├── OnboardingPage.jsx     # User onboarding
│   │   │   └── DashboardPage.jsx      # Results dashboard
│   │   │
│   │   ├── services/
│   │   │   └── api.js                 # API client (Axios)
│   │   │
│   │   ├── context/                   # State management
│   │   │   ├── AppContext.jsx         # Context provider
│   │   │   ├── appContextStore.js     # Zustand store
│   │   │   └── useAppContext.js       # Custom hook
│   │   │
│   │   ├── i18n/                      # Internationalization
│   │   │   ├── LanguageContext.jsx    # Language state
│   │   │   ├── languages.js           # Language definitions
│   │   │   ├── useLanguage.js         # Language hook
│   │   │   ├── useTranslation.js      # Translation hook
│   │   │   ├── voiceConfig.js         # Voice settings per language
│   │   │   └── locales/               # Translation JSON files
│   │   │       ├── en.json            # English
│   │   │       ├── hi.json            # Hindi
│   │   │       ├── ta.json            # Tamil
│   │   │       ├── te.json            # Telugu
│   │   │       ├── bn.json            # Bengali
│   │   │       ├── mr.json            # Marathi
│   │   │       ├── gu.json            # Gujarati
│   │   │       ├── kn.json            # Kannada
│   │   │       ├── ml.json            # Malayalam
│   │   │       ├── or.json            # Odia
│   │   │       ├── pa.json            # Punjabi
│   │   │       ├── ur.json            # Urdu
│   │   │       ├── as.json            # Assamese
│   │   │       ├── ne.json            # Nepali
│   │   │       └── [18 more languages]
│   │   │
│   │   ├── data/
│   │   │   ├── schemes.js             # Scheme definitions
│   │   │   └── questions.js           # Onboarding questions
│   │   │
│   │   ├── utils/
│   │   │   └── profile.js             # User profile utilities
│   │   │
│   │   └── assets/                    # Images, icons
│   │
│   ├── public/                        # Static files
│   ├── dist/                          # Built output (after npm run build)
│   ├── vite.config.js                 # Vite configuration
│   ├── tailwind.config.js             # Tailwind CSS config
│   ├── postcss.config.js              # PostCSS config
│   ├── eslint.config.js               # ESLint rules
│   ├── package.json                   # NPM dependencies
│   └── package-lock.json              # Locked versions
│
├── databricks/                        # Data Processing Scripts
│   ├── 01_bronze_citizens.py          # Stage 1: Raw data ingestion
│   ├── 02_silver_processing.py        # Stage 2: Data cleaning
│   ├── 03_schemes_engine.py           # Stage 3: Scheme categorization
│   ├── 04_eligibility_matching.py     # Stage 4: Eligibility scoring
│   ├── 05_adhikar_certificates.py     # Stage 5: Certificate generation
│   ├── 06_automation_triggers.py      # Stage 6: Automation workflows
│   └── __pycache__/
│
├── data/                              # Sample Data
│   └── updated_data.csv               # Test citizen data
│
├── STT_SETUP.md                       # STT Integration Guide
├── STT_TESTING.md                     # STT Testing Guide
└── VERIFY_DATABRICKS.md               # Databricks verification guide
```

---

## 🔄 Development Workflow

### Development Setup

```bash
# Terminal 1: Backend with auto-reload
cd backend
source venv/bin/activate
python3 -c "
import uvicorn
from app import app

uvicorn.run(
    app,
    host='127.0.0.1',
    port=8000,
    reload=True,
    log_level='debug'
)"

# Terminal 2: Frontend with hot module replacement
cd frontend
npm run dev

# Terminal 3: (Optional) Monitor Databricks
cd databricks
python3 01_bronze_citizens.py
```

### Code Changes Workflow

#### Backend Changes

1. Edit `backend/app.py`
2. File auto-reloads (watch for "Uvicorn restarted with reload" message)
3. Test via http://127.0.0.1:8000/docs

#### Frontend Changes

1. Edit component in `frontend/src/`
2. Vite hot module replacement applies changes instantly
3. See changes in browser immediately

#### Style Changes

1. Edit TailwindCSS classes in components
2. PostCSS processes on save
3. Browser auto-refreshes

### Testing Workflow

```bash
# Frontend linting
npm run lint

# Backend syntax check
python -m py_compile app.py

# Manual component testing
1. Open http://localhost:5173
2. Navigate to test page
3. Interact with components
4. Check browser console (F12)
5. Check network tab for API calls
```

### Commit & Deployment

```bash
# Check changes
git status

# Stage changes
git add backend/app.py frontend/src/components/VoiceQuestionCard.jsx

# Commit with descriptive message
git commit -m "feat: improve voice input accuracy with echo cancellation"

# Push to feature branch
git push origin feature/voice-improvements

# Create Pull Request for code review
```

---

## 🐛 Troubleshooting

### Backend Troubleshooting

#### Issue: "ModuleNotFoundError: No module named 'openai'"

```bash
# Solution 1: Check virtual environment
which python3  # Should show path with /venv/

# Solution 2: Reinstall openai
source venv/bin/activate
pip install --upgrade openai>=1.59.9

# Solution 3: Verify installation
python3 -c "from openai import OpenAI; print('OK')"
```

#### Issue: "Port 8000 already in use"

```bash
# Find process using port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
uvicorn app:app --port 8001
```

#### Issue: "Databricks connection refused"

```bash
# Check credentials in .env
grep DATABRICKS .env

# Test connection
python3 << 'TEST'
from databricks import sql
conn = sql.connect(
    server_hostname="xxx.databricks.com",
    http_path="/sql/1.0/warehouses/xxx",
    personal_access_token="dapixxx"
)
print("Connection OK")
TEST
```

### Frontend Troubleshooting

#### Issue: "npm: command not found"

```bash
# Install Node.js
brew install node  # macOS
sudo apt install nodejs npm  # Linux
# Windows: Download from nodejs.org

# Verify
npm --version
```

#### Issue: "npm ERR! Missing script: dev"

```bash
# Check package.json
grep '"dev"' frontend/package.json

# Reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Try again
npm run dev
```

#### Issue: "Blank page / 404 errors"

```bash
# Verify backend running
curl http://127.0.0.1:8000/docs

# Build frontend
npm run build

# Verify build output
ls -la frontend/dist/

# Serve dist
cd frontend/dist
python3 -m http.server 5173
```

### Voice (STT/TTS) Troubleshooting

#### Issue: "Microphone permission denied"

```
Browser Message: "Permission denied"

Solution:
1. Click browser URL bar → show site info
2. Permissions → Microphone → Allow
3. Refresh page
4. Try recording again
```

#### Issue: "Empty transcription"

```
Solution:
1. Speak clearly for at least 2-3 seconds
2. Reduce background noise
3. Test with browser's built-in recorder first
4. Check OpenAI API status
```

#### Issue: "API key not set"

```bash
# Verify .env file
cat .env | grep OPENAI_API_KEY

# If empty:
1. Get key from https://platform.openai.com/api-keys
2. Edit .env
3. Add: OPENAI_API_KEY=sk-proj-...
4. Save and restart backend
```

#### Issue: "Quota exceeded" (OpenAI)

```
Solution:
1. Check billing at platform.openai.com/account/billing
2. Set usage limits in account settings
3. Monitor API usage
4. Upgrade API plan if needed
```

---

## 📖 Additional Documentation

- **STT Integration**: See [STT_SETUP.md](STT_SETUP.md)
- **STT Testing**: See [STT_TESTING.md](STT_TESTING.md)
- **Databricks Setup**: See [VERIFY_DATABRICKS.md](VERIFY_DATABRICKS.md)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and test thoroughly
4. Commit with clear messages: `git commit -m "feat: description"`
5. Push to your branch: `git push origin feature/your-feature`
6. Create Pull Request with detailed description

---

## 📞 Support & Contact

- **API Documentation**: http://127.0.0.1:8000/docs
- **Frontend**: http://localhost:5173
- **Issues**: GitHub Issues
- **OpenAI Docs**: https://platform.openai.com/docs
- **Databricks Docs**: https://docs.databricks.com

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🎉 Acknowledgments

- OpenAI for Whisper STT/TTS APIs
- Databricks for data warehouse platform
- React ecosystem for amazing tooling
- All contributors and testers

---

**Status**: ✅ Production Ready  
**Last Updated**: March 29, 2025  
**Version**: 1.0.0
