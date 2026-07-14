import { NextResponse } from "next/server"
import { getSessionUser } from "@/lib/session"

export async function GET() {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ user: null }, { status: 200 })
  const firstDept = (user as any).departments?.[0] || null
  return NextResponse.json({
    user: {
      id: user.id,
      name: user.name,
      phone: user.phone,
      role: user.role,
      gender: (user as any).gender || null,
      departmentId: firstDept?.id || null,
      department: firstDept,
      departments: (user as any).departments || [],
    },
  })
}
