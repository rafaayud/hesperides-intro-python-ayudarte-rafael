"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown } from "lucide-react"

interface PricePanelProps {
  currentPrice: number
  isPriceUp: boolean
  symbol: string
}

export function PricePanel({ currentPrice, isPriceUp, symbol }: PricePanelProps) {
  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Current Price</CardTitle>
        <CardDescription>{symbol}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 ${isPriceUp ? "text-green-500" : "text-red-500"}`}>
            {isPriceUp ? (
              <TrendingUp className="h-6 w-6" />
            ) : (
              <TrendingDown className="h-6 w-6" />
            )}
          </div>
          <div>
            <div className="text-2xl font-bold">
              ${currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className={`text-xs ${isPriceUp ? "text-green-500" : "text-red-500"}`}>
              {isPriceUp ? "↑" : "↓"} Live
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

