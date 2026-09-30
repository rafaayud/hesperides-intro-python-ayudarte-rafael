"use client"

import { useState, useEffect } from "react"
import { CryptoSelector } from "@/components/crypto-selector"
import { TimeframeSelector } from "@/components/timeframe-selector"
import { TradingViewChart } from "@/components/candlestick-chart"
import { PortfolioSelector } from "@/components/portfolio-selector"
import { GlobalStats } from "@/components/dashboard/GlobalStats"
import { PositionsPieChart } from "@/components/dashboard/PositionsPieChart"
import { TradesTable } from "@/components/portfolio/TradesTable"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TrendingUp, TrendingDown, X, BarChart3, History } from "lucide-react"
import { listPortfolios, getPortfolioTrades, type Trade } from "@/lib/api"
import type { ChartConfig } from "@/components/layout/MainLayout"

interface TradingViewProps {
  chartConfig: ChartConfig
  setChartConfig: (config: ChartConfig) => void
  currentPrice: number
  isPriceUp: boolean
  onPriceUpdate: (price: number, isUp: boolean) => void
}

export function TradingView({ 
  chartConfig, 
  setChartConfig, 
  currentPrice, 
  isPriceUp,
  onPriceUpdate 
}: TradingViewProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loadingTrades, setLoadingTrades] = useState(false)
  
  const isViewingTrader = chartConfig.portfolioId && chartConfig.traderId
  
  // Load trades - all trades or filtered by trader
  useEffect(() => {
    let disposed = false
    setTrades([])
    const loadTrades = async () => {
      try {
        if (isViewingTrader && chartConfig.portfolioId) {
          // Load trades for specific trader
          const result = await getPortfolioTrades(chartConfig.portfolioId, chartConfig.traderId)
          if (!disposed) setTrades(result.trades)
        } else {
          // Load all trades from all portfolios
          const portfolios = await listPortfolios()
          const allTrades: Trade[] = []
          for (const portfolio of portfolios) {
            try {
              const result = await getPortfolioTrades(portfolio.id)
              allTrades.push(...result.trades)
            } catch {
              // Skip portfolios that fail
            }
          }
          // Sort by exit_time descending
          allTrades.sort((a, b) => new Date(b.exit_time).getTime() - new Date(a.exit_time).getTime())
          if (!disposed) setTrades(allTrades.slice(0, 50)) // Limit to 50 most recent
        }
      } catch (error) {
        console.error("Error loading trades:", error)
      } finally {
        if (!disposed) setLoadingTrades(false)
      }
    }
    
    setLoadingTrades(true)
    void loadTrades()
    const timer = window.setInterval(loadTrades, 10000)
    return () => {
      disposed = true
      window.clearInterval(timer)
    }
  }, [isViewingTrader, chartConfig.portfolioId, chartConfig.traderId])
  
  const clearTraderView = () => {
    setChartConfig({
      ...chartConfig,
      portfolioId: undefined,
      traderId: undefined
    })
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
      {/* Chart area - 3 columns */}
      <div className="lg:col-span-3 flex flex-col gap-4">
        
        {/* Trader viewing banner - prominent when viewing a trader */}
        {isViewingTrader && (
          <Card className="border-primary/30 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-primary/20 flex items-center justify-center">
                    <BarChart3 className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">Viewing Trader</span>
                      <Badge variant="outline" className="bg-primary/10 border-primary/30 text-primary text-[10px]">
                        Live
                      </Badge>
                    </div>
                    <div className="font-semibold text-lg">
                      {chartConfig.traderId?.split('_').slice(-2).join(' • ')}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right hidden sm:block">
                    <div className="text-xs text-muted-foreground">Portfolio</div>
                    <div className="font-medium text-sm">{chartConfig.portfolioId}</div>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={clearTraderView}
                    className="h-8 w-8 p-0 hover:bg-destructive/10 hover:text-destructive"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Controls row */}
        <Card className="border-border/50">
          <CardContent className="p-3">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <CryptoSelector 
                  value={chartConfig.symbol} 
                  onChange={(symbol) => setChartConfig({ ...chartConfig, symbol, portfolioId: undefined, traderId: undefined })} 
                />
                <TimeframeSelector 
                  value={chartConfig.interval} 
                  onChange={(interval) => setChartConfig({ ...chartConfig, interval })} 
                />
              </div>
              
              {/* Live price */}
              <div className={`flex items-center gap-3 px-4 py-2 rounded-lg border ${
                isPriceUp 
                  ? 'bg-profit/5 border-profit/20' 
                  : 'bg-loss/5 border-loss/20'
              }`}>
                {isPriceUp ? (
                  <TrendingUp className="h-5 w-5 text-profit" />
                ) : (
                  <TrendingDown className="h-5 w-5 text-loss" />
                )}
                <div className="flex items-center gap-2">
                  <span className={`text-xl font-mono font-bold ${isPriceUp ? 'text-profit' : 'text-loss'}`}>
                    ${currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <Badge variant="outline" className={`${isPriceUp ? 'border-profit/30 text-profit' : 'border-loss/30 text-loss'}`}>
                    {chartConfig.symbol.replace('USDT', '')}
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Chart */}
        <Card className="border-border/50 overflow-hidden flex-1">
          <CardContent className="p-0 h-full">
            <div className="h-[500px] w-full">
              <TradingViewChart 
                symbol={chartConfig.symbol} 
                interval={chartConfig.interval}
                trades={trades}
                onPriceUpdate={onPriceUpdate} 
              />
            </div>
          </CardContent>
        </Card>
        
        {/* Trades Table */}
        <Card className="border-border/50">
          <CardHeader className="py-3 px-4 border-b border-border/50">
            <CardTitle className="text-base flex items-center gap-2">
              <History className="h-4 w-4 text-primary" />
              {isViewingTrader ? (
                <span className="flex items-center gap-2">
                  Trades
                  <span className="text-muted-foreground font-normal">
                    {chartConfig.traderId?.split('_').slice(-2).join(' ')}
                  </span>
                  <Badge variant="secondary" className="text-[10px] font-normal">
                    {trades.length}
                  </Badge>
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  Recent Trades
                  <Badge variant="secondary" className="text-[10px] font-normal">
                    {trades.length}
                  </Badge>
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-[280px] overflow-auto">
              <TradesTable trades={trades} loading={loadingTrades} />
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Sidebar - 1 column */}
      <div className="flex flex-col gap-4">
        <GlobalStats />
        <PositionsPieChart />
        <PortfolioSelector />
      </div>
    </div>
  )
}
