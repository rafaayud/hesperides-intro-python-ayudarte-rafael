"use client"

import { useState, useEffect, useCallback } from "react"
import { CryptoSelector } from "@/components/crypto-selector"
import { TimeframeSelector } from "@/components/timeframe-selector"
import { CandlestickChart } from "@/components/candlestick-chart"
import { StrategyPanel } from "@/components/strategy-panel"
import { MetricsPanel } from "@/components/metrics-panel"
import { TradeHistory } from "@/components/trade-history"
import { PriceTicker } from "@/components/price-ticker"
import {
  generateCandles,
  runBacktest,
  calculateSMA,
  calculateRSI,
  type Candle,
  type BacktestResult,
  type Trade,
} from "@/lib/trading-data"
import { Activity } from "lucide-react"

const BASE_PRICES: Record<string, number> = {
  BTCUSDT: 95000,
  ETHUSDT: 3400,
  SOLUSDT: 180,
  BNBUSDT: 680,
  XRPUSDT: 2.2,
  ADAUSDT: 0.95,
}

export default function App() {
  const [selectedPair, setSelectedPair] = useState("BTCUSDT")
  const [timeframe, setTimeframe] = useState("1h")
  const [candles, setCandles] = useState<Candle[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null)
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null)
  const [isBacktesting, setIsBacktesting] = useState(false)
  const [isTrading, setIsTrading] = useState(false)
  const [paperBalance, setPaperBalance] = useState(10000)
  const [paperPosition, setPaperPosition] = useState<{ amount: number; entryPrice: number } | null>(null)
  const [paperTrades, setPaperTrades] = useState<Trade[]>([])

  // Generate initial candles
  useEffect(() => {
    const basePrice = BASE_PRICES[selectedPair] || 1000
    setCandles(generateCandles(basePrice, 100))
    setBacktestResult(null)
    setPaperPosition(null)
    setPaperTrades([])
    setPaperBalance(10000)
  }, [selectedPair])

  // Simulate live price updates
  useEffect(() => {
    if (!isTrading) return

    const interval = setInterval(() => {
      setCandles((prev) => {
        if (prev.length === 0) return prev

        const lastCandle = prev[prev.length - 1]
        const volatility = lastCandle.close * 0.005
        const change = (Math.random() - 0.5) * volatility
        const newClose = lastCandle.close + change

        const newCandle: Candle = {
          time: Date.now(),
          open: lastCandle.close,
          high: Math.max(lastCandle.close, newClose) + Math.random() * volatility * 0.3,
          low: Math.min(lastCandle.close, newClose) - Math.random() * volatility * 0.3,
          close: newClose,
          volume: Math.random() * 500000 + 250000,
        }

        return [...prev.slice(1), newCandle]
      })
    }, 2000)

    return () => clearInterval(interval)
  }, [isTrading])

  // Paper trading logic
  useEffect(() => {
    if (!isTrading || !selectedStrategy || candles.length < 22) return

    const prices = candles.map((c) => c.close)
    const currentPrice = prices[prices.length - 1]

    if (selectedStrategy === "ma_crossover") {
      const fastMA = calculateSMA(prices, 9)
      const slowMA = calculateSMA(prices, 21)
      const fast = fastMA[fastMA.length - 1]
      const slow = slowMA[slowMA.length - 1]
      const prevFast = fastMA[fastMA.length - 2]
      const prevSlow = slowMA[slowMA.length - 2]

      if (fast && slow && prevFast && prevSlow) {
        // Buy signal
        if (prevFast <= prevSlow && fast > slow && !paperPosition) {
          const amount = paperBalance / currentPrice
          setPaperPosition({ amount, entryPrice: currentPrice })
          setPaperBalance(0)
          setPaperTrades((prev) => [
            ...prev,
            {
              id: `paper-${Date.now()}`,
              type: "buy",
              price: currentPrice,
              amount,
              time: Date.now(),
              strategy: "MA Crossover",
            },
          ])
        }
        // Sell signal
        else if (prevFast >= prevSlow && fast < slow && paperPosition) {
          const pnl = ((currentPrice - paperPosition.entryPrice) / paperPosition.entryPrice) * 100
          const newBalance = paperPosition.amount * currentPrice
          setPaperBalance(newBalance)
          setPaperTrades((prev) => [
            ...prev,
            {
              id: `paper-${Date.now()}`,
              type: "sell",
              price: currentPrice,
              amount: paperPosition.amount,
              time: Date.now(),
              strategy: "MA Crossover",
              pnl,
            },
          ])
          setPaperPosition(null)
        }
      }
    } else if (selectedStrategy === "rsi") {
      const rsi = calculateRSI(prices, 14)
      const currentRSI = rsi[rsi.length - 1]

      if (currentRSI !== null) {
        // Buy signal (oversold)
        if (currentRSI < 30 && !paperPosition) {
          const amount = paperBalance / currentPrice
          setPaperPosition({ amount, entryPrice: currentPrice })
          setPaperBalance(0)
          setPaperTrades((prev) => [
            ...prev,
            {
              id: `paper-${Date.now()}`,
              type: "buy",
              price: currentPrice,
              amount,
              time: Date.now(),
              strategy: "RSI Strategy",
            },
          ])
        }
        // Sell signal (overbought)
        else if (currentRSI > 70 && paperPosition) {
          const pnl = ((currentPrice - paperPosition.entryPrice) / paperPosition.entryPrice) * 100
          const newBalance = paperPosition.amount * currentPrice
          setPaperBalance(newBalance)
          setPaperTrades((prev) => [
            ...prev,
            {
              id: `paper-${Date.now()}`,
              type: "sell",
              price: currentPrice,
              amount: paperPosition.amount,
              time: Date.now(),
              strategy: "RSI Strategy",
              pnl,
            },
          ])
          setPaperPosition(null)
        }
      }
    }
  }, [isTrading, selectedStrategy, candles, paperPosition, paperBalance])

  const handleBacktest = useCallback(() => {
    if (!selectedStrategy) return

    setIsBacktesting(true)
    setTimeout(() => {
      const result = runBacktest(candles, selectedStrategy)
      setBacktestResult(result)
      setIsBacktesting(false)
    }, 1000)
  }, [selectedStrategy, candles])

  const handleStartTrading = useCallback(() => {
    if (isTrading) {
      setIsTrading(false)
      // Close any open position
      if (paperPosition && candles.length > 0) {
        const currentPrice = candles[candles.length - 1].close
        const pnl = ((currentPrice - paperPosition.entryPrice) / paperPosition.entryPrice) * 100
        const newBalance = paperPosition.amount * currentPrice
        setPaperBalance(newBalance)
        setPaperTrades((prev) => [
          ...prev,
          {
            id: `paper-${Date.now()}`,
            type: "sell",
            price: currentPrice,
            amount: paperPosition.amount,
            time: Date.now(),
            strategy: selectedStrategy || "Manual",
            pnl,
          },
        ])
        setPaperPosition(null)
      }
    } else {
      setIsTrading(true)
      setPaperBalance(10000)
      setPaperPosition(null)
      setPaperTrades([])
    }
  }, [isTrading, paperPosition, candles, selectedStrategy])

  const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0
  const showMA = selectedStrategy === "ma_crossover"
  const showRSI = selectedStrategy === "rsi"

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="max-w-[1600px] mx-auto space-y-4">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
              <Activity className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">CryptoTrader</h1>
              <p className="text-xs text-muted-foreground">Paper Trading Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <CryptoSelector value={selectedPair} onChange={setSelectedPair} />
            <TimeframeSelector value={timeframe} onChange={setTimeframe} />
            {isTrading && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/20 text-primary text-sm">
                <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                Live Trading
              </div>
            )}
          </div>
        </header>

        {/* Price Ticker */}
        <div className="bg-card rounded-lg border border-border p-4">
          <PriceTicker symbol={selectedPair} candles={candles} />
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Chart */}
          <div className="lg:col-span-3 bg-card rounded-lg border border-border p-4">
            <div className="h-[400px] md:h-[500px]">
              <CandlestickChart candles={candles} showMA={showMA} showRSI={showRSI} />
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <StrategyPanel
              selectedStrategy={selectedStrategy}
              onSelect={setSelectedStrategy}
              onBacktest={handleBacktest}
              onStartTrading={handleStartTrading}
              isBacktesting={isBacktesting}
              isTrading={isTrading}
            />

            <MetricsPanel
              backtestResult={backtestResult}
              currentPrice={currentPrice}
              paperBalance={paperBalance}
              paperPosition={paperPosition}
            />
          </div>
        </div>

        {/* Trade History */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <TradeHistory trades={paperTrades} />
          {backtestResult && <TradeHistory trades={backtestResult.trades} />}
        </div>
      </div>
    </div>
  )
}
