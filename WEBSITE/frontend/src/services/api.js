import axios from "axios"
import { buildMockSchemes } from "../data/schemes"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"

export async function registerCitizen(payload) {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/register-user`, payload, {
      timeout: 8000,
      headers: { "Content-Type": "application/json" },
    })

    return { ok: true, data: response.data }
  } catch (error) {
    // Fail open in demos so the UI can continue with mock data.
    return {
      ok: false,
      error: error?.message || "register_failed",
    }
  }
}

export async function getEligibilityResults(citizenId, profile) {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/get-results/${citizenId}`, {
      timeout: 10000,
    })

    const schemes = response?.data?.schemes || []
    return { ok: true, schemes }
  } catch (error) {
    return {
      ok: false,
      schemes: buildMockSchemes(profile),
      error: error?.message || "results_failed",
    }
  }
}

export async function requestTtsAudio(text, language) {
  const response = await fetch(`${API_BASE_URL}/api/tts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      language,
    }),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || "tts_failed")
  }

  return response.blob()
}

export async function requestSpeechToText(audioBlob) {
  const formData = new FormData()
  formData.append("file", audioBlob, "audio.wav")

  try {
    const response = await fetch(`${API_BASE_URL}/api/stt`, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || "stt_failed")
    }

    const data = await response.json()
    return { ok: true, text: data.text || data.transcript || "", data }
  } catch (error) {
    return { ok: false, text: "", error: error.message }
  }
}


export async function runEligibilityFlow(profile) {
  try {
    const response = await axios.post(`${API_BASE_URL}/check-eligibility`, profile, {
      timeout: 600000,
      headers: { "Content-Type": "application/json" },
    })

    return {
      ok: true,
      data: response.data,
      schemes: response?.data?.eligible_schemes || [],
    }
  } catch (error) {
    return {
      ok: false,
      data: null,
      schemes: buildMockSchemes(profile),
      error: error?.message || "eligibility_flow_failed",
    }
  }
}

export async function linkTelegramMapping(payload) {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/link-telegram`, payload, {
      timeout: 10000,
      headers: { "Content-Type": "application/json" },
    })

    return { ok: true, data: response.data }
  } catch (error) {
    return {
      ok: false,
      error: error?.message || "telegram_link_failed",
    }
  }
}
