// POST /api/auth/request-code
// Body: { phone: string }
// Gera um código de 6 dígitos, salva no banco e retorna o link wa.me para o usuário
// se auto-enviar o código (já que não temos integração WhatsApp).
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { generateAccessCode, normalizePhone, whatsappLink } from "@/lib/helpers"
import { CODE_DURATION_MIN } from "@/lib/constants"

export async function POST(req: NextRequest) {
  try {
    const { phone } = await req.json()
    if (!phone || typeof phone !== "string") {
      return NextResponse.json({ error: "Telefone é obrigatório" }, { status: 400 })
    }
    const normalized = normalizePhone(phone)
    const user = await db.user.findUnique({ where: { phone: normalized } })
    if (!user) {
      return NextResponse.json(
        { error: "Telefone não cadastrado. Solicite seu cadastro ao supervisor ou admin." },
        { status: 404 }
      )
    }
    if (!user.active) {
      return NextResponse.json({ error: "Usuário inativo. Procure a liderança." }, { status: 403 })
    }

    const code = generateAccessCode()
    const expiresAt = new Date(Date.now() + CODE_DURATION_MIN * 60 * 1000)
    await db.accessCode.create({
      data: { userId: user.id, code, expiresAt },
    })

    const message = `*CCVideira Capim Macio - Follow-up*\n\nSeu código de acesso é: *${code}*\n\nEle expira em ${CODE_DURATION_MIN} minutos.`
    const waLink = whatsappLink(normalized, message)

    return NextResponse.json({
      ok: true,
      message: `Código gerado. Toque no botão abaixo para abrir o WhatsApp e receber seu código.`,
      whatsappLink: waLink,
      userName: user.name,
      userId: user.id,
    })
  } catch (e) {
    console.error(e)
    return NextResponse.json({ error: "Erro interno" }, { status: 500 })
  }
}
