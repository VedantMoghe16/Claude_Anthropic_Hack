import { useEffect, useRef, useState } from "react"
import { useLanguage } from "../i18n/useLanguage"
import { useTranslation } from "../i18n/useTranslation"
import { voiceConfig } from "../i18n/voiceConfig"
import { requestTtsAudio, requestSpeechToText } from "../services/api"

function VoiceQuestionCard({ question, value, onChange }) {
  const [isRecording, setIsRecording] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [transcript, setTranscript] = useState("")
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [error, setError] = useState("")
  const audioRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioContextRef = useRef(null)
  const streamRef = useRef(null)
  const recordingTimerRef = useRef(null)
  const { language } = useLanguage()
  const { t } = useTranslation()

  // Check browser support for audio
  const isAudioSupported = () => {
    return !!(navigator.mediaDevices?.getUserMedia && window.MediaRecorder)
  }

  useEffect(
    () => () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
      window.speechSynthesis?.cancel()
      stopRecording()
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
      }
    },
    [],
  )

  const fallbackBrowserSpeak = (text) => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = voiceConfig[language] || voiceConfig.en
      window.speechSynthesis.speak(utterance)
    }
  }

  const speakText = async (text) => {
    setIsSpeaking(true)
    setError("")

    try {
      const audioBlob = await requestTtsAudio(text, language)

      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }

      const audioUrl = URL.createObjectURL(audioBlob)
      const audio = new Audio(audioUrl)
      audioRef.current = audio

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl)
        setIsSpeaking(false)
      }

      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl)
        setIsSpeaking(false)
        setError("Failed to play audio")
      }

      await audio.play()
    } catch (err) {
      setIsSpeaking(false)
      console.error("TTS error:", err)
      fallbackBrowserSpeak(text)
    }
  }

  const handleSpeak = () => speakText(question.text)

  const startRecording = async () => {
    if (!isAudioSupported()) {
      setError("Your browser does not support audio recording. Please use Chrome, Firefox, Safari, or Edge.")
      return
    }

    setError("")
    setRecordingTime(0)

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      streamRef.current = stream

      // Create audio context
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      }

      // Create media recorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm" || "audio/wav",
      })
      mediaRecorderRef.current = mediaRecorder

      const audioChunks = []

      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data)
      }

      mediaRecorder.onstop = async () => {
        // Stop recording timer
        if (recordingTimerRef.current) {
          clearInterval(recordingTimerRef.current)
        }

        const audioBlob = new Blob(audioChunks, { type: "audio/webm" })

        // Check if audio blob is empty
        if (audioBlob.size === 0) {
          setError("No audio recorded. Please try again.")
          stream.getTracks().forEach((track) => track.stop())
          return
        }

        // Send to backend for transcription
        setIsTranscribing(true)
        setError("")
        const result = await requestSpeechToText(audioBlob)
        setIsTranscribing(false)

        if (result.ok && result.text) {
          setTranscript(t("onboarding.transcripts.heardPrefix", { text: result.text }))
          onChange(result.text)
          setError("")
        } else {
          const errorMsg = result.error || "Failed to transcribe audio"
          setTranscript(t("onboarding.transcripts.error", { error: errorMsg }))
          setError(errorMsg)
        }

        // Stop the stream
        stream.getTracks().forEach((track) => track.stop())
      }

      mediaRecorder.onerror = (event) => {
        setError(`Recording error: ${event.error}`)
        setIsRecording(false)
      }

      mediaRecorder.start()
      setIsRecording(true)

      // Start recording timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1)
      }, 1000)
    } catch (error) {
      console.error("Microphone access error:", error)
      
      // Provide specific error messages based on error type
      if (error.name === "NotAllowedError") {
        setError("Microphone access was denied. Please check your browser permissions and try again.")
      } else if (error.name === "NotFoundError") {
        setError("No microphone found. Please check your device.")
      } else if (error.name === "NotSupportedError") {
        setError("Microphone access is not supported in your browser. Try using a different browser.")
      } else {
        setError(`Microphone error: ${error.message}`)
      }
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
    
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current)
    }
  }

  const handleMicToggle = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  if (!isAudioSupported()) {
    return (
      <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h3 className="text-[1.01rem] font-semibold leading-snug text-slate-900">{question.text}</h3>
        </div>
        <div className="mt-4 space-y-2.5">
          <p className="text-sm text-red-600">⚠️ Voice input is not supported in your browser. Please use text input instead.</p>
          <input
            type={question.type === "number" ? "number" : "text"}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder={question.placeholder || t("common.textFallbackInput")}
            className="input-control"
          />
        </div>
      </article>
    )
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-lg">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h3 className="text-[1.01rem] font-semibold leading-snug text-slate-900">{question.text}</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSpeak}
            className="btn btn-ghost rounded-full px-3 py-2 text-xs"
            disabled={isSpeaking || isRecording}
            aria-label={t("voice.speaker")}
            title={t("voice.speaker")}
          >
            <span aria-hidden="true" className="inline-flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 10V14H7L12 19V5L7 10H3Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M16 9C17.2 10.2 17.2 13.8 16 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                <path d="M19 6C21.8 8.8 21.8 15.2 19 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </span>
          </button>
          <button
            type="button"
            onClick={handleMicToggle}
            className={`btn ${isRecording ? "btn-danger" : "btn-soft"} rounded-full px-3 py-2 text-xs transition-all`}
            disabled={isRecording && isTranscribing}
            aria-label={t("voice.mic")}
            title={isRecording ? t("voice.listening") : t("voice.mic")}
          >
            <span aria-hidden="true" className="inline-flex items-center justify-center">
              {isRecording ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-pulse">
                  <rect x="9" y="3" width="6" height="12" rx="3" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M5 11C5 14.3137 7.68629 17 11 17H13C16.3137 17 19 14.3137 19 11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  <path d="M12 17V21" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  <path d="M9 21H15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="9" y="3" width="6" height="12" rx="3" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M5 11C5 14.3137 7.68629 17 11 17H13C16.3137 17 19 14.3137 19 11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  <path d="M12 17V21" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  <path d="M9 21H15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              )}
            </span>
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-2.5">
        <input
          type={question.type === "number" ? "number" : "text"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={question.placeholder || t("common.textFallbackInput")}
          className="input-control"
        />

        {error && (
          <p className="chip chip-error text-[0.72rem] normal-case tracking-normal">
            ❌ {error}
          </p>
        )}

        {isRecording && (
          <p className="chip chip-info text-[0.72rem] normal-case tracking-normal animate-pulse">
            🎙️ Listening... {formatTime(recordingTime)}
          </p>
        )}

        {isTranscribing && (
          <p className="chip chip-info text-[0.72rem] normal-case tracking-normal animate-pulse">
            ⏳ Transcribing with AI...
          </p>
        )}

        {transcript && !isRecording && !isTranscribing ? (
          <p className="chip chip-brand text-[0.72rem] normal-case tracking-normal">{transcript}</p>
        ) : null}
      </div>
    </article>
  )
}

export default VoiceQuestionCard
