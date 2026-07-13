"use client"

import { create } from "zustand"

export type Role = "admin" | "recepcao" | "supervisor" | "voluntario"

export interface SessionUser {
  id: string
  name: string
  phone: string
  role: Role
  departmentId: string | null
  department: { id: string; name: string; color?: string | null } | null
}

interface AppState {
  user: SessionUser | null
  loadingUser: boolean
  view: "lista" | "kanban"
  setUser: (u: SessionUser | null) => void
  setLoadingUser: (b: boolean) => void
  setView: (v: "lista" | "kanban") => void
  logout: () => void
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  loadingUser: true,
  view: "lista",
  setUser: (u) => set({ user: u, loadingUser: false }),
  setLoadingUser: (b) => set({ loadingUser: b }),
  setView: (v) => set({ view: v }),
  logout: () => {
    fetch("/api/auth/logout", { method: "POST" })
    set({ user: null })
  },
}))
