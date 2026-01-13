"use client"

import { CRYPTO_PAIRS } from "@/lib/trading-data"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface CryptoSelectorProps {
  value: string
  onChange: (value: string) => void
}

export function CryptoSelector({ value, onChange }: CryptoSelectorProps) {
  const selected = CRYPTO_PAIRS.find((p) => p.symbol === value)

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-[180px] bg-secondary border-border">
        <SelectValue>
          {selected && (
            <span className="flex items-center gap-2">
              <span className="text-primary font-mono">{selected.icon}</span>
              <span>{selected.symbol}</span>
            </span>
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="bg-card border-border">
        {CRYPTO_PAIRS.map((pair) => (
          <SelectItem key={pair.symbol} value={pair.symbol}>
            <span className="flex items-center gap-2">
              <span className="text-primary font-mono">{pair.icon}</span>
              <span>{pair.name}</span>
              <span className="text-muted-foreground text-xs">({pair.symbol})</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
