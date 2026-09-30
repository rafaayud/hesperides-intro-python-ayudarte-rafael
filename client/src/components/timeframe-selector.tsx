"use client"

import { TIMEFRAMES, TIMEFRAME_LABELS } from "@/lib/trading-data"
import { Button } from "@/components/ui/button"

interface TimeframeSelectorProps {
  value: string      // Aquí llega "H1", "M5", etc.
  onChange: (value: string) => void
}

export function TimeframeSelector({ value, onChange }: TimeframeSelectorProps) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      {TIMEFRAMES.map((tf) => (
        <Button
          key={tf}
          variant={value === tf ? "default" : "ghost"}
          size="sm"
          onClick={() => onChange(tf)} // Envía "H1" a la API
          className={
            value === tf 
              ? "bg-primary text-primary-foreground" 
              : "text-muted-foreground hover:text-foreground"
          }
        >
          {/* Aquí mostramos "1h", "5m", etc. en lugar de "H1" o "M5" */}
          {TIMEFRAME_LABELS[tf]} 
        </Button>
      ))}
    </div>
  )
}
