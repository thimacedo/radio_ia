"use client"

import { useEffect, useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, LayoutGrid, List, Search, Users, BellRing, CalendarClock, Filter } from "lucide-react"
import { FollowupCard } from "@/components/shared/FollowupCard"
import { KanbanBoard } from "@/components/shared/KanbanBoard"
import { CardDetailSheet } from "@/components/shared/CardDetailSheet"
import { STATUS_LABELS, ROLES } from "@/lib/constants"
import { useAppStore } from "@/lib/store"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"

interface CardData {
  id: string
  status: string
  priority: string
  notes?: string | null
  lastContactAt?: string | null
  nextActionAt?: string | null
  createdAt: string
  visitor: any
  department?: any
  volunteer?: any
  supervisor?: any
}

interface Stats {
  total: number
  byStatus: Record<string, number>
  novosHoje: number
  proximasAcoes: number
}

export function Dashboard() {
  const user = useAppStore((s) => s.user)!
  const view = useAppStore((s) => s.view)
  const setView = useAppStore((s) => s.setView)

  const [cards, setCards] = useState<CardData[]>([])
  const [volunteers, setVolunteers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [deptFilter, setDeptFilter] = useState<string>("")
  const [departments, setDepartments] = useState<any[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [onlyMine, setOnlyMine] = useState(false)
  const [openCardId, setOpenCardId] = useState<string | null>(null)

  const isManager = user.role === ROLES.SUPERVISOR || user.role === ROLES.ADMIN
  const isVoluntario = user.role === ROLES.VOLUNTARIO

  const loadCards = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.set("search", search)
      if (statusFilter) params.set("status", statusFilter)
      if (deptFilter) params.set("department", deptFilter)
      if (onlyMine) params.set("mine", "1")
      const res = await fetch(`/api/cards?${params}`)
      const data = await res.json()
      setCards(data.cards || [])
    } catch {
      toast.error("Erro ao carregar cards")
    } finally {
      setLoading(false)
    }
  }, [search, statusFilter, deptFilter, onlyMine])

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch("/api/stats")
      const data = await res.json()
      setStats(data)
    } catch {}
  }, [])

  const loadDepartments = useCallback(async () => {
    try {
      const res = await fetch("/api/departments")
      const data = await res.json()
      setDepartments(data.departments || [])
    } catch {}
  }, [])

  const loadVolunteers = useCallback(async () => {
    if (!isManager) return
    try {
      const res = await fetch("/api/users")
      const data = await res.json()
      const v = (data.users || []).filter((u: any) => u.role === ROLES.VOLUNTARIO && u.active)
      setVolunteers(v)
    } catch {}
  }, [isManager])

  useEffect(() => {
    loadCards()
    loadStats()
    loadDepartments()
    loadVolunteers()
  }, [loadCards, loadStats, loadDepartments, loadVolunteers])

  async function moveCard(cardId: string, newStatus: string) {
    try {
      const res = await fetch(`/api/cards/${cardId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      })
      if (!res.ok) {
        const d = await res.json()
        toast.error(d.error || "Erro ao mover card")
        loadCards()
        return
      }
      toast.success(`Card movido para "${STATUS_LABELS[newStatus]}"`)
      loadCards()
      loadStats()
    } catch {
      toast.error("Erro de conexão")
      loadCards()
    }
  }

  const filtered = cards

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">Total de cards</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Users className="w-8 h-8 text-emerald-600/30" />
            </div>
          </Card>
          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">Novos hoje</p>
                <p className="text-2xl font-bold text-blue-600">{stats.novosHoje}</p>
              </div>
              <BellRing className="w-8 h-8 text-blue-600/30" />
            </div>
          </Card>
          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">Ações atrasadas</p>
                <p className="text-2xl font-bold text-amber-600">{stats.proximasAcoes}</p>
              </div>
              <CalendarClock className="w-8 h-8 text-amber-600/30" />
            </div>
          </Card>
          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">Em andamento</p>
                <p className="text-2xl font-bold text-emerald-600">
                  {(stats.byStatus.em_contato || 0) + (stats.byStatus.visita_agendada || 0) + (stats.byStatus.discipulado || 0)}
                </p>
              </div>
              <Loader2 className="w-8 h-8 text-emerald-600/30" />
            </div>
          </Card>
        </div>
      )}

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 bg-white dark:bg-slate-900 p-3 rounded-md border">
        <div className="relative flex-1 min-w-40">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input placeholder="Buscar por nome, telefone..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-10" />
        </div>
        <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
          <SelectTrigger className="w-44"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os status</SelectItem>
            {Object.entries(STATUS_LABELS).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isManager && (
          <Select value={deptFilter || "all"} onValueChange={(v) => setDeptFilter(v === "all" ? "" : v)}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Departamento" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os departamentos</SelectItem>
              {departments.map((d) => (
                <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        {isVoluntario && (
          <Button variant={onlyMine ? "default" : "outline"} onClick={() => setOnlyMine(!onlyMine)} className={onlyMine ? "bg-emerald-600 hover:bg-emerald-700" : ""}>
            <Filter className="w-4 h-4 mr-1" /> {onlyMine ? "Apenas meus" : "Todos"}
          </Button>
        )}
        <Tabs value={view} onValueChange={(v) => setView(v as "lista" | "kanban")}>
          <TabsList>
            <TabsTrigger value="lista"><List className="w-4 h-4 mr-1" /> Lista</TabsTrigger>
            <TabsTrigger value="kanban"><LayoutGrid className="w-4 h-4 mr-1" /> Kanban</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Cards */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
        </div>
      ) : view === "kanban" ? (
        <KanbanBoard cards={filtered} onOpen={setOpenCardId} onMove={moveCard} />
      ) : (
        <>
          {filtered.length === 0 ? (
            <Card className="p-12 text-center text-slate-400">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Nenhum card para mostrar. Tente ajustar os filtros.</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {filtered.map((c) => (
                <FollowupCard key={c.id} card={c} onOpen={setOpenCardId} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Detail Sheet */}
      <CardDetailSheet
        cardId={openCardId}
        open={!!openCardId}
        onOpenChange={(o) => !o && setOpenCardId(null)}
        onUpdated={() => {
          loadCards()
          loadStats()
        }}
        onDeleted={() => {
          loadCards()
          loadStats()
        }}
        volunteers={volunteers}
      />
    </div>
  )
}
