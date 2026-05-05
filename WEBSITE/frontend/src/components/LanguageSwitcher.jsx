import { useLanguage } from "../i18n/useLanguage"
import { LANGUAGE_OPTIONS } from "../i18n/languages"

function LanguageSwitcher() {
  const { language, changeLanguage } = useLanguage()

  return (
    <div className="language-pill">
      <select
        value={language}
        onChange={(event) => changeLanguage(event.target.value)}
        className="select-control"
        aria-label="Select language"
      >
        {LANGUAGE_OPTIONS.map((languageOption) => (
          <option key={languageOption.code} value={languageOption.code}>
            {languageOption.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export default LanguageSwitcher
