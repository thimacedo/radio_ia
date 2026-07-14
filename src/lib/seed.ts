// Seed: departamentos de follow-up por perfil de visitante - CCVideira
import { db } from "./db"
import { ROLES } from "./constants"

async function main() {
  console.log("Iniciando seed de departamentos...")

  // Limpa departamentos anteriores para garantir a migração para os 7 novos oficiais
  await db.department.deleteMany()

  // Departamentos oficiais com regras de matching por perfil
  const depts = await db.department.createMany({
    data: [
      {
        name: "Videira Kids",
        description: "Crianças de até 11 anos de idade",
        minAge: 0,
        maxAge: 11,
        genders: "M,F",
        color: "#f59e0b",
      },
      {
        name: "A13 Junior",
        description: "Adolescentes de 12 a 14 anos",
        minAge: 12,
        maxAge: 14,
        genders: "M,F",
        color: "#10b981",
      },
      {
        name: "A13 School",
        description: "Adolescentes de 15 a 17 anos",
        minAge: 15,
        maxAge: 17,
        genders: "M,F",
        color: "#3b82f6",
      },
      {
        name: "A13 Uni",
        description: "Jovens de 18 a 30 anos",
        minAge: 18,
        maxAge: 30,
        genders: "M,F",
        color: "#ec4899",
      },
      {
        name: "Inspire",
        description: "Adultos solteiros de 31 a 40 anos",
        minAge: 31,
        maxAge: 40,
        genders: "M,F",
        maritalStatuses: "solteiro,divorciado,viuvo,uniao_estavel",
        color: "#8b5cf6",
      },
      {
        name: "Inspire Up",
        description: "Adultos solteiros a partir de 41 anos",
        minAge: 41,
        genders: "M,F",
        maritalStatuses: "solteiro,divorciado,viuvo,uniao_estavel",
        color: "#f43f5e",
      },
      {
        name: "Somos Um",
        description: "Casais casados",
        maritalStatuses: "casado",
        color: "#e11d48",
      },
    ],
  })

  console.log("Departamentos criados.")

  // Cria Admin de testes apenas se não houver nenhum admin cadastrado no sistema
  const adminExists = await db.user.findFirst({
    where: { role: ROLES.ADMIN },
  })

  if (!adminExists) {
    await db.user.create({
      data: {
        name: "Administrador do Sistema",
        phone: "5584999999999",
        role: ROLES.ADMIN,
        active: true,
      },
    })
    console.log("Admin padrão criado (telefone: 5584999999999)")
  } else {
    console.log("Admin já existe. Pulando criação de admin padrão.")
  }

  console.log("Seed concluído com sucesso!")
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await db.$disconnect()
  })
