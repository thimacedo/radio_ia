// /api/visitors
// GET - lista visitantes (todos)
// POST - cria visitante + gera cards automaticamente para departamentos compatíveis
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { getSessionUser } from "@/lib/session"
import { findMatchingDepartments } from "@/lib/matching"
import { normalizePhone } from "@/lib/helpers"
import { ROLES } from "@/lib/constants"

export async function GET(req: NextRequest) {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const search = searchParams.get("search") || ""

  const where = search
    ? {
        OR: [
          { name: { contains: search } },
          { phone: { contains: search } },
          { email: { contains: search } },
        ],
      }
    : {}

  const visitors = await db.visitor.findMany({
    where,
    orderBy: { createdAt: "desc" },
    take: 200,
    include: {
      cards: {
        select: {
          id: true,
          status: true,
          department: { select: { name: true, color: true } },
        },
      },
    },
  })

  return NextResponse.json({ visitors })
}

export async function POST(req: NextRequest) {
  const user = await getSessionUser() // Opcional, pois o Lounge pode cadastrar sem login

  const body = await req.json()
  const {
    name,
    phone,
    email,
    age,
    birthDate,
    gender,
    maritalStatus,
    address,
    hasChildren,
    invitedBy,
    prayerRequest,
    notes,
    visitDate,
    departmentId,
  } = body

  if (!name || !phone) {
    return NextResponse.json({ error: "Nome e telefone são obrigatórios" }, { status: 400 })
  }

  const normalizedPhone = normalizePhone(phone)

  // Calcula idade automaticamente se passou birthDate
  let computedAge = age
  if (!computedAge && birthDate) {
    const bd = new Date(birthDate)
    const diff = Date.now() - bd.getTime()
    computedAge = Math.floor(diff / (365.25 * 24 * 3600 * 1000))
  }

  // Cria visitante
  const visitor = await db.visitor.create({
    data: {
      name,
      phone: normalizedPhone,
      email: email || null,
      age: computedAge ?? null,
      birthDate: birthDate ? new Date(birthDate) : null,
      gender: gender || null,
      maritalStatus: maritalStatus || null,
      address: address || null,
      hasChildren: !!hasChildren,
      invitedBy: invitedBy || null,
      prayerRequest: prayerRequest || null,
      notes: notes || null,
      visitDate: visitDate ? new Date(visitDate) : new Date(),
    },
  })

  // Determina departamentos a associar
  let deptsToUse: any[] = []
  if (departmentId) {
    const selectedDept = await db.department.findUnique({ where: { id: departmentId } })
    if (selectedDept) deptsToUse = [selectedDept]
  }

  // Se não foi selecionado ou não encontrado, roda o matching automático
  if (deptsToUse.length === 0) {
    const matching = await findMatchingDepartments({
      age: computedAge,
      gender,
      maritalStatus,
    })
    deptsToUse = matching
    if (deptsToUse.length === 0) {
      const geral = await db.department.findFirst({
        where: { name: { contains: "Geral" } },
      })
      if (geral) deptsToUse = [geral]
    }
  }

  // Cria um card por departamento correspondente (sem duplicar)
  const cardsCreated = []
  for (const dept of deptsToUse) {
    // Verifica se já existe card para este visitante+departamento
    const existing = await db.followUpCard.findFirst({
      where: { visitorId: visitor.id, departmentId: dept.id },
    })
    if (existing) continue

    // Encontra supervisor do dept usando a relação Muitos-para-Muitos
    const supervisor = await db.user.findFirst({
      where: {
        role: ROLES.SUPERVISOR,
        active: true,
        departments: {
          some: { id: dept.id },
        },
      },
    })

    const card = await db.followUpCard.create({
      data: {
        visitorId: visitor.id,
        departmentId: dept.id,
        supervisorId: supervisor?.id || null,
        status: "novo",
        history: {
          create: {
            userName: user?.name || "Lounge",
            action: "criado",
            message: `Visitante cadastrado pela lounge. Direcionado para ${dept.name}.`,
          },
        },
      },
    })
    cardsCreated.push(card)
  }

  return NextResponse.json({
    visitor,
    cardsCreated: cardsCreated.length,
    departments: deptsToUse.map((d) => d.name),
  })
}
