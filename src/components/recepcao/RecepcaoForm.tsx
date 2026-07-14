"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { UserPlus, Loader2, Search, Phone, Mail, Calendar, Users as UsersIcon, Home, Heart, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { formatPhoneLocal } from "@/lib/helpers"

interface Props {
  onCreated?: () => void
}

export function RecepcaoForm({ onCreated }: Props) {
  const [loading, setLoading] = useState(false)
  const [searchPhone, setSearchPhone] = useState("")
  const [recentVisitors, setRecentVisitors] = useState<any[]>([])
  const [departments, setDepartments] = useState<any[]>([])
  const [departmentId, setDepartmentId] = useState("")
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    birthDate: "",
    gender: "",
    maritalStatus: "",
    address: "",
    hasChildren: false,
    invitedBy: "",
    prayerRequest: "",
    notes: "",
  })

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }))
  }

  // Carrega os departamentos do sistema
  useEffect(() => {
    fetch("/api/departments")
      .then((r) => r.json())
      .then((data) => setDepartments(data.departments || []))
      .catch(() => {})
  }, [])

  async function submit() {
    if (!form.name.trim() || !form.phone.trim()) {
      toast.error("Nome e telefone são obrigatórios")
      return
    }
    if (!departmentId) {
      toast.error("Ministério de destino é obrigatório")
      return
    }
    setLoading(true)
    try {
      const res = await fetch("/api/visitors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          age: null, // a idade será calculada no backend via birthDate
          birthDate: form.birthDate || null,
          departmentId,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        toast.error(data.error || "Erro ao cadastrar")
        return
      }
      toast.success(`Visitante cadastrado! ${data.cardsCreated} card(s) criado(s) para: ${data.departments.join(", ")}`)
      setForm({
        name: "",
        phone: "",
        email: "",
        birthDate: "",
        gender: "",
        maritalStatus: "",
        address: "",
        hasChildren: false,
        invitedBy: "",
        prayerRequest: "",
        notes: "",
      })
      setDepartmentId("")
      onCreated?.()
      loadRecent()
    } finally {
      setLoading(false)
    }
  }

  async function loadRecent() {
    try {
      const res = await fetch("/api/visitors")
      const data = await res.json()
      setRecentVisitors(data.visitors?.slice(0, 5) || [])
    } catch {}
  }

  // Carrega recentes ao montar
  useState(() => {
    loadRecent()
  })

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Formulário */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-emerald-600" />
            Cadastro de Visitante
          </CardTitle>
          <CardDescription>
            Preencha os dados básicos. O sistema vai direcionar automaticamente para o departamento certo.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="name">Nome completo *</Label>
              <Input id="name" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Nome do visitante" />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="phone">Telefone / WhatsApp *</Label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input id="phone" className="pl-10" value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="(84) 99999-9999" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input id="email" type="email" className="pl-10" value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="email@exemplo.com" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Ministério de Destino *</Label>
              <Select value={departmentId} onValueChange={setDepartmentId}>
                <SelectTrigger><SelectValue placeholder="Selecione o ministério" /></SelectTrigger>
                <SelectContent>
                  {departments.map((d) => (
                    <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Data de nascimento</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input type="date" className="pl-10" value={form.birthDate} onChange={(e) => set("birthDate", e.target.value)} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Sexo</Label>
              <Select value={form.gender} onValueChange={(v) => set("gender", v)}>
                <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="M">Masculino</SelectItem>
                  <SelectItem value="F">Feminino</SelectItem>
                  <SelectItem value="Outro">Outro</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Estado civil</Label>
              <Select value={form.maritalStatus} onValueChange={(v) => set("maritalStatus", v)}>
                <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="solteiro">Solteiro(a)</SelectItem>
                  <SelectItem value="casado">Casado(a)</SelectItem>
                  <SelectItem value="uniao_estavel">União Estável</SelectItem>
                  <SelectItem value="divorciado">Divorciado(a)</SelectItem>
                  <SelectItem value="viuvo">Viúvo(a)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label>Endereço (opcional)</Label>
              <div className="relative">
                <Home className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input className="pl-10" value={form.address} onChange={(e) => set("address", e.target.value)} placeholder="Bairro, cidade..." />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Convidado por</Label>
              <Input value={form.invitedBy} onChange={(e) => set("invitedBy", e.target.value)} placeholder="Nome de quem convidou" />
            </div>

            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <Checkbox checked={form.hasChildren} onCheckedChange={(v) => set("hasChildren", !!v)} />
                Tem filhos
              </label>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="flex items-center gap-1"><Sparkles className="w-3 h-3" /> Pedido de oração (se houver)</Label>
            <Textarea value={form.prayerRequest} onChange={(e) => set("prayerRequest", e.target.value)} rows={2} placeholder="Ex: orar pela família, saúde..." />
          </div>

          <div className="space-y-1.5">
            <Label>Observações do Lounge</Label>
            <Textarea value={form.notes} onChange={(e) => set("notes", e.target.value)} rows={2} placeholder="Anotações gerais..." />
          </div>

          <div className="flex justify-end">
            <Button onClick={submit} disabled={loading} className="bg-emerald-600 hover:bg-emerald-700 min-w-40">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <UserPlus className="w-4 h-4 mr-2" />}
              Cadastrar visitante
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Últimos cadastros */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <UsersIcon className="w-4 h-4 text-emerald-600" />
            Últimos cadastros
          </CardTitle>
        </CardHeader>
        <CardContent>
          {recentVisitors.length === 0 ? (
            <p className="text-sm text-slate-400 italic">Nenhum visitante cadastrado ainda</p>
          ) : (
            <ul className="space-y-2">
              {recentVisitors.map((v) => (
                <li key={v.id} className="text-sm border-b last:border-b-0 border-slate-100 dark:border-slate-800 pb-2 last:pb-0">
                  <p className="font-medium">{v.name}</p>
                  <p className="text-xs text-slate-500">{formatPhoneLocal(v.phone)}</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {v.cards?.map((c: any) => (
                      <span key={c.id} className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800" style={{ color: c.department?.color || undefined }}>
                        {c.department?.name || c.status}
                      </span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
