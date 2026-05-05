export const INDIAN_LANGUAGE_CODES = [
  "hi",
  "bn",
  "mr",
  "ta",
  "te",
  "gu",
  "kn",
  "ml",
  "pa",
  "as",
  "or",
  "ur",
  "sa",
  "ks",
  "sd",
  "kok",
  "mni",
  "ne",
  "bodo",
  "sat",
  "mai",
  "doi",
]

const NON_ISO_LABELS = {
  en: "English",
  hi: "हिंदी",
  as: "অসমীয়া",
  bn: "বাংলা",
  mr: "मराठी",
  ta: "தமிழ்",
  te: "తెలుగు",
  gu: "ગુજરાતી",
  kn: "ಕನ್ನಡ",
  ml: "മലയാളം",
  pa: "ਪੰਜਾਬੀ",
  or: "ଓଡ଼ିଆ",
  ur: "اردو",
  sa: "संस्कृतम्",
  ks: "कॉशुर / کٲشُر",
  sd: "سنڌي",
  kok: "कोंकणी",
  mni: "মৈতৈলোন্",
  ne: "नेपाली",
  bodo: "बर'",
  sat: "ᱥᱟᱱᱛᱟᱲᱤ",
  mai: "मैथिली",
  doi: "डोगरी",
}

function displayNameForLanguage(code) {
  if (NON_ISO_LABELS[code]) {
    return NON_ISO_LABELS[code]
  }

  try {
    const displayNames = new Intl.DisplayNames(["en"], { type: "language" })
    return displayNames.of(code) || code.toUpperCase()
  } catch {
    return code.toUpperCase()
  }
}

export const SUPPORTED_LANGUAGE_CODES = ["hi", "en", ...INDIAN_LANGUAGE_CODES.filter((code) => code !== "hi")]

export const LANGUAGE_OPTIONS = SUPPORTED_LANGUAGE_CODES.map((code) => ({
  code,
  label: displayNameForLanguage(code),
}))

export function normalizeLanguageCode(code) {
  const baseCode = String(code || "").toLowerCase().split("-")[0]
  return SUPPORTED_LANGUAGE_CODES.includes(baseCode) ? baseCode : "en"
}
