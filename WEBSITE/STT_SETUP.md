# OpenAI STT (Speech-to-Text) Integration Guide

This document explains how to set up and use OpenAI's Speech-to-Text (Whisper API) with the Adhikar application.

## 📋 Prerequisites

- OpenAI API key with access to the Whisper API
- Node.js and npm for frontend
- Python 3.8+ for backend
- A modern browser with microphone access

## 🔧 Setup Instructions

### 1. Get Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com)
2. Sign up or log in to your account
3. Navigate to **API keys** section
4. Click **+ Create new secret key**
5. Copy the key (you won't be able to see it again)

### 2. Configure Environment Variables

1. Copy `.env.example` to `.env` in the project root:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your OpenAI API key:
   ```bash
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

3. Ensure other required environment variables are set (Databricks credentials, etc.)

### 3. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 4. Start the Application

**Backend:**
```bash
cd backend
python app.py
# or
uvicorn app:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## 🎤 Using Microphone/STT

### Frontend Features

The **VoiceQuestionCard** component provides:

- **Microphone Button** 🎙️: Click to start/stop recording
- **Speaker Button** 🔊: Click to hear the question spoken aloud
- **Real-time Feedback**: Shows "Listening..." while recording
- **Automatic Transcription**: Audio is sent to OpenAI Whisper API for transcription
- **Language Support**: Supports 22+ Indian languages

### How It Works

1. User clicks the **microphone button** 🎙️
2. Browser requests microphone access (one-time permission)
3. User speaks their answer
4. Click microphone button again to stop recording
5. Audio is sent to backend `/api/stt` endpoint
6. OpenAI Whisper API transcribes the audio
7. Transcribed text appears in the input field and question

### Permissions

The first time you use the microphone, your browser will ask for permission:
- ✅ Click **Allow** to enable microphone access
- ❌ Click **Block** if you want to use text input only

## 🔌 API Endpoints

### Speech-to-Text (STT)

**Endpoint:** `POST /api/stt`

**Request:**
- Multipart form data with audio file (WAV, MP3, M4A, FLAC, OPUS)

**Response:**
```json
{
  "ok": true,
  "text": "transcribed text from audio",
  "transcript": "transcribed text from audio"
}
```

**Error Response:**
```json
{
  "detail": "STT error: error message"
}
```

### Text-to-Speech (TTS)

**Endpoint:** `POST /api/tts`

**Request:**
```json
{
  "text": "text to convert to speech",
  "language": "language_code"
}
```

**Response:** Audio file (MP3)

## 🗣️ Supported Languages

The system supports transcription in multiple languages:

| Code | Language | Code | Language |
|------|----------|------|----------|
| en   | English  | ml   | Malayalam |
| hi   | Hindi    | ta   | Tamil |
| bengali | Bengali  | te   | Telugu |
| marathi | Marathi  | gu   | Gujarati |
| kannada | Kannada  | or   | Odia |
| punjabi | Punjabi  | as   | Assamese |
| urdu | Urdu | ne   | Nepali |

## 🐛 Troubleshooting

### Microphone Not Working

**Issue:** "Microphone access denied"
- **Solution:** 
  1. Check browser permissions for microphone access
  2. Allow microphone access in browser settings
  3. Try in a different browser or private window
  4. Check if another application is using the microphone

**Issue:** "Audio file is empty"
- **Solution:** Make sure you spoke clearly for at least 1-2 seconds

### STT Returns Empty Transcription

- **Cause:** Audio quality is too poor to transcribe
- **Solution:**
  1. Speak clearly and slowly
  2. Reduce background noise
  3. Ensure your microphone is working properly

### API Key Errors

**Issue:** "OPENAI_API_KEY environment variable is not set"
- **Solution:** 
  1. Add your API key to `.env` file
  2. Ensure the backend is reading the `.env` file
  3. Restart the backend server

**Issue:** "Invalid API key"
- **Solution:** 
  1. Verify you copied the entire key correctly
  2. Check that the key hasn't expired or been revoked
  3. Generate a new key from OpenAI dashboard

### CORS Errors

**Issue:** "CORS policy: Cross-origin request blocked"
- **Solution:** This is likely a development issue. Ensure:
  1. Backend is running on `http://127.0.0.1:8000`
  2. Frontend has correct `VITE_API_BASE_URL` in `.env`
  3. Backend has CORS middleware enabled

## 📊 Cost Considerations

OpenAI Whisper API pricing (as of 2024):
- **Cost:** $0.02 per minute of audio

Estimate:
- 1 hour of audio transcription = $1.20
- Average question (30 seconds) = $0.01

TTS API pricing:
- **Cost:** $0.015 per 1,000 characters

## 🔒 Security Notes

1. **Never commit `.env` file** - It contains sensitive API keys
2. **Add `.env` to `.gitignore`** - Already done
3. **Rotate API keys periodically** - Use OpenAI dashboard
4. **Monitor usage** - Check OpenAI dashboard for unusual activity
5. **Use environment variables** - Never hardcode API keys

## 📝 Integration Details

### Backend Implementation

The STT endpoint (`/api/stt`) uses:
- **Model:** `whisper-1` (OpenAI's Whisper API)
- **Library:** Official OpenAI Python client
- **Supported Formats:** WAV, MP3, M4A, FLAC, OPUS

```python
from openai import OpenAI

openai_client = OpenAI(api_key=OPENAI_API_KEY)

transcript = openai_client.audio.transcriptions.create(
    model="whisper-1",
    file=(filename, audio_content, content_type),
)
```

### Frontend Implementation

The frontend uses:
- **Web Audio API** - For microphone access and recording
- **MediaRecorder API** - For encoding audio to WAV format
- **Fetch API** - For sending audio to backend

```javascript
// Request microphone access
const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

// Record audio
const mediaRecorder = new MediaRecorder(stream)
const audioBlob = new Blob(audioChunks, { type: "audio/wav" })

// Send to backend
const response = await fetch("/api/stt", {
  method: "POST",
  body: formData,
})
```

## ✅ Testing

### Manual Testing

1. Start the backend and frontend
2. Go to the onboarding page
3. Click the microphone button
4. Speak a test phrase (e.g., "Hello, my name is John")
5. Verify that the text appears in the input field

### Automated Testing

Run the test suite:
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📚 Additional Resources

- [OpenAI Whisper API Docs](https://platform.openai.com/docs/guides/speech-to-text)
- [Web Audio API MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [MediaRecorder API MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)

## 📧 Support

For issues or questions:
1. Check the troubleshooting section
2. Review OpenAI API documentation
3. Check browser console for error messages
4. Check backend logs for detailed error information
