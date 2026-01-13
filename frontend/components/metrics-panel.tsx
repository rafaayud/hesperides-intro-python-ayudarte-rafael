"use client"

import type React from "react"

import type { BacktestResult } from "@/lib/trading-data"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Target, Activity, DollarSign, BarChart3 } from "lucide-react"

interface MetricsPanelProps {
  backtestResult: BacktestResult | null
  currentPrice: number
  paperBalance: number
  paperPosition: { amount: number; entryPrice: number } | null
}

export function MetricsPanel({ backtestResult, currentPrice, paperBalance, paperPosition }: MetricsPanelProps) {
  const unrealizedPnL = paperPosition
    ? ((currentPrice - paperPosition.entryPrice) / paperPosition.entryPrice) * 100 * paperPosition.amount
    : 0

  return (
    <div className="space-y-4">
      {/* Paper Trading Status */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Paper Trading</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Balance
            </span>
            <span className="font-mono text-lg">${paperBalance.toFixed(2)}</span>
          </div>
          {paperPosition && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Position</span>
                <span className="font-mono">{paperPosition.amount.toFixed(4)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Entry Price</span>
                <span className="font-mono">${paperPosition.entryPrice.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Unrealized P&L</span>
                <span className={`font-mono ${unrealizedPnL >= 0 ? "text-profit" : "text-loss"}`}>
                  {unrealizedPnL >= 0 ? "+" : ""}
                  {unrealizedPnL.toFixed(2)}%
                </span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Backtest Results */}
      {backtestResult && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Backtest Results</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <MetricItem
              icon={<BarChart3 className="h-4 w-4" />}
              label="Total Trades"
              value={backtestResult.totalTrades.toString()}
            />
            <MetricItem
              icon={<Target className="h-4 w-4" />}
              label="Win Rate"
              value={`${backtestResult.winRate.toFixed(1)}%`}
              positive={backtestResult.winRate >= 50}
            />
            <MetricItem
              icon={
                backtestResult.totalReturn >= 0 ? (
                  <TrendingUp className="h-4 w-4" />
                ) : (
                  <TrendingDown className="h-4 w-4" />
                )
              }
              label="Total Return"
              value={`${backtestResult.totalReturn >= 0 ? "+" : ""}${backtestResult.totalReturn.toFixed(2)}%`}
              positive={backtestResult.totalReturn >= 0}
            />
            <MetricItem
              icon={<Activity className="h-4 w-4" />}
              label="Max Drawdown"
              value={`-${backtestResult.maxDrawdown.toFixed(2)}%`}
              positive={false}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function MetricItem({
  icon,
  label,
  value,
  positive,
}: {
  icon: React.ReactNode
  label: string
  value: string
  positive?: boolean
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <span
        className={`font-mono text-lg ${positive !== undefined ? (positive ? "text-profit" : "text-loss") : "text-foreground"}`}
      >
        {value}
      </span>
    </div>
  )
}
