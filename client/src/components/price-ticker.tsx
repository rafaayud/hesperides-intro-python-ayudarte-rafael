"use client"

import { useEffect, useState } from "react"
import type { Candle } from "@/lib/trading-data"
import { TrendingUp, TrendingDown } from "lucide-react"

interface PriceTickerProps {
  symbol: string
  candles: Candle[]
}

export function PriceTicker({ symbol, candles }: PriceTickerProps) {
  const [flash, setFlash] = useState<"up" | "down" | null>(null)

  const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0
  const prevPrice = candles.length > 1 ? candles[candles.length - 2].close : currentPrice
  const change = currentPrice - prevPrice
  const changePercent = prevPrice > 0 ? (change / prevPrice) * 100 : 0
  const isPositive = change >= 0

  const high24h = candles.length > 0 ? Math.max(...candles.slice(-24).map((c) => c.high)) : 0
  const low24h = candles.length > 0 ? Math.min(...candles.slice(-24).map((c) => c.low)) : 0
  const volume24h = candles.length > 0 ? candles.slice(-24).reduce((sum, c) => sum + c.volume, 0) : 0

  useEffect(() => {
    if (change !== 0) {
      setFlash(change > 0 ? "up" : "down")
      const timer = setTimeout(() => setFlash(null), 200)
      return () => clearTimeout(timer)
    }
  }, [currentPrice, change])

  return (
    <div className="flex items-center gap-6 flex-wrap">
      <div className="flex items-center gap-3">
        <div>
          <div className="text-xs text-muted-foreground">{symbol}</div>
          <div
            className={`text-2xl font-mono font-semibold transition-colors ${
              flash === "up" ? "text-profit" : flash === "down" ? "text-loss" : "text-foreground"
            }`}
          >
            ${currentPrice.toFixed(2)}
          </div>
        </div>
        <div className={`flex items-center gap-1 ${isPositive ? "text-profit" : "text-loss"}`}>
          {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
          <span className="font-mono text-sm">
            {isPositive ? "+" : ""}
            {changePercent.toFixed(2)}%
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-sm">
        <div>
          <div className="text-xs text-muted-foreground">24h High</div>
          <div className="font-mono text-profit">${high24h.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">24h Low</div>
          <div className="font-mono text-loss">${low24h.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">24h Volume</div>
          <div className="font-mono">{(volume24h / 1000000).toFixed(2)}M</div>
        </div>
      </div>
    </div>
  )
}
