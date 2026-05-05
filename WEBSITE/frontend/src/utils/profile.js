export function normalizeBoolean(value) {
  if (typeof value === "boolean") {
    return value
  }

  const normalized = String(value || "")
    .trim()
    .toLowerCase()

  return normalized === "yes" || normalized === "true" || normalized === "student"
}

export function normalizeNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function normalizeCasteCategory(value) {
  const casteByToken = {
    general: "General",
    obc: "OBC",
    sc: "SC",
    st: "ST",
  }

  return casteByToken[String(value || "").toLowerCase()] || "General"
}

export function buildProfileFromAnswers({ citizenId, answers }) {
  const isStudentChoice = (answers.isStudent || "").toLowerCase() === "student"

  return {
    citizen_id: citizenId,
    state: answers.state || "",
    occupation: answers.occupation || answers.ownsBusiness || "",
    income: normalizeNumber(answers.income),
    land_acres: normalizeNumber(answers.landAcres),
    has_children: (answers.isStudent || "").toLowerCase() === "child",
    has_girl_child: normalizeBoolean(answers.hasGirlChild),
    caste_category: normalizeCasteCategory(answers.casteCategory),
    is_tribal: normalizeBoolean(answers.isTribal),
    housing_status: answers.housingStatus || "",
    employment_days: normalizeNumber(answers.employmentDays),
    is_student: isStudentChoice,
  }
}

export function buildConfirmationSummary(answers) {
  return {
    income: answers.income || "",
    occupation: answers.occupation || answers.ownsBusiness || "",
    keyDetailsList: [
      answers.state,
      answers.casteCategory,
      answers.educationLevel,
      answers.housingStatus,
      answers.bpl,
    ].filter(Boolean),
  }
}
