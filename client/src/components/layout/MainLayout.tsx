"use client"

import { useState, useCallback } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BarChart3, Briefcase, Settings } from "lucide-react"
import { Header } from "./Header"
import { TradingView } from "@/components/views/TradingView"
import { PortfoliosView } from "@/components/views/PortfoliosView"

export type ChartConfig = {
  symbol: string
  interval: string
  portfolioId?: string
  traderId?: string
}

export function MainLayout() {
  const [activeTab, setActiveTab] = useState("trading")
  
  // Chart configuration - can be updated from PortfoliosView
  const [chartConfig, setChartConfig] = useState<ChartConfig>({
    symbol: "BTCUSDT",
    interval: "H1"
  })
  
  // Price state from chart
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [isPriceUp, setIsPriceUp] = useState<boolean>(true)
  
  const handlePriceUpdate = useCallback((price: number, isUp: boolean) => {
    setCurrentPrice(price)
    setIsPriceUp(isUp)
  }, [])
  
  // When a trader is selected from portfolios, switch to trading tab and load the chart
  const handleTraderSelect = useCallback((config: ChartConfig) => {
    setChartConfig(config)
    setActiveTab("trading")
  }, [])

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Header />
      
      <div className="flex-1 flex">
        {/* Main content area */}
        <main className="flex-1 p-4">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
            <div className="flex items-center justify-between mb-4">
              <TabsList className="bg-secondary/50">
                <TabsTrigger 
                  value="trading" 
                  className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground gap-2"
                >
                  <BarChart3 className="h-4 w-4" />
                  Trading
                </TabsTrigger>
                <TabsTrigger 
                  value="portfolios"
                  className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground gap-2"
                >
                  <Briefcase className="h-4 w-4" />
                  Portfolios
                </TabsTrigger>
              </TabsList>
              
              {activeTab === "trading" && (
                <div className="text-sm text-muted-foreground">
                  {chartConfig.portfolioId && chartConfig.traderId ? (
                    <span className="text-primary">
                      Viewing: {chartConfig.portfolioId} / {chartConfig.traderId}
                    </span>
                  ) : (
                    <span>{chartConfig.symbol} • {chartConfig.interval}</span>
                  )}
                </div>
              )}
            </div>
            
            <TabsContent value="trading" className="mt-0 h-[calc(100%-60px)]">
              <TradingView 
                chartConfig={chartConfig}
                setChartConfig={setChartConfig}
                currentPrice={currentPrice}
                isPriceUp={isPriceUp}
                onPriceUpdate={handlePriceUpdate}
              />
            </TabsContent>
            
            <TabsContent value="portfolios" className="mt-0">
              <PortfoliosView onTraderSelect={handleTraderSelect} />
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </div>
  )
}

