"""
Adhikar-Aina | sarvam.py

Thin client for Sarvam AI APIs:
  translate(text, target_lang, source_lang) → str
  tts(text, target_lang)                   → bytes (wav) or None
  stt(audio_bytes, lang)                   → str

All functions fail silently and return the original input on error.
Set SARVAM_API_KEY env var to enable.
"""

from __future__ import annotations

import base64
import os
from typing import Optional

import requests

SARVAM_BASE = "https://api.sarvam.ai"

LANG_CODES = {
    "hi": "hi-IN",
    "bn": "bn-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "ta": "ta-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "or": "or-IN",
    "as": "as-IN",
    "ur": "ur-IN",
    "en": "en-IN",
}

TTS_SPEAKERS = {
    "hi-IN": "meera",
    "bn-IN": "meera",
    "te-IN": "meera",
    "mr-IN": "meera",
    "ta-IN": "meera",
    "gu-IN": "meera",
    "kn-IN": "meera",
    "ml-IN": "meera",
    "pa-IN": "meera",
    "or-IN": "meera",
    "as-IN": "meera",
    "ur-IN": "meera",
    "en-IN": "meera",
}


def _key() -> str:
    return os.getenv("SARVAM_API_KEY", "")


def _json_headers() -> dict:
    return {"api-subscription-key": _key(), "Content-Type": "application/json"}


def normalise_lang(lang: str) -> str:
    """Convert short code ('hi') or full code ('hi-IN') to Sarvam format."""
    if "-" in lang:
        return lang
    return LANG_CODES.get(lang.lower(), "hi-IN")


def translate(text: str, target_lang: str, source_lang: str = "en-IN") -> str:
    """Translate text. Returns original on any error."""
    if not _key() or not text.strip():
        return text
    target = normalise_lang(target_lang)
    source = normalise_lang(source_lang)
    if target == source:
        return text
    try:
        resp = requests.post(
            f"{SARVAM_BASE}/translate",
            headers=_json_headers(),
            json={
                "input":                text[:1000],
                "source_language_code": source,
                "target_language_code": target,
                "speaker_gender":       "Male",
                "mode":                 "formal",
                "model":                "mayura:v1",
                "enable_preprocessing": False,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("translated_text", text)
    except Exception:
        return text


def tts(text: str, target_lang: str = "hi-IN") -> Optional[bytes]:
    """Text-to-speech. Returns raw WAV bytes or None on failure."""
    if not _key() or not text.strip():
        return None
    lang = normalise_lang(target_lang)
    try:
        resp = requests.post(
            f"{SARVAM_BASE}/text-to-speech",
            headers=_json_headers(),
            json={
                "inputs":               [text[:500]],
                "target_language_code": lang,
                "speaker":              TTS_SPEAKERS.get(lang, "meera"),
                "pitch":                0,
                "pace":                 1.0,
                "loudness":             1.0,
                "speech_sample_rate":   8000,
                "enable_preprocessing": True,
                "model":                "bulbul:v1",
            },
            timeout=30,
        )
        resp.raise_for_status()
        audios = resp.json().get("audios", [])
        if audios:
            return base64.b64decode(audios[0])
        return None
    except Exception:
        return None


def stt(audio_bytes: bytes, lang: str = "hi-IN") -> str:
    """Speech-to-text. Returns transcript string or empty string on failure."""
    if not _key():
        return ""
    language = normalise_lang(lang)
    try:
        resp = requests.post(
            f"{SARVAM_BASE}/speech-to-text",
            headers={"api-subscription-key": _key()},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={
                "language_code":   language,
                "model":           "saarika:v1",
                "with_timestamps": "false",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("transcript", "")
    except Exception:
        return ""
