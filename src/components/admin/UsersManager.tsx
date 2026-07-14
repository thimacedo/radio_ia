"use client"

import { useEffect, useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Switch } from "@/components/ui/switch"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { UserPlus, Users, Loader2, Phone, Pencil, Trash2, MessageCircle } from "lucide-react"
import { ROLE_LABELS, ROLES } from "@/lib/constants"
import { formatPhoneLocal, whatsappLink, initials, avatarColor } from "@/lib/helpers"
import { useAppStore } from "@/lib/store"
import { toast } from "sonner"

export function UsersManager() {
  const user = useAppStore((s) => s.user)!
  const [users, setUsers] = useState<any[]>([])
  const [departments, setDepartments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<any | null>(null)
  const [form, setForm] = useState({ name: "", phone: "", role: ROLES.VOLUNTARIO, departmentIds: [] as string[], gender: "M" })

  const isAdmin = user.role === ROLES.ADMIN

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [resU, resD] = await Promise.all([fetch("/api/users"), fetch("/api/departments")])
      const du = await resU.json()
      const dd = await resD.json()
      setUsers(du.users || [])
      setDepartments(dd.departments || [])
    } catch {
      toast.error("Erro ao carregar")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  function openNew() {
    setEditingUser(null)
    const initialDepts = user.role === ROLES.SUPERVISOR
      ? (user.departments?.map((d: any) => d.id) || [user.departmentId].filter(Boolean) as string[])
      : []
    setForm({
      name: "",
      phone: "",
      role: ROLES.VOLUNTARIO,
      departmentIds: initialDepts,
      gender: "M",
    })
    setDialogOpen(true)
  }

  function openEdit(u: any) {
    setEditingUser(u)
    const userDepts = u.departments?.map((d: any) => d.id) || [u.departmentId].filter(Boolean) as string[]
    setForm({
      name: u.name,
      phone: u.phone,
      role: u.role,
      departmentIds: userDepts,
      gender: u.gender || "M",
    })
    setDialogOpen(true)
  }

  async function save() {
    if (!form.name.trim() || !form.phone.trim()) {
      toast.error("Nome e telefone são obrigatórios")
      return
    }
    try {
      if (editingUser) {
        const res = await fetch(`/api/users/${editingUser.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        })
        if (!res.ok) {
          const d = await res.json()
          toast.error(d.error || "Erro ao editar")
          return
        }
        toast.success("Usuário atualizado")
      } else {
        const res = await fetch("/api/users", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        })
        if (!res.ok) {
          const d = await res.json()
          toast.error(d.error || "Erro ao cadastrar")
          return
        }
        toast.success("Usuário cadastrado! Ele já pode acessar com o telefone.")
      }
      setDialogOpen(false)
      load()
    } catch {
      toast.error("Erro de conexão")
    }
  }

  async function toggleActive(u: any) {
    try {
      const res = await fetch(`/api/users/${u.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !u.active }),
      })
      if (!res.ok) {
        toast.error("Erro")
        return
      }
      toast.success(u.active ? "Usuário desativado" : "Usuário ativado")
      load()
    } catch {}
  }

  async function remove(u: any) {
    if (!confirm(`Desativar ${u.name}?`)) return
    try {
      const res = await fetch(`/api/users/${u.id}`, { method: "DELETE" })
      if (!res.ok) {
        toast.error("Erro")
        return
      }
      toast.success("Usuário removido")
      load()
    } catch {}
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5 text-emerald-600" />
            Equipe de Follow-up
          </CardTitle>
          <CardDescription>Gerencie voluntários, supervisores e Lounge</CardDescription>
        </div>
        <Button onClick={openNew} className="bg-emerald-600 hover:bg-emerald-700">
          <UserPlus className="w-4 h-4 mr-2" /> Novo
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {users.map((u) => (
              <div key={u.id} className={`rounded-md border p-3 ${!u.active ? "opacity-50" : ""}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Avatar className="w-9 h-9">
                      <AvatarFallback className={`text-xs text-white ${avatarColor(u.name)}`}>
                        {initials(u.name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{u.name}</p>
                      <p className="text-xs text-slate-500 flex items-center gap-1">
                        <Phone className="w-3 h-3" />
                        {formatPhoneLocal(u.phone)}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-[10px]">{ROLE_LABELS[u.role]}</Badge>
                </div>
                <div className="mt-2 pl-11 space-y-0.5">
                  {u.departments && u.departments.length > 0 && (
                    <p className="text-xs text-slate-500 font-medium">
                      Depts: {u.departments.map((d: any) => d.name).join(", ")}
                    </p>
                  )}
                  {u.gender && (
                    <p className="text-[10px] text-slate-400">
                      Gênero: {u.gender === "M" ? "Masculino" : "Feminino"}
                    </p>
                  )}
                </div>
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <Switch checked={u.active} onCheckedChange={() => toggleActive(u)} />
                    <span className="text-xs text-slate-500">{u.active ? "Ativo" : "Inativo"}</span>
                  </div>
                  <div className="flex gap-1">
                    <a href={whatsappLink(u.phone, `Olá ${u.name}, aqui é ${user.name} da CCVideira.`)} target="_blank" rel="noopener noreferrer">
                      <Button size="icon" variant="ghost" className="h-7 w-7 text-emerald-600">
                        <MessageCircle className="w-3.5 h-3.5" />
                      </Button>
                    </a>
                    <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openEdit(u)}>
                      <Pencil className="w-3.5 h-3.5" />
                    </Button>
                    {isAdmin && (
                      <Button size="icon" variant="ghost" className="h-7 w-7 text-rose-600" onClick={() => remove(u)}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {users.length === 0 && (
              <p className="col-span-full text-center text-slate-400 italic py-8">Nenhum usuário cadastrado</p>
            )}
          </div>
        )}
      </CardContent>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingUser ? "Editar usuário" : "Novo usuário"}</DialogTitle>
            <DialogDescription>
              {editingUser
                ? "Atualize os dados do membro da equipe."
                : "Cadastre um novo voluntário, supervisor ou membro do Lounge. Ele acessará o sistema via WhatsApp, sem senha."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Nome *</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nome completo" />
            </div>
            <div className="space-y-1.5">
              <Label>Telefone / WhatsApp *</Label>
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="(84) 99999-9999" />
            </div>
            {isAdmin && (
              <div className="space-y-1.5">
                <Label>Papel</Label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(ROLE_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-1.5">
              <Label>Sexo (Gênero) *</Label>
              <Select value={form.gender} onValueChange={(v) => setForm({ ...form, gender: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="M">Masculino</SelectItem>
                  <SelectItem value="F">Feminino</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Ministérios / Departamentos</Label>
              <div className="grid grid-cols-1 gap-1.5 border rounded-md p-3 max-h-36 overflow-y-auto">
                {departments.map((d) => {
                  const checked = form.departmentIds.includes(d.id)
                  return (
                    <label key={d.id} className="flex items-center gap-2 text-sm cursor-pointer hover:opacity-80">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setForm({ ...form, departmentIds: [...form.departmentIds, d.id] })
                          } else {
                            setForm({ ...form, departmentIds: form.departmentIds.filter((id) => id !== d.id) })
                          }
                        }}
                        className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 w-4 h-4"
                      />
                      <span>{d.name}</span>
                    </label>
                  )
                })}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button onClick={save} className="bg-emerald-600 hover:bg-emerald-700">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
