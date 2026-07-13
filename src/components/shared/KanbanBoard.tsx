"use client"

import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCorners, useDroppable, type DragEndEvent, type DragStartEvent } from "@dnd-kit/core"
import { SortableContext, verticalListSortingStrategy, useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { useState } from "react"
import { STATUS_KANBAN_COLUMNS } from "@/lib/constants"
import { FollowupCard } from "./FollowupCard"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { Users, Loader2 } from "lucide-react"

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
  cards: CardData[]
  onOpen: (id: string) => void
  onMove: (cardId: string, newStatus: string) => Promise<void>
}

function SortableCard({ card, onOpen }: { card: CardData; onOpen: (id: string) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: card.id })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing">
      <FollowupCard card={card} onOpen={onOpen} />
    </div>
  )
}

function Column({ statusKey, col, colCards, onOpen }: { statusKey: string; col: any; colCards: CardData[]; onOpen: (id: string) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: statusKey })
  return (
    <div className="w-72 shrink-0">
      <div className={`rounded-t-md border-t-4 ${col.color} ${col.accent} p-2.5 flex items-center justify-between`}>
        <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">{col.title}</h3>
        <span className="text-xs bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-full px-2 py-0.5 flex items-center gap-1">
          <Users className="w-3 h-3" />
          {colCards.length}
        </span>
      </div>
      <div
        ref={setNodeRef}
        className={`min-h-[200px] p-2 space-y-2 rounded-b-md border border-t-0 border-slate-200 dark:border-slate-800 ${col.accent} ${isOver ? "ring-2 ring-emerald-400" : ""}`}
      >
        <SortableContext items={colCards.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          {colCards.map((card) => (
            <SortableCard key={card.id} card={card} onOpen={onOpen} />
          ))}
        </SortableContext>
        {colCards.length === 0 && (
          <div className="text-center text-xs text-slate-400 py-8 italic">Solte cards aqui</div>
        )}
      </div>
    </div>
  )
}

export function KanbanBoard({ cards, onOpen, onMove }: Props) {
  const [activeCard, setActiveCard] = useState<CardData | null>(null)
  const [moving, setMoving] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  const columns = Object.entries(STATUS_KANBAN_COLUMNS)

  function handleDragStart(e: DragStartEvent) {
    const c = cards.find((c) => c.id === e.active.id)
    if (c) setActiveCard(c)
  }

  async function handleDragEnd(e: DragEndEvent) {
    setActiveCard(null)
    const { active, over } = e
    if (!over) return
    const card = cards.find((c) => c.id === active.id)
    if (!card) return
    // over.id pode ser a coluna (status) ou outro card
    let newStatus: string | null = null
    const overId = String(over.id)
    if (STATUS_KANBAN_COLUMNS[overId]) {
      newStatus = overId
    } else {
      // é um card; pega status dele
      const overCard = cards.find((c) => c.id === overId)
      if (overCard) newStatus = overCard.status
    }
    if (!newStatus || newStatus === card.status) return
    setMoving(card.id)
    try {
      await onMove(card.id, newStatus)
    } finally {
      setMoving(null)
    }
  }

  return (
    <div className="relative">
      {moving && (
        <div className="absolute top-2 right-2 z-50 bg-emerald-600 text-white px-3 py-1.5 rounded-md text-xs flex items-center gap-2 shadow-lg">
          <Loader2 className="w-3 h-3 animate-spin" /> Movendo card...
        </div>
      )}
      <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <ScrollArea className="w-full whitespace-nowrap rounded-md">
          <div className="flex gap-4 min-w-max pb-4 px-1">
            {columns.map(([statusKey, col]) => (
              <Column key={statusKey} statusKey={statusKey} col={col} colCards={cards.filter((c) => c.status === statusKey)} onOpen={onOpen} />
            ))}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </DndContext>

      <DragOverlay>
        {activeCard ? (
          <div className="opacity-90 rotate-2 w-72">
            <FollowupCard card={activeCard} />
          </div>
        ) : null}
      </DragOverlay>
    </div>
  )
}
