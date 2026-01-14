"use client"

import { CRYPTO_PAIRS } from "@/lib/trading-data"
import { useState } from "react"
import { ChevronsUpDown, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { cn } from "@/lib/utils"

interface CryptoSelectorProps {
  value: string
  onChange: (value: string) => void
}

export function CryptoSelector({ value, onChange }: CryptoSelectorProps) {
  const [open, setOpen] = useState(false)
  const selected = CRYPTO_PAIRS.find((p) => p.symbol === value)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-[200px] justify-between bg-secondary border-border"
        >
          {selected ? (
            <span className="flex items-center gap-2 truncate">
              <span className="text-primary font-mono">{selected.icon}</span>
              <span className="truncate">{selected.symbol}</span>
            </span>
          ) : (
            <span className="text-muted-foreground">Select pair...</span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[260px] p-0 bg-card border-border">
        <Command>
          <CommandInput placeholder="Search pair or symbol..." />
          <CommandEmpty>No pair found.</CommandEmpty>
          <CommandList>
            <CommandGroup>
              {CRYPTO_PAIRS.map((pair) => (
                <CommandItem
                  key={pair.symbol}
                  value={`${pair.symbol} ${pair.name}`}
                  onSelect={() => {
                    onChange(pair.symbol)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      pair.symbol === value ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <span className="flex items-center gap-2">
                    <span className="text-primary font-mono">{pair.icon}</span>
                    <span>{pair.name}</span>
                    <span className="text-muted-foreground text-xs">({pair.symbol})</span>
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
