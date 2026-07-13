// Lógica de matching de visitante → departamento(s)
import { db } from "./db"

interface VisitorProfile {
  age?: number | null
  gender?: string | null
  maritalStatus?: string | null
}

function matches(value: string | null | undefined, csv: string | null | undefined): boolean {
  if (!csv) return true // sem restrição
  if (!value) return false
  const list = csv.split(",").map((s) => s.trim())
  return list.includes(value)
}

function matchesAge(age: number | null | undefined, min?: number | null, max?: number | null): boolean {
  if (age == null) {
    // se o dept não tem restrição de idade, ok; se tem, não dá pra casar
    if (min == null && max == null) return true
    return false
  }
  if (min != null && age < min) return false
  if (max != null && age > max) return false
  return true
}

// Verifica se o departamento tem algum critério definido (não é fallback)
function hasCriteria(d: any): boolean {
  return d.minAge != null || d.maxAge != null || !!d.genders || !!d.maritalStatuses
}

export async function findMatchingDepartments(profile: VisitorProfile) {
  const departments = await db.department.findMany()
  // Considera apenas departamentos com critérios para matching
  const specific = departments.filter(hasCriteria)
  const matched = specific.filter((d) => {
    if (!matchesAge(profile.age, d.minAge, d.maxAge)) return false
    if (!matches(profile.gender, d.genders)) return false
    if (!matches(profile.maritalStatus, d.maritalStatuses)) return false
    return true
  })
  if (matched.length > 0) return matched
  // Se nenhum específico casou, retorna os departamentos de fallback (sem critérios)
  return departments.filter((d) => !hasCriteria(d))
}
