"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { 
  TrendingUp, 
  TrendingDown,
  BarChart3,
  ExternalLink
} from "lucide-react"
import type { Trader, Trade } from "@/lib/api"
import { CRYPTO_PAIRS, TIMEFRAME_LABELS } from "@/lib/trading-data"

interface TraderCardProps {
  trader: Trader
  trades: Trade[]
  onViewChart: () => void
}

export function TraderCard({ trader, trades, onViewChart }: TraderCardProps) {
  const pairInfo = CRYPTO_PAIRS.find(p => p.symbol === trader.symbol)
  const intervalLabel = TIMEFRAME_LABELS[trader.interval] || trader.interval
  
  // Calculate trader stats
  const totalPnl = trades.reduce((sum, t) => sum + (t.pnl || 0), 0)
  const winningTrades = trades.filter(t => (t.pnl || 0) > 0).length
  const winRate = trades.length > 0 ? (winningTrades / trades.length) * 100 : 0
  const lastTrade = trades[0]

  return (
    <Card className="border-border/50 hover:border-primary/50 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
              {pairInfo?.icon || trader.symbol.slice(0, 2)}
            </div>
            <div>
              <div className="font-medium flex items-center gap-2">
                {trader.symbol}
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  {intervalLabel}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground">
                {trader.strategy || trader.strategy_name || 'Strategy'}
              </div>
            </div>
          </div>
          
          <Button 
            size="sm" 
            variant="ghost" 
            onClick={onViewChart}
            className="h-8 px-2"
          >
            <BarChart3 className="h-4 w-4 mr-1" />
            Chart
            <ExternalLink className="h-3 w-3 ml-1" />
          </Button>
        </div>
        
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-secondary/30 rounded p-2">
            <div className="text-[10px] text-muted-foreground uppercase">Trades</div>
            <div className="font-semibold">{trades.length}</div>
          </div>
          <div className="bg-secondary/30 rounded p-2">
            <div className="text-[10px] text-muted-foreground uppercase">Win Rate</div>
            <div className={`font-semibold ${winRate >= 50 ? 'text-profit' : 'text-loss'}`}>
              {winRate.toFixed(0)}%
            </div>
          </div>
          <div className="bg-secondary/30 rounded p-2">
            <div className="text-[10px] text-muted-foreground uppercase">PnL</div>
            <div className={`font-semibold font-mono ${totalPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
              {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}
            </div>
          </div>
        </div>
        
        {lastTrade && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Last trade:</span>
              <span className={`font-mono font-medium ${(lastTrade.pnl || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                {(lastTrade.pnl || 0) >= 0 ? '+' : ''}{(lastTrade.pnl || 0).toFixed(2)}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

