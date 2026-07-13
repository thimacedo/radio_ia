// /api/users/[id]
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"
import { normalizePhone } from "@/lib/helpers"
import { ROLES } from "@/lib/constants"

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  if (user.role !== ROLES.ADMIN && user.role !== ROLES.SUPERVISOR) {
    return NextResponse.json({ error: "Sem permissão" }, { status: 403 })
  }
  const { id } = await params
  const body = await req.json()
  const data: any = {}
  if (body.name) data.name = body.name
  if (body.phone) {
    data.phone = normalizePhone(body.phone)
    const existing = await db.user.findUnique({ where: { phone: data.phone } })
    if (existing && existing.id !== id) {
      return NextResponse.json({ error: "Telefone já cadastrado" }, { status: 400 })
    }
  }
  // Apenas admin muda role e departamento
  if (user.role === ROLES.ADMIN) {
    if (body.role) data.role = body.role
    if (body.departmentId !== undefined) data.departmentId = body.departmentId || null
  } else if (user.role === ROLES.SUPERVISOR && body.departmentId !== undefined) {
    // supervisor só pode mexer nos usuários do seu dept
    const target = await db.user.findUnique({ where: { id } })
    if (!target || target.departmentId !== user.departmentId) {
      return NextResponse.json({ error: "Sem permissão sobre este usuário" }, { status: 403 })
    }
  }
  if (body.active !== undefined) data.active = !!body.active

  const updated = await db.user.update({ where: { id }, data })
  return NextResponse.json({ user: updated })
}

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  if (user.role !== ROLES.ADMIN) {
    return NextResponse.json({ error: "Sem permissão" }, { status: 403 })
  }
  const { id } = await params
  // Desativa em vez de excluir para preservar histórico
  await db.user.update({ where: { id }, data: { active: false } })
  return NextResponse.json({ ok: true })
}
