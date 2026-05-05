import { readFile, writeFile } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { INDIAN_LANGUAGE_CODES, LANGUAGE_OPTIONS } from "../src/i18n/languages.js"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const localesDir = path.resolve(__dirname, "../src/i18n/locales")
const apiKey = process.env.OPENAI_API_KEY
const model = process.env.OPENAI_MODEL || "gpt-4.1-mini"

if (!apiKey) {
  console.error("OPENAI_API_KEY is missing. Set it and run again.")
  process.exit(1)
}

const requestedCodes = process.argv.slice(2)
const supportedCodes = ["en", ...INDIAN_LANGUAGE_CODES]
const targetCodes = (requestedCodes.length ? requestedCodes : INDIAN_LANGUAGE_CODES).filter((code) =>
  supportedCodes.includes(code),
)

function languageName(code) {
  return LANGUAGE_OPTIONS.find((option) => option.code === code)?.label || code
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value)
}

function flattenObject(object, prefix = "", output = {}) {
  for (const [key, value] of Object.entries(object)) {
    const nextKey = prefix ? `${prefix}.${key}` : key

    if (isObject(value)) {
      flattenObject(value, nextKey, output)
      continue
    }

    if (typeof value === "string") {
      output[nextKey] = value
    }
  }

  return output
}

function setValueByPath(object, dottedPath, value) {
  const keys = dottedPath.split(".")
  let current = object

  for (let index = 0; index < keys.length - 1; index += 1) {
    const key = keys[index]
    if (!isObject(current[key])) {
      current[key] = {}
    }
    current = current[key]
  }

  current[keys[keys.length - 1]] = value
}

async function readLocale(code) {
  const filePath = path.join(localesDir, `${code}.json`)

  try {
    const content = await readFile(filePath, "utf8")
    return JSON.parse(content)
  } catch {
    return {}
  }
}

async function writeLocale(code, data) {
  const filePath = path.join(localesDir, `${code}.json`)
  await writeFile(filePath, `${JSON.stringify(data, null, 2)}\n`, "utf8")
}

async function requestTranslations(langCode, sourceMap) {
  const targetLanguageName = languageName(langCode)

  const prompt = [
    `Translate each value in the JSON object to ${targetLanguageName}.`,
    "Rules:",
    "1) Keep all JSON keys exactly unchanged.",
    "2) Preserve placeholders like {{step}}, {{total}}, {{text}} exactly.",
    "3) Keep numbers, ids, abbreviations (OBC, SC, ST, API) unchanged unless language grammar requires context words.",
    "4) Return strict JSON object only. No markdown.",
  ].join("\n")

  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      input: [
        {
          role: "system",
          content: [{ type: "input_text", text: "You are a professional software localization engine." }],
        },
        {
          role: "user",
          content: [
            {
              type: "input_text",
              text: `${prompt}\n\nJSON:\n${JSON.stringify(sourceMap, null, 2)}`,
            },
          ],
        },
      ],
      text: {
        format: {
          type: "json_object",
        },
      },
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`OpenAI API error (${response.status}): ${errorText}`)
  }

  const data = await response.json()
  const jsonText = extractTextFromResponse(data)

  if (!jsonText) {
    throw new Error(`OpenAI response did not contain text output: ${JSON.stringify(data)}`)
  }

  try {
    return JSON.parse(jsonText)
  } catch {
    throw new Error(`Failed parsing OpenAI JSON response: ${jsonText}`)
  }
}

function extractTextFromResponse(data) {
  if (typeof data?.output_text === "string" && data.output_text.trim()) {
    return data.output_text
  }

  const outputItems = Array.isArray(data?.output) ? data.output : []
  for (const item of outputItems) {
    if (typeof item?.text === "string" && item.text.trim()) {
      return item.text
    }

    const contentItems = Array.isArray(item?.content) ? item.content : []
    for (const contentItem of contentItems) {
      if (typeof contentItem?.text === "string" && contentItem.text.trim()) {
        return contentItem.text
      }
      if (typeof contentItem?.output_text === "string" && contentItem.output_text.trim()) {
        return contentItem.output_text
      }
    }
  }

  return ""
}

async function translateLocale(langCode, baseEnglishFlat) {
  const localeObject = await readLocale(langCode)
  const localeFlat = flattenObject(localeObject)

  const missingEntries = {}
  for (const [key, englishValue] of Object.entries(baseEnglishFlat)) {
    const currentValue = localeFlat[key]
    if (!currentValue || currentValue === englishValue) {
      missingEntries[key] = englishValue
    }
  }

  const missingKeys = Object.keys(missingEntries)
  if (missingKeys.length === 0) {
    console.log(`${langCode}: no missing translations`) 
    return { translated: 0 }
  }

  console.log(`${langCode}: translating ${missingKeys.length} keys`)
  const translatedEntries = await requestTranslations(langCode, missingEntries)

  for (const [key, value] of Object.entries(translatedEntries)) {
    if (typeof value === "string") {
      setValueByPath(localeObject, key, value)
    }
  }

  for (const [key, englishValue] of Object.entries(baseEnglishFlat)) {
    if (getValueByPath(localeObject, key) === undefined) {
      setValueByPath(localeObject, key, englishValue)
    }
  }

  await writeLocale(langCode, localeObject)
  return { translated: missingKeys.length }
}

function getValueByPath(object, dottedPath) {
  return dottedPath.split(".").reduce((current, key) => (current ? current[key] : undefined), object)
}

async function main() {
  const baseEnglish = await readLocale("en")
  const baseEnglishFlat = flattenObject(baseEnglish)

  if (!Object.keys(baseEnglishFlat).length) {
    throw new Error("Base locale src/i18n/locales/en.json is empty or missing.")
  }

  const summary = []
  for (const langCode of targetCodes) {
    if (langCode === "en") {
      continue
    }

    const result = await translateLocale(langCode, baseEnglishFlat)
    summary.push({ code: langCode, translatedKeys: result.translated })
  }

  console.table(summary)
  console.log("Done. Locale files updated.")
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
