// /api/users
// GET - lista usuários (apenas supervisor/admin)
// POST - cadastra novo usuário (voluntário/supervisor/recepcao) - sem senha
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"
import { normalizePhone } from "@/lib/helpers"
import { ROLES } from "@/lib/constants"

export async function GET(req: NextRequest) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  if (user.role !== ROLES.ADMIN && user.role !== ROLES.SUPERVISOR) {
    return NextResponse.json({ error: "Sem permissão" }, { status: 403 })
  }

  // Se for supervisor, só vê usuários do seu dept
  let where: any = {}
  if (user.role === ROLES.SUPERVISOR && user.departmentId) {
    where = {
      OR: [
        { departmentId: user.departmentId },
        { role: ROLES.ADMIN }, // admin sempre visível
      ],
    }
  }

  const users = await db.user.findMany({
    where,
    include: { department: true },
    orderBy: { name: "asc" },
  })
  return NextResponse.json({ users })
}

export async function POST(req: NextRequest) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  // Admin cadastra qualquer um; supervisor cadastra apenas voluntários do seu dept
  const body = await req.json()
  const { name, phone, role, departmentId } = body

  if (!name || !phone) {
    return NextResponse.json({ error: "Nome e telefone são obrigatórios" }, { status: 400 })
  }

  let finalRole = role || ROLES.VOLUNTARIO
  let finalDept = departmentId || null

  if (user.role === ROLES.SUPERVISOR) {
    finalRole = ROLES.VOLUNTARIO // só pode criar voluntário
    finalDept = user.departmentId // só no seu dept
  } else if (user.role !== ROLES.ADMIN) {
    return NextResponse.json({ error: "Sem permissão" }, { status: 403 })
  }

  const normalizedPhone = normalizePhone(phone)
  const existing = await db.user.findUnique({ where: { phone: normalizedPhone } })
  if (existing) {
    return NextResponse.json({ error: "Telefone já cadastrado" }, { status: 400 })
  }

  const newUser = await db.user.create({
    data: {
      name,
      phone: normalizedPhone,
      role: finalRole,
      departmentId: finalDept,
    },
  })
  return NextResponse.json({ user: newUser })
}
