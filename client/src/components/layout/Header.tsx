"use client"

import { Activity } from "lucide-react"
import { CryptoTicker } from "@/components/crypto-ticker"
import { Clock } from "@/components/clock"

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      {/* Top bar with logo and clock */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
            <Activity className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-semibold font-[family-name:var(--font-display)] tracking-tight">
              CryptoTrader
            </h1>
            <p className="text-[10px] text-muted-foreground leading-none">
              Paper Trading Dashboard
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-profit animate-pulse-dot" />
            <span className="text-xs text-muted-foreground">Live</span>
          </div>
          <Clock />
        </div>
      </div>
      
      {/* Ticker bar */}
      <CryptoTicker />
    </header>
  )
}

