"use client"

import { useEffect, useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { MessageCircle, Phone, Calendar, History, User, Trash2, Save, Loader2, UserCircle, CalendarPlus } from "lucide-react"
import { STATUS_LABELS, PRIORITY_LABELS, ROLE_LABELS, GENDER_LABELS, MARITAL_STATUS_LABELS } from "@/lib/constants"
import { STATUS_COLORS, PRIORITY_COLORS } from "@/lib/constants"
import { formatPhoneLocal, whatsappLink, formatDateTime, initials, avatarColor } from "@/lib/helpers"
import { toast } from "sonner"
import { useAppStore } from "@/lib/store"
import { Input } from "@/components/ui/input"

interface HistoryItem {
  id: string
  action: string
  fromStatus?: string | null
  toStatus?: string | null
  message?: string | null
  userName: string
  createdAt: string
}

interface CardDetail {
  id: string
  status: string
  priority: string
  notes?: string | null
  lastContactAt?: string | null
  nextActionAt?: string | null
  createdAt: string
  updatedAt: string
  volunteerId?: string | null
  departmentId?: string | null
  supervisorId?: string | null
  visitor: {
    id: string
    name: string
    phone: string
    email?: string | null
    age?: number | null
    gender?: string | null
    maritalStatus?: string | null
    address?: string | null
    invitedBy?: string | null
    prayerRequest?: string | null
    notes?: string | null
    visitDate: string
  }
  department?: { id: string; name: string; color?: string | null } | null
  volunteer?: { id: string; name: string; phone: string } | null
  supervisor?: { id: string; name: string; phone: string } | null
  history: HistoryItem[]
}

interface Props {
  cardId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUpdated: () => void
  onDeleted: () => void
  // Lista de voluntários para o supervisor atribuir
  volunteers?: { id: string; name: string; phone: string }[]
}

const ACTION_LABELS: Record<string, string> = {
  criado: "Card criado",
  status_alterado: "Status alterado",
  redistribuido: "Redistribuído",
  prioridade: "Prioridade alterada",
  contato: "Contato registrado",
  nota: "Nota adicionada",
}

export function CardDetailSheet({ cardId, open, onOpenChange, onUpdated, onDeleted, volunteers }: Props) {
  const user = useAppStore((s) => s.user)
  const [card, setCard] = useState<CardDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [newNote, setNewNote] = useState("")
  const [editNotes, setEditNotes] = useState("")
  const [nextAction, setNextAction] = useState("")
  const [selectedVolunteer, setSelectedVolunteer] = useState<string>("")

  const isManager = user?.role === "supervisor" || user?.role === "admin"
  const canEdit = !!user && (isManager || card?.volunteerId === user.id || (!card?.volunteer && card?.departmentId === user?.departmentId))

  useEffect(() => {
    if (cardId && open) loadCard()
  }, [cardId, open])

  async function loadCard() {
    setLoading(true)
    try {
      const res = await fetch(`/api/cards/${cardId}`)
      const data = await res.json()
      setCard(data.card)
      setEditNotes(data.card?.notes || "")
      setNextAction(data.card?.nextActionAt ? data.card.nextActionAt.slice(0, 10) : "")
      setSelectedVolunteer(data.card?.volunteerId || "")
    } catch (e) {
      toast.error("Erro ao carregar card")
    } finally {
      setLoading(false)
    }
  }

  async function updateStatus(status: string) {
    if (!card) return
    setSaving(true)
    try {
      const res = await fetch(`/api/cards/${card.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      })
      if (!res.ok) {
        const d = await res.json()
        toast.error(d.error || "Erro ao atualizar")
        return
      }
      toast.success("Status atualizado")
      await loadCard()
      onUpdated()
    } finally {
      setSaving(false)
    }
  }

  async function updatePriority(priority: string) {
    if (!card) return
    setSaving(true)
    try {
      const res = await fetch(`/api/cards/${card.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ priority }),
      })
      if (!res.ok) {
        const d = await res.json()
        toast.error(d.error || "Erro")
        return
      }
      toast.success("Prioridade atualizada")
      await loadCard()
      onUpdated()
    } finally {
      setSaving(false)
    }
  }

  async function assignVolunteer() {
    if (!card) return
    setSaving(true)
    try {
      const res = await fetch(`/api/cards/${card.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ volunteerId: selectedVolunteer || null }),
      })
      if (!res.ok) {
        const d = await res.json()
        toast.error(d.error || "Erro")
        return
      }
      toast.success("Atribuição atualizada")
      await loadCard()
      onUpdated()
    } finally {
      setSaving(false)
    }
  }

  async function saveNotes() {
    if (!card) return
    setSaving(true)
    try {
      const res = await fetch(`/api/cards/${card.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: editNotes }),
      })
      if (!res.ok) {
        toast.error("Erro ao salvar")
        return
      }
      toast.success("Notas salvas")
      await loadCard()
      onUpdated()
    } finally {
      setSaving(false)
    }
  }

  async function registerContact() {
    if (!card) return
    setSaving(true)
    try {
      const res = await fetch(`/api/cards/${card.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lastContactAt: new Date().toISOString() }),
      })
      if (!res.ok) {
        toast.error("Erro")
        return
      }
      toast.success("Contato registrado")
      await loadCard()
      onUpdated()
    } finally {
      setSaving(false)
    }
  }

  async function saveNextAction() {
    if (!card) return
    setSaving(true)
    try {
      const res = await fetch(`/api/cards/${card.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nextActionAt: nextAction ? new Date(nextAction).toISOString() : null }),
      })
      if (!res.ok) {
        toast.error("Erro")
        return
      }
      toast.success("Próxima ação agendada")
      await loadCard()
      onUpdated()
    } finally {
      setSaving(false)
    }
  }

  async function addNote() {
    if (!card || !newNote.trim()) return
    setSaving(true)
    try {
      const res = await fetch(`/api/cards/${card.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ addHistory: newNote }),
      })
      if (!res.ok) {
        toast.error("Erro")
        return
      }
      setNewNote("")
      await loadCard()
      onUpdated()
    } finally {
      setSaving(false)
    }
  }

  async function deleteCard() {
    if (!card) return
    if (!confirm("Excluir este card? O visitante permanece cadastrado.")) return
    setSaving(true)
    try {
      const res = await fetch(`/api/cards/${card.id}`, { method: "DELETE" })
      if (!res.ok) {
        toast.error("Erro ao excluir")
        return
      }
      toast.success("Card excluído")
      onOpenChange(false)
      onDeleted()
    } finally {
      setSaving(false)
    }
  }

  const waMsg = card ? `Olá ${card.visitor.name}, aqui é ${user?.name || "da equipe"} da CCVideira Capim Macio. Tudo bem?` : ""
  const waLink = card ? whatsappLink(card.visitor.phone, waMsg) : ""

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            {card?.visitor.name || "Carregando..."}
            {card && (
              <Badge variant="outline" className={`${STATUS_COLORS[card.status]} text-xs`}>
                {STATUS_LABELS[card.status]}
              </Badge>
            )}
          </SheetTitle>
          <SheetDescription>
            {card?.department?.name} · Card criado em {card ? formatDateTime(card.createdAt) : ""}
          </SheetDescription>
        </SheetHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
          </div>
        ) : card ? (
          <div className="space-y-4 mt-4">
            {/* Ações rápidas WhatsApp */}
            <div className="flex gap-2">
              <a href={waLink} target="_blank" rel="noopener noreferrer" className="flex-1">
                <Button className="w-full bg-emerald-600 hover:bg-emerald-700">
                  <MessageCircle className="w-4 h-4 mr-2" />
                  Iniciar conversa WhatsApp
                </Button>
              </a>
              {canEdit && (
                <Button variant="outline" onClick={registerContact} disabled={saving}>
                  <Phone className="w-4 h-4 mr-2" />
                  Registrou contato
                </Button>
              )}
            </div>

            {/* Dados do visitante */}
            <div className="rounded-md border p-3 bg-slate-50 dark:bg-slate-900/50 space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-slate-700 dark:text-slate-200">Dados do Visitante</h4>
                <Badge variant="outline" className={`text-xs ${PRIORITY_COLORS[card.priority]}`}>
                  {PRIORITY_LABELS[card.priority]}
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-slate-500">Idade:</span> {card.visitor.age || "—"}</div>
                <div><span className="text-slate-500">Sexo:</span> {card.visitor.gender ? GENDER_LABELS[card.visitor.gender] : "—"}</div>
                <div><span className="text-slate-500">Estado civil:</span> {card.visitor.maritalStatus ? MARITAL_STATUS_LABELS[card.visitor.maritalStatus] : "—"}</div>
                <div><span className="text-slate-500">Telefone:</span> {formatPhoneLocal(card.visitor.phone)}</div>
                {card.visitor.email && <div><span className="text-slate-500">Email:</span> {card.visitor.email}</div>}
                {card.visitor.invitedBy && <div><span className="text-slate-500">Convidado por:</span> {card.visitor.invitedBy}</div>}
              </div>
              {card.visitor.prayerRequest && (
                <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
                  <p className="text-xs font-medium text-slate-500 mb-1">Pedido de oração:</p>
                  <p className="text-sm italic">{card.visitor.prayerRequest}</p>
                </div>
              )}
            </div>

            {/* Alterar status */}
            {canEdit && (
              <div className="space-y-2">
                <Label className="text-xs uppercase text-slate-500">Alterar status</Label>
                <Select value={card.status} onValueChange={updateStatus} disabled={saving}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(STATUS_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Prioridade */}
            {isManager && (
              <div className="space-y-2">
                <Label className="text-xs uppercase text-slate-500">Prioridade</Label>
                <Select value={card.priority} onValueChange={updatePriority} disabled={saving}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(PRIORITY_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Atribuir voluntário */}
            {isManager && volunteers && (
              <div className="space-y-2">
                <Label className="text-xs uppercase text-slate-500">Atribuir voluntário</Label>
                <div className="flex gap-2">
                  <Select value={selectedVolunteer || "none"} onValueChange={(v) => setSelectedVolunteer(v === "none" ? "" : v)}>
                    <SelectTrigger className="flex-1"><SelectValue placeholder="Sem voluntário" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">— Sem voluntário —</SelectItem>
                      {volunteers.map((v) => (
                        <SelectItem key={v.id} value={v.id}>{v.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button onClick={assignVolunteer} disabled={saving} size="icon">
                    <Save className="w-4 h-4" />
                  </Button>
                </div>
                {card.volunteer && (
                  <div className="flex items-center gap-2 text-xs">
                    <Avatar className="w-5 h-5">
                      <AvatarFallback className={`text-[10px] text-white ${avatarColor(card.volunteer.name)}`}>
                        {initials(card.volunteer.name)}
                      </AvatarFallback>
                    </Avatar>
                    <span>{card.volunteer.name}</span>
                  </div>
                )}
              </div>
            )}

            {/* Próxima ação */}
            {canEdit && (
              <div className="space-y-2">
                <Label className="text-xs uppercase text-slate-500 flex items-center gap-1"><CalendarPlus className="w-3 h-3" /> Próxima ação</Label>
                <div className="flex gap-2">
                  <Input type="date" value={nextAction} onChange={(e) => setNextAction(e.target.value)} />
                  <Button onClick={saveNextAction} disabled={saving} size="icon">
                    <Save className="w-4 h-4" />
                  </Button>
                </div>
                {card.lastContactAt && (
                  <p className="text-xs text-slate-500">Último contato: {formatDateTime(card.lastContactAt)}</p>
                )}
              </div>
            )}

            {/* Notas internas do card */}
            {canEdit && (
              <div className="space-y-2">
                <Label className="text-xs uppercase text-slate-500">Notas internas do card</Label>
                <Textarea value={editNotes} onChange={(e) => setEditNotes(e.target.value)} rows={3} placeholder="Anotações da equipe..." />
                <Button size="sm" variant="outline" onClick={saveNotes} disabled={saving}>
                  <Save className="w-3 h-3 mr-1" /> Salvar notas
                </Button>
              </div>
            )}

            {/* Adicionar entrada no histórico */}
            {canEdit && (
              <div className="space-y-2">
                <Label className="text-xs uppercase text-slate-500 flex items-center gap-1"><History className="w-3 h-3" /> Adicionar nota ao histórico</Label>
                <div className="flex gap-2">
                  <Textarea value={newNote} onChange={(e) => setNewNote(e.target.value)} rows={2} placeholder="Ex: Visitante respondeu, marcou de ir ao culto..." />
                </div>
                <Button size="sm" onClick={addNote} disabled={saving || !newNote.trim()}>
                  Adicionar nota
                </Button>
              </div>
            )}

            {/* Histórico */}
            <div className="space-y-2">
              <Label className="text-xs uppercase text-slate-500 flex items-center gap-1"><History className="w-3 h-3" /> Histórico de ações</Label>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {card.history.length === 0 && <p className="text-xs text-slate-400 italic">Sem histórico ainda</p>}
                {card.history.map((h) => (
                  <div key={h.id} className="text-xs border-l-2 border-emerald-300 pl-2 py-1">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{ACTION_LABELS[h.action] || h.action}</span>
                      <span className="text-slate-400">{formatDateTime(h.createdAt)}</span>
                    </div>
                    {h.message && <p className="text-slate-600 dark:text-slate-400 mt-0.5">{h.message}</p>}
                    <p className="text-slate-400 mt-0.5">por {h.userName}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Excluir */}
            {isManager && (
              <Button variant="destructive" size="sm" onClick={deleteCard} disabled={saving} className="w-full">
                <Trash2 className="w-3 h-3 mr-1" /> Excluir card
              </Button>
            )}
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
