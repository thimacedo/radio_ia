// /api/users
// GET - lista usuários (apenas supervisor/admin)
// POST - cadastra novo usuário (voluntário/supervisor/lounge) - sem senha
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

  // Se for supervisor, só vê usuários dos seus depts
  let where: any = {}
  if (user.role === ROLES.SUPERVISOR) {
    const userDeptIds = (user as any).departments?.map((d: any) => d.id) || []
    where = {
      OR: [
        {
          departments: {
            some: { id: { in: userDeptIds } },
          },
        },
        { role: ROLES.ADMIN }, // admin sempre visível
      ],
    }
  }

  const users = await db.user.findMany({
    where,
    include: { departments: true },
    orderBy: { name: "asc" },
  })

  // Mapeamos para retornar departmentId e department para compatibilidade com o frontend
  const formattedUsers = users.map((u) => {
    const firstDept = u.departments?.[0] || null
    return {
      ...u,
      departmentId: firstDept?.id || null,
      department: firstDept,
    }
  })

  return NextResponse.json({ users: formattedUsers })
}

export async function POST(req: NextRequest) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  
  // Admin cadastra qualquer um; supervisor cadastra apenas voluntários do seu dept
  const body = await req.json()
  const { name, phone, role, departmentIds, gender } = body

  if (!name || !phone) {
    return NextResponse.json({ error: "Nome e telefone são obrigatórios" }, { status: 400 })
  }

  let finalRole = role || ROLES.VOLUNTARIO
  let finalDeptIds: string[] = departmentIds || []

  const userDeptIds = (user as any).departments?.map((d: any) => d.id) || []

  if (user.role === ROLES.SUPERVISOR) {
    finalRole = ROLES.VOLUNTARIO // só pode criar voluntário
    finalDeptIds = userDeptIds // só nos seus depts
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
      gender: gender || null,
      departments: {
        connect: finalDeptIds.map((id) => ({ id })),
      },
    },
    include: { departments: true },
  })

  const firstDept = newUser.departments?.[0] || null
  const formattedUser = {
    ...newUser,
    departmentId: firstDept?.id || null,
    department: firstDept,
  }

  return NextResponse.json({ user: formattedUser })
}
