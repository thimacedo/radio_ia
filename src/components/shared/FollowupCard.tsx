"use client"

import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { MessageCircle, Calendar, Clock, User as UserIcon } from "lucide-react"
import { STATUS_LABELS, STATUS_COLORS, PRIORITY_COLORS, PRIORITY_LABELS } from "@/lib/constants"
import { formatPhoneLocal, whatsappLink, timeAgo, formatDate, initials, avatarColor } from "@/lib/helpers"
import { Button } from "@/components/ui/button"

interface CardData {
  id: string
  status: string
  priority: string
  notes?: string | null
  lastContactAt?: string | null
  nextActionAt?: string | null
  createdAt: string
  visitor: {
    id: string
    name: string
    phone: string
    age?: number | null
    gender?: string | null
    maritalStatus?: string | null
    prayerRequest?: string | null
  }
  department?: { id: string; name: string; color?: string | null } | null
  volunteer?: { id: string; name: string; phone: string } | null
  supervisor?: { id: string; name: string; phone: string } | null
}

interface Props {
  card: CardData
  onOpen?: (id: string) => void
  showVolunteer?: boolean
}

export function FollowupCard({ card, onOpen, showVolunteer = true }: Props) {
  const waMsg = `Olá ${card.visitor.name}, aqui é ${card.volunteer?.name || "da equipe"} da CCVideira Capim Macio. Tudo bem?`
  const wa = whatsappLink(card.visitor.phone, waMsg)

  return (
    <Card
      className="p-3 cursor-pointer hover:shadow-md transition-shadow border-l-4 group"
      style={{ borderLeftColor: card.department?.color || "#10b981" }}
      onClick={() => onOpen?.(card.id)}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm text-slate-900 dark:text-slate-100 truncate">{card.visitor.name}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {card.visitor.age ? `${card.visitor.age} anos` : ""}
            {card.visitor.gender ? ` · ${card.visitor.gender === "M" ? "Homem" : card.visitor.gender === "F" ? "Mulher" : "Outro"}` : ""}
          </p>
        </div>
        <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${PRIORITY_COLORS[card.priority] || PRIORITY_COLORS.normal}`}>
          {PRIORITY_LABELS[card.priority] || "Normal"}
        </Badge>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-2">
        <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${STATUS_COLORS[card.status] || STATUS_COLORS.novo}`}>
          {STATUS_LABELS[card.status] || card.status}
        </Badge>
        {card.department && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            {card.department.name}
          </Badge>
        )}
      </div>

      {card.nextActionAt && (
        <div className="flex items-center gap-1 text-xs text-amber-700 dark:text-amber-400 mb-2">
          <Calendar className="w-3 h-3" />
          <span>Próx. ação: {formatDate(card.nextActionAt)}</span>
        </div>
      )}

      {showVolunteer && card.volunteer && (
        <div className="flex items-center gap-1.5 mb-2">
          <Avatar className="w-5 h-5">
            <AvatarFallback className={`text-[9px] text-white ${avatarColor(card.volunteer.name)}`}>
              {initials(card.volunteer.name)}
            </AvatarFallback>
          </Avatar>
          <span className="text-xs text-slate-500 dark:text-slate-400 truncate">{card.volunteer.name}</span>
        </div>
      )}
      {showVolunteer && !card.volunteer && (
        <div className="flex items-center gap-1 text-xs text-slate-400 italic mb-2">
          <UserIcon className="w-3 h-3" /> Sem voluntário
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
        <span className="text-[10px] text-slate-400 flex items-center gap-1">
          <Clock className="w-3 h-3" /> {timeAgo(card.createdAt)}
        </span>
        <a
          href={wa}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
        >
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-900/20"
          >
            <MessageCircle className="w-3.5 h-3.5 mr-1" />
            WhatsApp
          </Button>
        </a>
      </div>
    </Card>
  )
}
