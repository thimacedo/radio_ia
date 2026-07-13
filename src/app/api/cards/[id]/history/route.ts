// /api/cards/[id]/history
// POST - adiciona entrada no histórico
// GET - lista histórico completo
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  const { id } = await params
  const history = await db.cardHistory.findMany({
    where: { cardId: id },
    orderBy: { createdAt: "desc" },
  })
  return NextResponse.json({ history })
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  const { id } = await params
  const { action, message, fromStatus, toStatus } = await req.json()

  const entry = await db.cardHistory.create({
    data: {
      cardId: id,
      userId: user.id,
      userName: user.name,
      action: action || "nota",
      fromStatus,
      toStatus,
      message,
    },
  })
  return NextResponse.json({ entry })
}
