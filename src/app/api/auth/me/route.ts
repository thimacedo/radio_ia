import { NextResponse } from "next/server"
import { getSessionUser } from "@/lib/session"

export async function GET() {
  const user = await getSessionUser()
  if (!user) return NextResponse.json({ user: null }, { status: 200 })
  return NextResponse.json({
    user: {
      id: user.id,
      name: user.name,
      phone: user.phone,
      role: user.role,
      departmentId: user.departmentId,
      department: user.department,
    },
  })
}
