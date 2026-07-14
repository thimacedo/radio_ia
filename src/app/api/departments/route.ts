// /api/departments
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"
import { ROLES } from "@/lib/constants"

export async function GET() {
  const user = await getSessionUser()

  if (user) {
    const departments = await db.department.findMany({
      include: {
        _count: { select: { cards: true, users: true } },
        users: {
          where: { role: { in: [ROLES.SUPERVISOR, ROLES.VOLUNTARIO] }, active: true },
          select: { id: true, name: true, role: true, phone: true },
        },
      },
      orderBy: { name: "asc" },
    })
    return NextResponse.json({ departments })
  }

  // Se deslogado (Lounge público), traz apenas o básico
  const departments = await db.department.findMany({
    select: {
      id: true,
      name: true,
      description: true,
      color: true,
    },
    orderBy: { name: "asc" },
  })
  return NextResponse.json({ departments })
}

export async function POST(req: NextRequest) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  if (user.role !== ROLES.ADMIN) {
    return NextResponse.json({ error: "Sem permissão" }, { status: 403 })
  }
  const body = await req.json()
  const dept = await db.department.create({ data: body })
  return NextResponse.json({ department: dept })
}
