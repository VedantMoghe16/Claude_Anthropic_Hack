import { useEffect, useMemo, useRef, useState } from "react"
import { Navigate, useNavigate } from "react-router-dom"
import VoiceQuestionCard from "../components/VoiceQuestionCard"
import { useAppContext } from "../context/useAppContext"
import { QUESTIONS_BY_CATEGORY, SUPPORT_CATEGORIES } from "../data/questions"
import { useLanguage } from "../i18n/useLanguage"
import { useTranslation } from "../i18n/useTranslation"
import { voiceConfig } from "../i18n/voiceConfig"
import { requestTtsAudio } from "../services/api"
import { runEligibilityFlow } from "../services/api"
import { buildConfirmationSummary, buildProfileFromAnswers } from "../utils/profile"

const VALUE_TO_TRANSLATION_KEY = {
  yes: "common.yes",
  no: "common.no",
  general: "onboarding.options.general",
  obc: "onboarding.options.obc",
  sc: "onboarding.options.sc",
  st: "onboarding.options.st",
  student: "onboarding.options.student",
  child: "onboarding.options.child",
}

function OnboardingPage() {
  const navigate = useNavigate()
  const {
    citizenId,
    setCitizenId,
    selectedCategory,
    setSelectedCategory,
    answers,
    setAnswers,
    profile,
    setProfile,
    setResults,
    setPipelineRunId,
    setEligibilityExplanation,
  } = useAppContext()

  const [step, setStep] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [submitStatusText, setSubmitStatusText] = useState("")
  const [retrievedCitizenData, setRetrievedCitizenData] = useState(null)
  const audioRef = useRef(null)
  const { language } = useLanguage()
  const { t } = useTranslation()

  // Check if profile is pre-filled from citizen lookup
  const isProfileFromCitizenLookup = () => {
    return profile && (profile.annual_income || profile.land_acres || profile.occupation_category)
  }

  const questions = useMemo(
    () =>
      (QUESTIONS_BY_CATEGORY[selectedCategory] || []).map((question) => ({
        ...question,
        text: t(question.textKey),
        placeholder: question.placeholderKey ? t(question.placeholderKey) : "",
        sampleTranscript: question.sampleTranscriptKey ? t(question.sampleTranscriptKey) : "",
        options:
          question.options?.map((option) => ({
            ...option,
            label: t(option.labelKey),
          })) || [],
      })),
    [selectedCategory, t],
  )
  const summary = useMemo(() => buildConfirmationSummary(answers), [answers])

  const formatSummaryValue = (value) => {
    if (!value) {
      return t("common.notProvided")
    }

    const normalized = String(value).trim().toLowerCase()
    const translationKey = VALUE_TO_TRANSLATION_KEY[normalized]

    return translationKey ? t(translationKey) : value
  }

  const keyDetailsText =
    summary.keyDetailsList?.length
      ? summary.keyDetailsList.map((item) => formatSummaryValue(item)).join(" | ")
      : t("common.notProvided")

  if (!citizenId) {
    return <Navigate to="/login" replace />
  }

  useEffect(
    () => () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
      window.speechSynthesis?.cancel()
    },
    [],
  )

  // Auto-submit when profile is pre-filled from citizen lookup
  useEffect(() => {
    if (isProfileFromCitizenLookup() && !isSubmitting) {
      console.log("🎯 Auto-submitting with pre-filled citizen data...")
      handleAutoSubmit()
    }
  }, [profile])

  const fallbackBrowserSpeak = (text) => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = voiceConfig[language] || voiceConfig.en
      window.speechSynthesis.speak(utterance)
    }
  }

  const speakText = async (text) => {
    setIsSpeaking(true)

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
      }

      await audio.play()
    } catch {
      setIsSpeaking(false)
      fallbackBrowserSpeak(text)
    }
  }

  const updateAnswer = (key, value) => {
    setAnswers((previous) => ({
      ...previous,
      [key]: value,
    }))
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setSubmitStatusText("⏳ Checking your eligibility...")

    const payload = buildProfileFromAnswers({ citizenId, answers })
    setProfile(payload)
    setSubmitStatusText("Running government eligibility engine...")

    const flowResponse = await runEligibilityFlow(payload)
    if (flowResponse.ok) {
      if (flowResponse?.data?.citizen_id) {
        setCitizenId(flowResponse.data.citizen_id)
      }
      setResults(flowResponse.schemes || [])
      setPipelineRunId(String(flowResponse?.data?.run_id || ""))
      setEligibilityExplanation(flowResponse?.data?.eligibility_explanation || null)
      setSubmitStatusText(`✅ You are eligible for ${(flowResponse.schemes || []).length} schemes!`)
    } else {
      setResults(flowResponse.schemes || [])
      setPipelineRunId("")
      setEligibilityExplanation(null)
      console.error("Eligibility flow failed:", flowResponse.error)
    }

    setTimeout(() => {
      setIsSubmitting(false)
      navigate("/dashboard")
    }, 500)
  }

  const handleAutoSubmit = async () => {
    setIsSubmitting(true)
    setSubmitStatusText("⏳ Processing your citizen record...")

    // Use the pre-filled profile directly from citizen lookup
    const payload = {
      citizen_id: citizenId,
      ...profile,
    }
    
    setSubmitStatusText("Running government eligibility engine...")

    const flowResponse = await runEligibilityFlow(payload)
    if (flowResponse.ok) {
      if (flowResponse?.data?.citizen_id) {
        setCitizenId(flowResponse.data.citizen_id)
      }
      setResults(flowResponse.schemes || [])
      setPipelineRunId(String(flowResponse?.data?.run_id || ""))
      setEligibilityExplanation(flowResponse?.data?.eligibility_explanation || null)
      setSubmitStatusText(`✅ You are eligible for ${(flowResponse.schemes || []).length} schemes!`)
    } else {
      setResults(flowResponse.schemes || [])
      setPipelineRunId("")
      setEligibilityExplanation(null)
      console.error("Eligibility flow failed:", flowResponse.error)
    }

    setTimeout(() => {
      setIsSubmitting(false)
      navigate("/dashboard")
    }, 500)
  }

  return (
    <main className="page-shell">
      <div className="page-container max-w-6xl">
        {isProfileFromCitizenLookup() && isSubmitting && (
          <section className="section-card p-7 sm:p-10 text-center">
            <div className="mb-6">
              <div className="inline-block mb-4">
                <svg className="animate-spin h-12 w-12 text-teal-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Processing Your Profile</h2>
              <p className="text-slate-600 mb-4">{submitStatusText || "Checking your eligibility for government schemes..."}</p>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-center gap-2 text-slate-600">
                <span>✓ Citizen record retrieved</span>
              </div>
              <div className="flex items-center justify-center gap-2 text-teal-600 font-medium">
                <svg className="inline-block h-4 w-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                </svg>
                <span>Running eligibility checks...</span>
              </div>
            </div>
          </section>
        )}

        {(!isProfileFromCitizenLookup() || !isSubmitting) && (
          <>
        <section className="section-card p-7 sm:p-10">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="page-title text-3xl">{t("onboarding.title")}</h1>
              <p className="page-subtitle mt-1">{t("onboarding.stepText", { step, total: 3 })}</p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="btn btn-ghost"
            >
              {t("onboarding.exit")}
            </button>
          </div>

          {step === 1 ? (
            <div>
              {profile && Object.keys(profile).length > 0 && (
                <div className="mb-6 rounded-lg bg-blue-50 border border-blue-200 p-4">
                  <h3 className="font-semibold text-blue-900 mb-3">📋 Retrieved Citizen Record</h3>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 text-sm">
                    {profile.district && (<div><span className="text-blue-700">District:</span> <span className="font-medium text-blue-900">{profile.district}</span></div>)}
                    {profile.income && (<div><span className="text-blue-700">Income:</span> <span className="font-medium text-blue-900">₹{Number(profile.income).toLocaleString()}</span></div>)}
                    {profile.occupation && (<div><span className="text-blue-700">Occupation:</span> <span className="font-medium text-blue-900">{profile.occupation}</span></div>)}
                    {profile.landAcres && (<div><span className="text-blue-700">Land:</span> <span className="font-medium text-blue-900">{profile.landAcres} acres</span></div>)}
                    {profile.category && (<div><span className="text-blue-700">Category:</span> <span className="font-medium text-blue-900">{profile.category}</span></div>)}
                    {profile.hasGirlChild && (<div><span className="text-blue-700">Girl Child:</span> <span className="font-medium text-blue-900">Yes</span></div>)}
                  </div>
                  <p className="text-xs text-blue-600 mt-3">You can proceed with this data or modify answers below.</p>
                </div>
              )}
              
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-2xl font-semibold text-slate-900">{t("onboarding.supportPrompt")}</h2>
                <button
                  type="button"
                  onClick={() => speakText(t("onboarding.supportPrompt"))}
                  className="btn btn-ghost rounded-full px-3 py-2 text-xs"
                  disabled={isSpeaking}
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
              </div>
              <div className="mt-5 grid grid-cols-1 gap-3">
                {SUPPORT_CATEGORIES.map((categoryOption) => (
                  <div
                    key={categoryOption.id}
                    className={`rounded-2xl border px-4 py-3.5 transition ${
                      selectedCategory === categoryOption.id
                        ? "border-teal-500 bg-teal-50 text-teal-800 shadow-sm"
                        : "border-slate-200 bg-white text-slate-700 hover:border-teal-300 hover:bg-teal-50/40"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedCategory(categoryOption.id)
                          setAnswers({})
                        }}
                        className="flex-1 text-left text-sm font-semibold"
                      >
                        {t(categoryOption.labelKey)}
                      </button>
                      <button
                        type="button"
                        onClick={() => speakText(t(categoryOption.labelKey))}
                        className="btn btn-ghost rounded-full px-2.5 py-2"
                        disabled={isSpeaking}
                        aria-label={`${t("voice.speaker")}: ${t(categoryOption.labelKey)}`}
                        title={`${t("voice.speaker")}: ${t(categoryOption.labelKey)}`}
                      >
                        <span aria-hidden="true" className="inline-flex items-center justify-center">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 10V14H7L12 19V5L7 10H3Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                            <path d="M16 9C17.2 10.2 17.2 13.8 16 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                          </svg>
                        </span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setStep(2)}
                disabled={!selectedCategory}
                className="btn btn-primary mt-6 px-6 py-3.5 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {t("common.continue")}
              </button>
            </div>
          ) : null}

          {step === 2 ? (
            <div>
              <div className="grid gap-4">
                {questions.map((question) => (
                  <VoiceQuestionCard
                    key={question.id}
                    question={question}
                    value={answers[question.id] || ""}
                    onChange={(value) => updateAnswer(question.id, value)}
                  />
                ))}
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="btn btn-ghost"
                >
                  {t("common.back")}
                </button>
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  className="btn btn-primary"
                >
                  {t("onboarding.reviewAnswers")}
                </button>
              </div>
            </div>
          ) : null}

          {step === 3 ? (
            <div>
              <h2 className="text-2xl font-semibold text-slate-900">{t("onboarding.summaryTitle")}</h2>
              <div className="panel-muted mt-4 space-y-3 p-5 text-sm text-slate-700">
                <p>
                  <span className="font-semibold">{t("onboarding.incomeLabel")}:</span> {formatSummaryValue(summary.income)}
                </p>
                <p>
                  <span className="font-semibold">{t("onboarding.occupationLabel")}:</span> {formatSummaryValue(summary.occupation)}
                </p>
                <p>
                  <span className="font-semibold">{t("onboarding.keyDetailsLabel")}:</span> {keyDetailsText}
                </p>
              </div>

              {isSubmitting ? (
                <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  <p className="font-semibold">{submitStatusText || "⏳ Checking your eligibility..."}</p>
                  <p className="mt-1 text-slate-600">Running government eligibility engine...</p>
                </div>
              ) : (
                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="btn btn-ghost"
                  >
                    {t("common.edit")}
                  </button>
                  <button
                    type="button"
                    onClick={handleSubmit}
                    className="btn btn-primary"
                  >
                    {t("common.confirm")}
                  </button>
                </div>
              )}
            </div>
          ) : null}
        </section>
        </>
        )}
      </div>
    </main>
  )
}

export default OnboardingPage
