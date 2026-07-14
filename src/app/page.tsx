"use client"

import { useEffect, useState } from "react"
import { useAppStore } from "@/lib/store"
import { LoginScreen } from "@/components/auth/LoginScreen"
import { AppShell } from "@/components/shared/AppShell"
import { Dashboard } from "@/components/shared/Dashboard"
import { RecepcaoForm } from "@/components/recepcao/RecepcaoForm"
import { UsersManager } from "@/components/admin/UsersManager"
import { ROLES } from "@/lib/constants"
import { Leaf, Loader2, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function Home() {
  const { user, loadingUser, setUser, setLoadingUser } = useAppStore()
  const [activeTab, setActiveTab] = useState("dashboard")
  const [showLoungePublic, setShowLoungePublic] = useState(false)

  // Carrega sessão atual
  useEffect(() => {
    fetch("/api/auth/me")
      .then((r) => r.json())
      .then((data) => {
        setUser(data.user || null)
      })
      .catch(() => setUser(null))
      .finally(() => setLoadingUser(false))
  }, [setUser, setLoadingUser])

  if (loadingUser) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-emerald-50 dark:bg-slate-950">
        <div className="w-16 h-16 rounded-full bg-emerald-600 text-white flex items-center justify-center mb-4 animate-pulse">
          <Leaf className="w-8 h-8" />
        </div>
        <Loader2 className="w-5 h-5 animate-spin text-emerald-600" />
        <p className="text-xs text-slate-500 mt-2">Carregando...</p>
      </div>
    )
  }

  if (!user) {
    if (showLoungePublic) {
      return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 md:p-8 flex flex-col">
          <div className="max-w-4xl mx-auto w-full flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
              <Leaf className="text-emerald-600 w-5 h-5" /> CCVideira - Cadastro Lounge
            </h2>
            <Button variant="outline" size="sm" onClick={() => setShowLoungePublic(false)}>
              <ArrowLeft className="w-4 h-4 mr-2" /> Voltar para o Login
            </Button>
          </div>
          <div className="max-w-4xl mx-auto w-full flex-1">
            <RecepcaoForm onCreated={() => setShowLoungePublic(false)} />
          </div>
        </div>
      )
    }
    return <LoginScreen onSuccess={(u) => setUser(u)} onLoungeAccess={() => setShowLoungePublic(true)} />
  }

  return <App loggedUser={user} activeTab={activeTab} setActiveTab={setActiveTab} />
}

function App({ loggedUser, activeTab, setActiveTab }: { loggedUser: any; activeTab: string; setActiveTab: (t: string) => void }) {
  const user = loggedUser

  // Define abas conforme role
  const tabs = []
  if (user.role === ROLES.RECEPCAO) {
    tabs.push({ id: "cadastro", label: "Cadastrar Visitante", icon: Leaf })
    tabs.push({ id: "dashboard", label: "Cards", icon: Leaf })
  } else if (user.role === ROLES.VOLUNTARIO) {
    tabs.push({ id: "dashboard", label: "Meus Cards", icon: Leaf })
  } else if (user.role === ROLES.SUPERVISOR) {
    tabs.push({ id: "dashboard", label: "Dashboard", icon: Leaf })
    tabs.push({ id: "equipe", label: "Minha Equipe", icon: Leaf })
  } else if (user.role === ROLES.ADMIN) {
    tabs.push({ id: "dashboard", label: "Dashboard", icon: Leaf })
    tabs.push({ id: "equipe", label: "Equipe", icon: Leaf })
    tabs.push({ id: "cadastro", label: "Lounge", icon: Leaf })
  }

  // Garante que a aba atual existe
  useEffect(() => {
    if (!tabs.find((t) => t.id === activeTab)) {
      setActiveTab(tabs[0]?.id || "dashboard")
    }
  }, [user.role, activeTab])

  const safeTab = tabs.find((t) => t.id === activeTab) ? activeTab : tabs[0]?.id

  return (
    <AppShell activeTab={safeTab || "dashboard"} onTabChange={setActiveTab} tabs={tabs}>
      {safeTab === "dashboard" && <Dashboard />}
      {safeTab === "cadastro" && <RecepcaoForm onCreated={() => setActiveTab("dashboard")} />}
      {safeTab === "equipe" && <UsersManager />}
    </AppShell>
  )
}
