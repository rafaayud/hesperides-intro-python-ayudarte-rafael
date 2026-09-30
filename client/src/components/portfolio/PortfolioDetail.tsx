"use client"

import { formatPnl } from "@/lib/utils"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  DollarSign, 
  Users, 
  TrendingUp, 
  TrendingDown,
  BarChart3,
  History,
  RefreshCw
} from "lucide-react"
import { TraderCard } from "./TraderCard"
import { TradesTable } from "./TradesTable"
import type { Portfolio, TradingStatus, Trader, Trade } from "@/lib/api"
import type { ChartConfig } from "@/components/layout/MainLayout"
import { backendInterval } from "@/lib/chart-time"

interface PortfolioWithDetails extends Portfolio {
  status?: TradingStatus
  traders?: Trader[]
  trades?: Trade[]
}

interface PortfolioDetailProps {
  portfolio: PortfolioWithDetails
  onTraderSelect: (config: ChartConfig) => void
  onRefresh: () => void
}

export function PortfolioDetail({ portfolio, onTraderSelect, onRefresh }: PortfolioDetailProps) {
  const traders = portfolio.traders || []
  const trades = portfolio.trades || []
  
  // Calculate PnL summary
  const totalPnl = trades.reduce((sum, t) => sum + (t.pnl || 0), 0)
  const winningTrades = trades.filter(t => (t.pnl || 0) > 0).length
  const winRate = trades.length > 0 ? (winningTrades / trades.length) * 100 : 0

  const handleViewTrader = (trader: Trader) => {
    onTraderSelect({
      symbol: trader.symbol,
      interval: backendInterval(trader.interval),
      portfolioId: portfolio.id,
      traderId: trader.id
    })
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl flex flex-wrap items-center gap-2">
              {portfolio.name}
              <Badge 
                variant="outline"
                className={portfolio.status?.is_running ? 'status-running' : 'status-stopped'}
              >
                {portfolio.status?.is_running ? 'Running' : 'Stopped'}
              </Badge>
            </CardTitle>
            <CardDescription className="mt-1">{portfolio.id}</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onRefresh} aria-label="Refresh portfolio">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
          <div className="bg-secondary/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <DollarSign className="h-3.5 w-3.5" />
              Initial Capital
            </div>
            <div className="text-lg font-semibold font-mono">
              ${Math.round(portfolio.initial_capital || 0).toLocaleString()}
            </div>
          </div>
          
          <div className="bg-secondary/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <Users className="h-3.5 w-3.5" />
              Traders
            </div>
            <div className="text-lg font-semibold">
              {traders.length}
            </div>
          </div>
          
          <div className="bg-secondary/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              {totalPnl >= 0 ? (
                <TrendingUp className="h-3.5 w-3.5 text-profit" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 text-loss" />
              )}
              Total PnL
            </div>
            <div className={`text-lg font-semibold font-mono ${totalPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
              {totalPnl >= 0 ? '+' : ''}{formatPnl(totalPnl)}
            </div>
          </div>
          
          <div className="bg-secondary/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <BarChart3 className="h-3.5 w-3.5" />
              Win Rate
            </div>
            <div className={`text-lg font-semibold ${winRate >= 50 ? 'text-profit' : 'text-loss'}`}>
              {winRate.toFixed(1)}%
            </div>
          </div>
        </div>
      </CardHeader>
      
      <Separator />
      
      <CardContent className="pt-4">
        <Tabs defaultValue="traders">
          <TabsList className="mb-4">
            <TabsTrigger value="traders" className="gap-2">
              <Users className="h-4 w-4" />
              Traders ({traders.length})
            </TabsTrigger>
            <TabsTrigger value="trades" className="gap-2">
              <History className="h-4 w-4" />
              Trade History ({trades.length})
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="traders" className="mt-0">
            {traders.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Users className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No traders configured</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {traders.map((trader) => (
                  <TraderCard 
                    key={trader.id} 
                    trader={trader}
                    trades={trades.filter(t => t.trader_id === trader.id)}
                    onViewChart={() => handleViewTrader(trader)}
                  />
                ))}
              </div>
            )}
          </TabsContent>
          
          <TabsContent value="trades" className="mt-0">
            <TradesTable trades={trades} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

