# CCVideira Capim Macio - Sistema de Follow-up

Este é o sistema de acompanhamento (follow-up) de novos visitantes da CCVideira Capim Macio. Ele foi projetado para gerenciar o fluxo de acolhimento e integração de novos membros através de acompanhamentos direcionados e personalizados por departamentos.

---

## 🚀 Tecnologias Utilizadas

- **Framework**: [Next.js](https://nextjs.org/) (App Router + React 19)
- **Banco de Dados**: [SQLite](https://www.sqlite.org/) (ideal para facilidade de deploy local e testes rápidos)
- **ORM**: [Prisma](https://www.prisma.io/)
- **Runtime & Gerenciador de Pacotes**: [Bun](https://bun.sh/)
- **UI & Estilização**: TailwindCSS + Shadcn/ui + Lucide Icons

---

## 📦 Como Rodar o Projeto Localmente

### 1. Pré-requisitos
Certifique-se de ter o [Bun](https://bun.sh/) instalado em sua máquina.

### 2. Instalar Dependências
```bash
bun install
```

### 3. Configurar Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
```env
DATABASE_URL="file:./db/custom.db"
```

### 4. Inicializar o Banco de Dados e Rodar o Seed
Rode o push do banco para criar as tabelas do SQLite e execute o seed oficial do sistema para popular os departamentos e criar o Administrador de testes:
```bash
bun run db:push
bun x prisma db seed
```

### 5. Iniciar o Servidor de Desenvolvimento
```bash
bun run dev
```
O projeto estará rodando em [http://localhost:3000](http://localhost:3000).

---

## 🔑 Fluxo de Autenticação Sem Senha

O sistema utiliza um fluxo de autenticação seguro e simplificado via WhatsApp (Access Codes):
1. O usuário informa seu telefone cadastrado.
2. O sistema gera um código numérico de 6 dígitos de uso único (com expiração de 10 minutos).
3. **Ambiente de Produção**: O sistema gera um link direcionando para o WhatsApp do usuário contendo o código para que ele copie e faça o login.
4. **Ambiente de Desenvolvimento (Local)**: Para facilitar o desenvolvimento e testes locais com números de teste fictícios, o sistema exibe o **código diretamente na tela** de login se o ambiente não for produção (`process.env.NODE_ENV !== "production"`).

### 👥 Usuários de Teste Iniciais (Seed)
Ao rodar o seed, o seguinte usuário é criado por padrão:
- **Papel**: Administrador (Admin)
- **Telefone**: `5584999999999` (Use este telefone para acessar o painel pela primeira vez)

---

## 🏢 Departamentos e Matching de Visitantes

Quando um novo visitante é cadastrado pelo Lounge, o sistema calcula automaticamente a compatibilidade do perfil dele (idade, sexo, estado civil) e cria um card de acompanhamento para os departamentos correspondentes:

1. **Crianças (0-11 anos)**
2. **Adolescentes (12-17 anos)**
3. **Jovens Solteiros (18-29 anos)**
4. **Homens Casados** (18+ anos, casado/união estável)
5. **Mulheres Casadas** (18+ anos, casado/união estável)
6. **Homens Adultos Solteiros** (30+ anos, solteiro/divorciado/viúvo)
7. **Mulheres Adultas Solteiras** (30+ anos, solteira/divorciada/viúva)
8. **Geral** (Fallback quando nenhum outro perfil se aplica)

---

## 🔄 Organização de Papéis e Permissões

- **Admin**:
  - Acesso total a configurações, estatísticas e gerenciamento de equipe.
  - Pode ver todos os cards, alterar departamento, alterar prioridades e designar supervisores/voluntários.
- **Lounge** *(anteriormente chamado de Recepção)*:
  - Focado no atendimento e acolhimento inicial.
  - Responsável por cadastrar novos visitantes.
  - Tem permissão de leitura de todos os cards e pode **alterar ou adicionar departamentos** para os visitantes caso seja necessário corrigir o fluxo automático.
- **Supervisor**:
  - Responsável por gerenciar o acompanhamento de departamentos específicos.
  - Pode atribuir voluntários da sua equipe aos cards e acompanhar o andamento.
- **Voluntário**:
  - Responsável pelo contato direto e acompanhamento (follow-up).
  - Visualiza apenas seus próprios cards atribuídos ou cards sem voluntário de seu departamento.
  - Pode registrar notas de contato, alterar status de acompanhamento (Em contato, Visita Agendada, Discipulado, Concluído, etc.) e agendar novas ações.

---

## 🛠️ Alterações Recentes

- **Renomeação Visual para Lounge**: Toda a interface foi modificada para exibir "Lounge" no lugar do termo antigo "Recepção", adequando o software à nomenclatura interna adotada.
- **Painel de Departamentos Interativo**: No painel de detalhes do card (`CardDetailSheet.tsx`), foi implementada uma área de gerenciamento completo de departamentos do visitante:
  - **Alteração direta**: Gestores e Lounge podem alterar o departamento do acompanhamento aberto. Ao alterar, o voluntário anterior é limpo para evitar inconsistências e o supervisor correspondente do novo departamento é atribuído.
  - **Multi-direcionamento**: É possível adicionar o mesmo visitante a outros departamentos de forma rápida diretamente pela ficha dele.
  - **Navegação rápida**: Badges coloridos mostram todos os acompanhamentos ativos do visitante e permitem alternar as fichas instantaneamente ao clicar neles.
