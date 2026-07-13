// /api/cards/[id]
// GET - detalhe
// PATCH - atualiza (status, voluntário, supervisor, prioridade, notas, nextActionAt)
// DELETE - remove
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"
import { ROLES, STATUS_LABELS } from "@/lib/constants"

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })

  const { id } = await params
  const card = await db.followUpCard.findUnique({
    where: { id },
    include: {
      visitor: true,
      department: true,
      volunteer: { select: { id: true, name: true, phone: true } },
      supervisor: { select: { id: true, name: true, phone: true } },
      history: {
        orderBy: { createdAt: "desc" },
      },
    },
  })
  if (!card) return NextResponse.json({ error: "Card não encontrado" }, { status: 404 })
  return NextResponse.json({ card })
}

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })

  const { id } = await params
  const body = await req.json()
  const { status, volunteerId, supervisorId, priority, notes, lastContactAt, nextActionAt, addHistory } = body

  const card = await db.followUpCard.findUnique({ where: { id } })
  if (!card) return NextResponse.json({ error: "Card não encontrado" }, { status: 404 })

  // Permissões:
  // voluntario: só pode mudar status, notes, lastContactAt, nextActionAt
  // supervisor/admin: tudo
  const isVoluntario = user.role === ROLES.VOLUNTARIO
  const isManager = user.role === ROLES.SUPERVISOR || user.role === ROLES.ADMIN

  const data: any = {}
  const historyEntries: any[] = []

  if (status && status !== card.status) {
    data.status = status
    historyEntries.push({
      userId: user.id,
      userName: user.name,
      action: "status_alterado",
      fromStatus: card.status,
      toStatus: status,
      message: `Status alterado de "${STATUS_LABELS[card.status] || card.status}" para "${STATUS_LABELS[status] || status}" por ${user.name}.`,
    })
  }
  if (volunteerId !== undefined && isManager) {
    if (volunteerId !== card.volunteerId) {
      data.volunteerId = volunteerId || null
      historyEntries.push({
        userId: user.id,
        userName: user.name,
        action: "redistribuido",
        message: volunteerId
          ? `Card atribuído a um voluntário por ${user.name}.`
          : `Card liberado (sem voluntário) por ${user.name}.`,
      })
    }
  }
  if (supervisorId !== undefined && isManager) {
    data.supervisorId = supervisorId || null
  }
  if (priority && priority !== card.priority && isManager) {
    data.priority = priority
    historyEntries.push({
      userId: user.id,
      userName: user.name,
      action: "prioridade",
      message: `Prioridade alterada para "${priority}" por ${user.name}.`,
    })
  }
  if (notes !== undefined) {
    data.notes = notes
  }
  if (lastContactAt !== undefined) {
    data.lastContactAt = lastContactAt ? new Date(lastContactAt) : null
    if (lastContactAt) {
      historyEntries.push({
        userId: user.id,
        userName: user.name,
        action: "contato",
        message: `Contato registrado por ${user.name}.`,
      })
    }
  }
  if (nextActionAt !== undefined) {
    data.nextActionAt = nextActionAt ? new Date(nextActionAt) : null
  }
  if (addHistory) {
    historyEntries.push({
      userId: user.id,
      userName: user.name,
      action: "nota",
      message: addHistory,
    })
  }

  // Voluntário só pode mexer nos cards que lhe pertencem OU sem dono do seu dept
  if (isVoluntario) {
    const isMyCard = card.volunteerId === user.id
    const isFreeInMyDept = !card.volunteerId && card.departmentId === user.departmentId
    if (!isMyCard && !isFreeInMyDept) {
      return NextResponse.json({ error: "Sem permissão para editar este card" }, { status: 403 })
    }
  }

  const updated = await db.followUpCard.update({
    where: { id },
    data: {
      ...data,
      history: historyEntries.length > 0 ? { createMany: { data: historyEntries } } : undefined,
    },
  })

  return NextResponse.json({ card: updated })
}

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  if (user.role !== ROLES.SUPERVISOR && user.role !== ROLES.ADMIN) {
    return NextResponse.json({ error: "Sem permissão" }, { status: 403 })
  }

  const { id } = await params
  await db.followUpCard.delete({ where: { id } })
  return NextResponse.json({ ok: true })
}
