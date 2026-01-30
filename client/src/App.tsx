"use client"

import { useState, useCallback } from "react"

import { CryptoSelector } from "@/components/crypto-selector" 
import { TimeframeSelector } from "@/components/timeframe-selector"
import { TradingViewChart } from "@/components/candlestick-chart"
import { CryptoTicker } from "@/components/crypto-ticker"
import { Clock } from "@/components/clock"
import { CreatePortfolio } from "@/components/create-portfolio"
import { PortfolioSelector } from "@/components/portfolio-selector"
import { PricePanel } from "@/components/price-panel"
import { Toaster } from "@/components/ui/sonner"
import { Activity } from "lucide-react"

export default function App() {
  const [selectedPair, setSelectedPair] = useState("BTCUSDT")
  const [timeframe, setTimeframe] = useState("H1") // Usamos claves de API: H1, M1, etc.
  
  // Estado para el precio real que viene del gráfico
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [isPriceUp, setIsPriceUp] = useState<boolean>(true) // true = verde (subida), false = rojo (bajada)
  

  // Esta función recibe el precio desde el componente TradingViewChart
  const handlePriceUpdate = useCallback((price: number, isUp: boolean) => {
    setCurrentPrice(price)
    setIsPriceUp(isUp)
    
    // AQUÍ IRÍA TU LÓGICA DE TRADING AUTOMÁTICO EN EL FUTURO
    // Si (Estrategia === "RSI" && price < ...) -> Comprar
  }, [])

  const handleTraderSelect = useCallback((payload: { symbol: string; interval: string }) => {
    setSelectedPair(payload.symbol)
    setTimeframe(payload.interval)
  }, [])

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Toaster />
      {/* Crypto Ticker Bar */}
      <CryptoTicker />
      
      <div className="p-4 md:p-6">
        <div className="max-w-[1600px] mx-auto space-y-4">
          
          {/* Header */}
          <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
                <Activity className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-semibold">CryptoTrader</h1>
                <p className="text-xs text-muted-foreground">Real-time Binance Data</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <CryptoSelector value={selectedPair} onChange={setSelectedPair} />
              <TimeframeSelector value={timeframe} onChange={setTimeframe} />
              
              <Clock />
            </div>
          </header>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          
          {/* Gráfico (Ocupa 3 columnas) */}
          <div className="lg:col-span-3 space-y-4 relative">
            <div className="bg-card rounded-lg border border-border p-4 shadow-sm">
              <div className="mb-2">
                <h2 className="text-lg font-semibold">{selectedPair}</h2>
                <p className="text-xs text-muted-foreground">Candlestick Chart with Volume</p>
              </div>
              <div className="h-[700px] w-full">
                {/* Pasamos la función para recibir el precio */}
                <TradingViewChart 
                  symbol={selectedPair} 
                  interval={timeframe} 
                  onPriceUpdate={handlePriceUpdate} 
                />
              </div>
            </div>

            {/* Create Portfolio Component - Debajo de la gráfica */}
            <div className="relative mt-6" style={{ zIndex: 10 }}>
              <CreatePortfolio />
            </div>
          </div>

          {/* Sidebar (Ocupa 1 columna) */}
          <div className="space-y-4">
            {/* Panel de Precio Actual */}
            <PricePanel
              currentPrice={currentPrice}
              isPriceUp={isPriceUp}
              symbol={selectedPair}
            />
            
            {/* Portfolio Selector */}
            <PortfolioSelector onTraderSelect={handleTraderSelect} />
          </div>
        </div>
        </div>
      </div>
    </div>
  )
}