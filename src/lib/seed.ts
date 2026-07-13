// Seed: departamentos típicos de follow-up por perfil de visitante
import { db } from "./db"
import { ROLES } from "./constants"

async function main() {
  // Verifica se já tem dados
  const deptCount = await db.department.count()
  if (deptCount > 0) {
    console.log("Seed já executado. Pulado.")
    return
  }

  // Departamentos com regras de matching por perfil
  // A ideia é cobrir todos os perfis que chegam na igreja
  await db.department.createMany({
    data: [
      {
        name: "Crianças (0-11 anos)",
        description: "Follow-up de famílias com crianças e das próprias crianças",
        minAge: 0,
        maxAge: 11,
        genders: "M,F",
        color: "#f59e0b",
      },
      {
        name: "Adolescentes (12-17 anos)",
        description: "Follow-up de adolescentes do ministry de jovens",
        minAge: 12,
        maxAge: 17,
        genders: "M,F",
        color: "#10b981",
      },
      {
        name: "Jovens Solteiros (18-29 anos)",
        description: "Jovens adultos solteiros",
        minAge: 18,
        maxAge: 29,
        genders: "M,F",
        maritalStatuses: "solteiro",
        color: "#ec4899",
      },
      {
        name: "Homens Casados",
        description: "Follow-up de homens casados",
        minAge: 18,
        genders: "M",
        maritalStatuses: "casado,uniao_estavel",
        color: "#0ea5e9",
      },
      {
        name: "Mulheres Casadas",
        description: "Follow-up de mulheres casadas",
        minAge: 18,
        genders: "F",
        maritalStatuses: "casado,uniao_estavel",
        color: "#a855f7",
      },
      {
        name: "Homens Adultos Solteiros",
        description: "Homens 30+ solteiros/divorciados/viúvos",
        minAge: 30,
        genders: "M",
        maritalStatuses: "solteiro,divorciado,viuvo",
        color: "#14b8a6",
      },
      {
        name: "Mulheres Adultas Solteiras",
        description: "Mulheres 30+ solteiras/divorciadas/viúvas",
        minAge: 30,
        genders: "F",
        maritalStatuses: "solteiro,divorciado,viuvo",
        color: "#f43f5e",
      },
      {
        name: "Geral (Sem Perfil Específico)",
        description: "Quando o perfil não casa com nenhum departamento específico",
        color: "#64748b",
      },
    ],
  })

  // Admin inicial: telefone 5584999999999 (código será mostrado na tela)
  await db.user.create({
    data: {
      name: "Administrador do Sistema",
      phone: "5584999999999",
      role: ROLES.ADMIN,
      active: true,
    },
  })

  console.log("Seed concluído:")
  console.log(" - 8 departamentos criados")
  console.log(" - Admin criado (telefone: 5584999999999)")
  console.log(" - Para acessar, solicite código e o sistema vai mostrar o link wa.me")
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await db.$disconnect()
  })
