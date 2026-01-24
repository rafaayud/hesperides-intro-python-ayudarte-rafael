"use client"

import { STRATEGIES } from "@/lib/trading-data"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Activity } from "lucide-react"

interface StrategyPanelProps {
  selectedStrategy: string | null
  onSelect: (strategyId: string) => void
  onBacktest: () => void
  onStartTrading: () => void
  isBacktesting: boolean
  isTrading: boolean
}

export function StrategyPanel({
  selectedStrategy,
  onSelect,
  onBacktest,
  onStartTrading,
  isBacktesting,
  isTrading,
}: StrategyPanelProps) {
  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Trading Strategies</CardTitle>
        <CardDescription>Select a strategy to backtest or trade</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {STRATEGIES.map((strategy) => (
          <div
            key={strategy.id}
            onClick={() => onSelect(strategy.id)}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              selectedStrategy === strategy.id
                ? "border-primary bg-primary/10"
                : "border-border hover:border-muted-foreground"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-medium">{strategy.name}</span>
              {strategy.id === "ma_crossover" ? (
                <TrendingUp className="h-4 w-4 text-primary" />
              ) : (
                <Activity className="h-4 w-4 text-primary" />
              )}
            </div>
            <p className="text-xs text-muted-foreground mb-2">{strategy.description}</p>
            <div className="flex flex-wrap gap-1">
              {Object.entries(strategy.params).map(([key, value]) => (
                <Badge key={key} variant="secondary" className="text-xs">
                  {key}: {value}
                </Badge>
              ))}
            </div>
          </div>
        ))}

        <div className="flex flex-col gap-2 pt-2">
          <Button
            onClick={onBacktest}
            disabled={!selectedStrategy || isBacktesting}
            className="w-full bg-transparent"
            variant="outline"
          >
            {isBacktesting ? "Running Backtest..." : "Run Backtest"}
          </Button>
          <Button
            onClick={onStartTrading}
            disabled={!selectedStrategy}
            className="w-full bg-primary hover:bg-primary/90"
          >
            {isTrading ? "Stop Trading" : "Start Paper Trading"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
