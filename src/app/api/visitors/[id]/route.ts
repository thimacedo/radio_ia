// /api/visitors/[id]
// PATCH - atualiza visitante
// DELETE - remove visitante (e cascade cards)
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"
import { normalizePhone } from "@/lib/helpers"

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })

  const { id } = await params
  const body = await req.json()
  const data: any = { ...body }
  if (data.phone) data.phone = normalizePhone(data.phone)
  if (data.birthDate) data.birthDate = new Date(data.birthDate)
  if (data.age != null) data.age = Number(data.age)

  const visitor = await db.visitor.update({
    where: { id },
    data,
  })
  return NextResponse.json({ visitor })
}

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })

  const { id } = await params
  await db.visitor.delete({ where: { id } })
  return NextResponse.json({ ok: true })
}
