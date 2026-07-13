// Helpers gerais

export function normalizePhone(phone: string): string {
  // Remove tudo que não é dígito
  let p = phone.replace(/\D/g, "")
  // Se começar com 0, remove
  if (p.startsWith("0")) p = p.slice(1)
  // Se não tem código de país, adiciona 55 (Brasil)
  if (p.length <= 11) p = "55" + p
  // Se tem 12 dígitos (55 + 10) e o número começa com 0, remove
  return p
}

export function formatPhone(phone: string): string {
  const p = phone.replace(/\D/g, "")
  if (p.length === 13 && p.startsWith("55")) {
    const ddd = p.slice(2, 4)
    const part1 = p.slice(4, 9)
    const part2 = p.slice(9)
    return `+55 (${ddd}) ${part1}-${part2}`
  }
  if (p.length === 12 && p.startsWith("55")) {
    const ddd = p.slice(2, 4)
    const part1 = p.slice(4, 8)
    const part2 = p.slice(8)
    return `+55 (${ddd}) ${part1}-${part2}`
  }
  return phone
}

export function formatPhoneLocal(phone: string): string {
  const p = phone.replace(/\D/g, "")
  if (p.length === 13 && p.startsWith("55")) {
    const ddd = p.slice(2, 4)
    const rest = p.slice(4)
    if (rest.length === 9) return `(${ddd}) ${rest.slice(0, 5)}-${rest.slice(5)}`
    if (rest.length === 8) return `(${ddd}) ${rest.slice(0, 4)}-${rest.slice(4)}`
  }
  if (p.length === 12 && p.startsWith("55")) {
    const ddd = p.slice(2, 4)
    const rest = p.slice(4)
    return `(${ddd}) ${rest.slice(0, 4)}-${rest.slice(4)}`
  }
  return phone
}

export function generateAccessCode(): string {
  // 6 dígitos
  return Math.floor(100000 + Math.random() * 900000).toString()
}

export function whatsappLink(phone: string, message?: string): string {
  const p = phone.replace(/\D/g, "")
  const base = `https://wa.me/${p}`
  if (message) return `${base}?text=${encodeURIComponent(message)}`
  return base
}

export function timeAgo(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date
  const seconds = Math.floor((Date.now() - d.getTime()) / 1000)
  if (seconds < 60) return "agora"
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}min atrás`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h atrás`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d atrás`
  if (days < 30) return `${Math.floor(days / 7)}sem atrás`
  return d.toLocaleDateString("pt-BR")
}

export function formatDate(date: Date | string | null | undefined): string {
  if (!date) return "—"
  const d = typeof date === "string" ? new Date(date) : date
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

export function formatDateTime(date: Date | string | null | undefined): string {
  if (!date) return "—"
  const d = typeof date === "string" ? new Date(date) : date
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// Cores para avatares (sem azul/indigo)
const AVATAR_COLORS = [
  "bg-rose-500",
  "bg-pink-500",
  "bg-fuchsia-500",
  "bg-purple-500",
  "bg-violet-500",
  "bg-emerald-500",
  "bg-green-500",
  "bg-teal-500",
  "bg-cyan-500",
  "bg-orange-500",
  "bg-amber-500",
  "bg-lime-500",
]

export function avatarColor(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}
