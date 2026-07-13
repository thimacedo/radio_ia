// /api/stats - dashboard stats
import { NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"
import { ROLES } from "@/lib/constants"

export async function GET() {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })

  let where: any = {}
  if (user.role === ROLES.VOLUNTARIO) {
    where = { volunteerId: user.id }
  } else if (user.role === ROLES.SUPERVISOR && user.departmentId) {
    where = { departmentId: user.departmentId }
  }

  const total = await db.followUpCard.count({ where })
  const byStatus = await db.followUpCard.groupBy({
    by: ["status"],
    where,
    _count: true,
  })
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const novosHoje = await db.followUpCard.count({
    where: { ...where, createdAt: { gte: today } },
  })
  const proximasAcoes = await db.followUpCard.count({
    where: { ...where, nextActionAt: { not: null, lte: new Date() }, status: { notIn: ["concluido", "sem_interesse"] } },
  })

  return NextResponse.json({
    total,
    byStatus: byStatus.reduce((acc, s) => ({ ...acc, [s.status]: s._count }), {}),
    novosHoje,
    proximasAcoes,
  })
}
