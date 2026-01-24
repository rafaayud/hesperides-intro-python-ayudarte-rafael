import type React from "react"
import type { BacktestResult } from "@/lib/trading-data"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Target, Activity, DollarSign, BarChart3, TrendingUp as TrendingUpIcon, TrendingDown as TrendingDownIcon } from "lucide-react"

interface MetricsPanelProps {
  backtestResult: BacktestResult | null
  currentPrice: number
  isPriceUp?: boolean
  paperBalance: number
  paperPosition: { amount: number; entryPrice: number } | null
}

export function MetricsPanel({ backtestResult, currentPrice, isPriceUp = true, paperBalance, paperPosition }: MetricsPanelProps) {
  const unrealizedPnL = paperPosition
    ? ((currentPrice - paperPosition.entryPrice) / paperPosition.entryPrice) * 100 * paperPosition.amount
    : 0

  const totalPnL = paperPosition
    ? ((currentPrice - paperPosition.entryPrice) / paperPosition.entryPrice) * 100
    : 0

  return (
    <div className="space-y-4">
      {/* Current Price Display */}
      {currentPrice > 0 && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Current Price</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-mono font-bold transition-colors ${
              isPriceUp ? "text-profit" : "text-loss"
            }`}>
              ${currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Paper Trading Status */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            Paper Trading
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Balance</span>
            <span className="font-mono text-lg font-semibold">${paperBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
          {paperPosition && (
            <>
              <div className="pt-2 border-t border-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Position</span>
                  <span className="font-mono">{paperPosition.amount.toFixed(4)}</span>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Entry Price</span>
                  <span className="font-mono">${paperPosition.entryPrice.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Unrealized P&L</span>
                  <div className={`flex items-center gap-1 font-mono font-semibold ${totalPnL >= 0 ? "text-profit" : "text-loss"}`}>
                    {totalPnL >= 0 ? (
                      <TrendingUpIcon className="h-3 w-3" />
                    ) : (
                      <TrendingDownIcon className="h-3 w-3" />
                    )}
                    <span>
                      {totalPnL >= 0 ? "+" : ""}
                      {totalPnL.toFixed(2)}%
                    </span>
                  </div>
                </div>
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
