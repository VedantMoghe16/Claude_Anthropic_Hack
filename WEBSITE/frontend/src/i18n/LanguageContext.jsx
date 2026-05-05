import { useMemo, useState } from "react"
import { normalizeLanguageCode } from "./languages"
import { LanguageContext } from "./languageStore"

const DEFAULT_LANGUAGE = "en"
const STORAGE_KEY = "app_language"

function getInitialLanguage() {
  return normalizeLanguageCode(localStorage.getItem(STORAGE_KEY) || DEFAULT_LANGUAGE)
}

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(getInitialLanguage())

  const changeLanguage = (nextLanguage) => {
    const normalizedLanguage = normalizeLanguageCode(nextLanguage)
    setLanguage(normalizedLanguage)
    localStorage.setItem(STORAGE_KEY, normalizedLanguage)
  }

  const value = useMemo(
    () => ({
      language,
      changeLanguage,
    }),
    [language],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}
