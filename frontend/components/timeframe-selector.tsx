"use client"

import { TIMEFRAMES } from "@/lib/trading-data"
import { Button } from "@/components/ui/button"

interface TimeframeSelectorProps {
  value: string
  onChange: (value: string) => void
}

export function TimeframeSelector({ value, onChange }: TimeframeSelectorProps) {
  return (
    <div className="flex items-center gap-1">
      {TIMEFRAMES.map((tf) => (
        <Button
          key={tf}
          variant={value === tf ? "default" : "ghost"}
          size="sm"
          onClick={() => onChange(tf)}
          className={
            value === tf ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
          }
        >
          {tf}
        </Button>
      ))}
    </div>
  )
}
