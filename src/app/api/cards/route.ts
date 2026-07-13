// /api/cards
// GET - lista cards de acordo com o papel do usuário:
//   voluntario → apenas seus cards (incluindo sem voluntário do seu dept)
//   supervisor → cards dos seus departamentos
//   admin → todos
//   recepcao → todos (somente leitura)
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"
import { ROLES } from "@/lib/constants"

export async function GET(req: NextRequest) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const statusFilter = searchParams.get("status") || ""
  const deptFilter = searchParams.get("department") || ""
  const search = searchParams.get("search") || ""
  const onlyMine = searchParams.get("mine") === "1"

  // Constrói where conforme role
  let where: any = {}

  if (user.role === ROLES.VOLUNTARIO) {
    // Voluntário vê: cards atribuídos a ele + cards sem voluntário do seu dept
    if (onlyMine) {
      where.volunteerId = user.id
    } else {
      where.OR = [
        { volunteerId: user.id },
        { volunteerId: null, departmentId: user.departmentId || "___none___" },
      ]
    }
  } else if (user.role === ROLES.SUPERVISOR) {
    // Supervisor vê: todos os cards dos seus departamentos
    if (user.departmentId) {
      where.departmentId = user.departmentId
    }
    // Se supervisor não tem dept, vê tudo (supervisor geral)
  }
  // admin e recepcao: vê tudo

  if (statusFilter) {
    where.status = statusFilter
  }
  if (deptFilter) {
    where.departmentId = deptFilter
  }
  if (search) {
    where.visitor = {
      OR: [
        { name: { contains: search } },
        { phone: { contains: search } },
        { email: { contains: search } },
      ],
    }
  }

  const cards = await db.followUpCard.findMany({
    where,
    orderBy: [{ priority: "desc" }, { createdAt: "desc" }],
    include: {
      visitor: true,
      department: true,
      volunteer: { select: { id: true, name: true, phone: true } },
      supervisor: { select: { id: true, name: true, phone: true } },
      history: {
        orderBy: { createdAt: "desc" },
        take: 5,
      },
    },
  })

  return NextResponse.json({ cards })
}

export async function POST(req: NextRequest) {
  // Cria card manualmente (supervisor/admin pode direcionar novo card para dept)
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })
  if (user.role !== ROLES.SUPERVISOR && user.role !== ROLES.ADMIN) {
    return NextResponse.json({ error: "Sem permissão" }, { status: 403 })
  }

  const body = await req.json()
  const { visitorId, departmentId, volunteerId, priority, notes } = body

  if (!visitorId || !departmentId) {
    return NextResponse.json({ error: "Visitante e departamento são obrigatórios" }, { status: 400 })
  }

  const card = await db.followUpCard.create({
    data: {
      visitorId,
      departmentId,
      volunteerId: volunteerId || null,
      supervisorId: user.role === ROLES.SUPERVISOR ? user.id : null,
      priority: priority || "normal",
      notes: notes || null,
      status: "novo",
      history: {
        create: {
          userId: user.id,
          userName: user.name,
          action: "criado",
          message: `Card criado manualmente por ${user.name}.`,
        },
      },
    },
  })

  return NextResponse.json({ card })
}
