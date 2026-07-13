// Constantes do sistema de follow-up

export const ROLES = {
  ADMIN: "admin",
  RECEPCAO: "recepcao",
  SUPERVISOR: "supervisor",
  VOLUNTARIO: "voluntario",
} as const

export const ROLE_LABELS: Record<string, string> = {
  admin: "Administrador",
  recepcao: "Recepção",
  supervisor: "Supervisor de Follow-up",
  voluntario: "Voluntário",
}

export const STATUS = {
  NOVO: "novo",
  EM_CONTATO: "em_contato",
  AGUARDANDO: "aguardando",
  VISITA_AGENDADA: "visita_agendada",
  DISCIPULADO: "discipulado",
  CONCLUIDO: "concluido",
  SEM_INTERESSE: "sem_interesse",
} as const

export const STATUS_LABELS: Record<string, string> = {
  novo: "Novo",
  em_contato: "Em Contato",
  aguardando: "Aguardando Resposta",
  visita_agendada: "Visita Agendada",
  discipulado: "Discipulado",
  concluido: "Concluído",
  sem_interesse: "Sem Interesse",
}

export const STATUS_COLORS: Record<string, string> = {
  novo: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800",
  em_contato: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800",
  aguardando: "bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800",
  visita_agendada: "bg-cyan-100 text-cyan-700 border-cyan-200 dark:bg-cyan-900/30 dark:text-cyan-300 dark:border-cyan-800",
  discipulado: "bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800",
  concluido: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800",
  sem_interesse: "bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/30 dark:text-rose-300 dark:border-rose-800",
}

export const STATUS_KANBAN_COLUMNS: Record<string, { title: string; color: string; accent: string }> = {
  novo: { title: "Novo", color: "border-t-blue-500", accent: "bg-blue-50 dark:bg-blue-900/20" },
  em_contato: { title: "Em Contato", color: "border-t-amber-500", accent: "bg-amber-50 dark:bg-amber-900/20" },
  aguardando: { title: "Aguardando", color: "border-t-purple-500", accent: "bg-purple-50 dark:bg-purple-900/20" },
  visita_agendada: { title: "Visita Agendada", color: "border-t-cyan-500", accent: "bg-cyan-50 dark:bg-cyan-900/20" },
  discipulado: { title: "Discipulado", color: "border-t-green-500", accent: "bg-green-50 dark:bg-green-900/20" },
  concluido: { title: "Concluído", color: "border-t-emerald-500", accent: "bg-emerald-50 dark:bg-emerald-900/20" },
  sem_interesse: { title: "Sem Interesse", color: "border-t-rose-500", accent: "bg-rose-50 dark:bg-rose-900/20" },
}

export const STATUS_ORDER = [
  "novo",
  "em_contato",
  "aguardando",
  "visita_agendada",
  "discipulado",
  "concluido",
  "sem_interresse",
]

export const PRIORITIES = {
  BAIXA: "baixa",
  NORMAL: "normal",
  ALTA: "alta",
} as const

export const PRIORITY_LABELS: Record<string, string> = {
  baixa: "Baixa",
  normal: "Normal",
  alta: "Alta",
}

export const PRIORITY_COLORS: Record<string, string> = {
  baixa: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  normal: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  alta: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
}

export const GENDER_LABELS: Record<string, string> = {
  M: "Masculino",
  F: "Feminino",
  Outro: "Outro",
}

export const MARITAL_STATUS_LABELS: Record<string, string> = {
  solteiro: "Solteiro(a)",
  casado: "Casado(a)",
  divorciado: "Divorciado(a)",
  viuvo: "Viúvo(a)",
  uniao_estavel: "União Estável",
}

// Sessão - tempo em segundos
export const SESSION_DURATION = 60 * 60 * 8 // 8 horas
export const CODE_DURATION_MIN = 10 // código expira em 10 min
