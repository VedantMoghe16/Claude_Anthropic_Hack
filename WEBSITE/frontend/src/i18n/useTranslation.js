import { useLanguage } from "./useLanguage"
import { normalizeLanguageCode } from "./languages"

function getValueByPath(object, path) {
  return path.split(".").reduce((current, key) => (current ? current[key] : undefined), object)
}

const localeModules = import.meta.glob("./locales/*.json", { eager: true })

const translations = Object.fromEntries(
  Object.entries(localeModules).map(([modulePath, moduleValue]) => {
    const matched = modulePath.match(/\/([^/]+)\.json$/)
    const code = matched ? matched[1] : "en"
    return [code, moduleValue.default || moduleValue]
  }),
)

export function useTranslation() {
  const { language } = useLanguage()
  const normalizedLanguage = normalizeLanguageCode(language)

  const t = (key, params = {}) => {
    const selectedLanguagePack = translations[normalizedLanguage] || translations.en
    const fallbackValue = getValueByPath(translations.en, key)
    const rawValue = getValueByPath(selectedLanguagePack, key) ?? fallbackValue ?? key

    if (typeof rawValue !== "string") {
      return key
    }

    return rawValue.replace(/\{\{(\w+)\}\}/g, (_, variable) => String(params[variable] ?? ""))
  }

  return {
    language: normalizedLanguage,
    t,
  }
}
