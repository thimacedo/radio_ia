"use client"

import { useState } from "react"
import { Leaf, LogOut, LayoutDashboard, ClipboardList, Users, Menu, X, Phone } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ROLE_LABELS } from "@/lib/constants"
import { useAppStore } from "@/lib/store"
import { formatPhoneLocal, initials, avatarColor } from "@/lib/helpers"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"

interface Tab {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

interface Props {
  activeTab: string
  onTabChange: (id: string) => void
  tabs: Tab[]
  children: React.ReactNode
}

export function AppShell({ activeTab, onTabChange, tabs, children }: Props) {
  const user = useAppStore((s) => s.user)!
  const logout = useAppStore((s) => s.logout)
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      {/* Header */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow-sm">
              <Leaf className="w-5 h-5" />
            </div>
            <div className="hidden sm:block">
              <h1 className="text-sm font-bold text-slate-900 dark:text-white leading-tight">CCVideira Capim Macio</h1>
              <p className="text-[11px] text-slate-500 leading-tight">Follow-up · Natal</p>
            </div>
          </div>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {tabs.map((t) => (
              <Button
                key={t.id}
                variant={activeTab === t.id ? "default" : "ghost"}
                size="sm"
                onClick={() => onTabChange(t.id)}
                className={activeTab === t.id ? "bg-emerald-600 hover:bg-emerald-700" : ""}
              >
                <t.icon className="w-4 h-4 mr-1.5" />
                {t.label}
              </Button>
            ))}
          </nav>

          {/* User */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex flex-col items-end">
              <span className="text-sm font-medium text-slate-900 dark:text-white">{user.name}</span>
              <Badge variant="outline" className="text-[10px]">{ROLE_LABELS[user.role]}</Badge>
            </div>
            <Avatar className="w-9 h-9">
              <AvatarFallback className={`text-xs text-white ${avatarColor(user.name)}`}>
                {initials(user.name)}
              </AvatarFallback>
            </Avatar>
            <Button variant="ghost" size="icon" onClick={logout} title="Sair">
              <LogOut className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMenuOpen(true)}>
              <Menu className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Mobile menu */}
      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="w-64">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Leaf className="w-4 h-4 text-emerald-600" /> Menu
            </SheetTitle>
          </SheetHeader>
          <div className="mt-4 flex flex-col gap-1">
            {tabs.map((t) => (
              <Button
                key={t.id}
                variant={activeTab === t.id ? "default" : "ghost"}
                onClick={() => {
                  onTabChange(t.id)
                  setMenuOpen(false)
                }}
                className={`justify-start ${activeTab === t.id ? "bg-emerald-600 hover:bg-emerald-700" : ""}`}
              >
                <t.icon className="w-4 h-4 mr-2" /> {t.label}
              </Button>
            ))}
            <div className="border-t my-2" />
            <div className="px-3 py-2 text-xs text-slate-500">
              <p className="flex items-center gap-1"><Phone className="w-3 h-3" /> {formatPhoneLocal(user.phone)}</p>
              {user.department && <p className="mt-1">{user.department.name}</p>}
            </div>
            <Button variant="ghost" onClick={logout} className="justify-start text-rose-600">
              <LogOut className="w-4 h-4 mr-2" /> Sair
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-4 pb-12">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-3 text-xs text-slate-500 flex items-center justify-between">
          <span>CCVideira Capim Macio — Follow-up</span>
          <span className="hidden sm:inline">"Eu sou a videira; vocês são os ramos." — Jo 15.5</span>
        </div>
      </footer>
    </div>
  )
}
