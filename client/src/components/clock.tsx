"use client"

import { useEffect, useState } from "react"
import { Clock as ClockIcon } from "lucide-react"

export function Clock() {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date())
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('es-ES', { 
      timeZone: 'UTC',
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      hour12: false 
    })
  }

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('es-ES', {
      timeZone: 'UTC',
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    })
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/50 border border-border">
      <ClockIcon className="h-4 w-4 text-muted-foreground" />
      <div className="flex flex-col">
        <div className="text-sm font-mono font-semibold">{formatTime(time)} UTC</div>
        <div className="text-xs text-muted-foreground">{formatDate(time)}</div>
      </div>
    </div>
  )
}

