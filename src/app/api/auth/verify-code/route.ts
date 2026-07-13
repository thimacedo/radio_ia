// POST /api/auth/verify-code
// Body: { userId, code }
// Valida o código e cria a sessão (cookie)
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { setSessionCookie } from "@/lib/session"

export async function POST(req: NextRequest) {
  try {
    const { userId, code } = await req.json()
    if (!userId || !code) {
      return NextResponse.json({ error: "Dados incompletos" }, { status: 400 })
    }
    const user = await db.user.findUnique({ where: { id: userId } })
    if (!user || !user.active) {
      return NextResponse.json({ error: "Usuário inválido" }, { status: 404 })
    }

    // Pega o código mais recente não usado e não expirado
    const accessCode = await db.accessCode.findFirst({
      where: {
        userId: user.id,
        code: code.trim(),
        used: false,
        expiresAt: { gt: new Date() },
      },
      orderBy: { createdAt: "desc" },
    })

    if (!accessCode) {
      return NextResponse.json({ error: "Código inválido ou expirado" }, { status: 401 })
    }

    await db.accessCode.update({
      where: { id: accessCode.id },
      data: { used: true, consumedAt: new Date() },
    })

    await setSessionCookie(user.id)

    return NextResponse.json({
      ok: true,
      user: {
        id: user.id,
        name: user.name,
        role: user.role,
        phone: user.phone,
      },
    })
  } catch (e) {
    console.error(e)
    return NextResponse.json({ error: "Erro interno" }, { status: 500 })
  }
}
