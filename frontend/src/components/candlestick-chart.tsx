"use client"

import { useEffect, useRef } from "react"
import type { Candle } from "@/lib/trading-data"
import { calculateSMA, calculateRSI } from "@/lib/trading-data"

interface CandlestickChartProps {
  candles: Candle[]
  showMA?: boolean
  showRSI?: boolean
}

export function CandlestickChart({ candles, showMA = false, showRSI = false }: CandlestickChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rsiCanvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || candles.length === 0) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = rect.height
    const padding = { top: 20, right: 60, bottom: 30, left: 10 }
    const chartWidth = width - padding.left - padding.right
    const chartHeight = height - padding.top - padding.bottom

    // Clear canvas
    ctx.fillStyle = "#1a1a2e"
    ctx.fillRect(0, 0, width, height)

    // Calculate price range
    const prices = candles.flatMap((c) => [c.high, c.low])
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const priceRange = maxPrice - minPrice
    const pricePadding = priceRange * 0.1

    const scaleY = (price: number) =>
      padding.top + chartHeight - ((price - minPrice + pricePadding) / (priceRange + 2 * pricePadding)) * chartHeight

    const candleWidth = Math.max(2, (chartWidth / candles.length) * 0.8)
    const gap = chartWidth / candles.length

    // Draw grid lines
    ctx.strokeStyle = "#2a2a4e"
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartHeight / 5) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(width - padding.right, y)
      ctx.stroke()

      // Price labels
      const price = maxPrice + pricePadding - ((priceRange + 2 * pricePadding) / 5) * i
      ctx.fillStyle = "#6b7280"
      ctx.font = "11px monospace"
      ctx.textAlign = "left"
      ctx.fillText(price.toFixed(2), width - padding.right + 5, y + 4)
    }

    // Draw candles
    candles.forEach((candle, i) => {
      const x = padding.left + i * gap + gap / 2
      const isGreen = candle.close >= candle.open

      // Wick
      ctx.strokeStyle = isGreen ? "#22c55e" : "#ef4444"
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, scaleY(candle.high))
      ctx.lineTo(x, scaleY(candle.low))
      ctx.stroke()

      // Body
      ctx.fillStyle = isGreen ? "#22c55e" : "#ef4444"
      const bodyTop = scaleY(Math.max(candle.open, candle.close))
      const bodyBottom = scaleY(Math.min(candle.open, candle.close))
      const bodyHeight = Math.max(1, bodyBottom - bodyTop)
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight)
    })

    // Draw Moving Averages if enabled
    if (showMA) {
      const closePrices = candles.map((c) => c.close)
      const fastMA = calculateSMA(closePrices, 9)
      const slowMA = calculateSMA(closePrices, 21)

      // Fast MA (9)
      ctx.strokeStyle = "#3b82f6"
      ctx.lineWidth = 1.5
      ctx.beginPath()
      fastMA.forEach((val, i) => {
        if (val !== null) {
          const x = padding.left + i * gap + gap / 2
          const y = scaleY(val)
          if (i === 0 || fastMA[i - 1] === null) {
            ctx.moveTo(x, y)
          } else {
            ctx.lineTo(x, y)
          }
        }
      })
      ctx.stroke()

      // Slow MA (21)
      ctx.strokeStyle = "#f59e0b"
      ctx.lineWidth = 1.5
      ctx.beginPath()
      slowMA.forEach((val, i) => {
        if (val !== null) {
          const x = padding.left + i * gap + gap / 2
          const y = scaleY(val)
          if (i === 0 || slowMA[i - 1] === null) {
            ctx.moveTo(x, y)
          } else {
            ctx.lineTo(x, y)
          }
        }
      })
      ctx.stroke()

      // Legend
      ctx.fillStyle = "#3b82f6"
      ctx.fillRect(padding.left + 10, padding.top + 5, 12, 3)
      ctx.fillStyle = "#9ca3af"
      ctx.font = "10px sans-serif"
      ctx.fillText("MA9", padding.left + 26, padding.top + 10)

      ctx.fillStyle = "#f59e0b"
      ctx.fillRect(padding.left + 60, padding.top + 5, 12, 3)
      ctx.fillText("MA21", padding.left + 76, padding.top + 10)
    }
  }, [candles, showMA])

  // Draw RSI chart
  useEffect(() => {
    if (!showRSI) return

    const canvas = rsiCanvasRef.current
    if (!canvas || candles.length === 0) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = rect.height
    const padding = { top: 10, right: 60, bottom: 20, left: 10 }
    const chartWidth = width - padding.left - padding.right
    const chartHeight = height - padding.top - padding.bottom

    // Clear canvas
    ctx.fillStyle = "#1a1a2e"
    ctx.fillRect(0, 0, width, height)

    const closePrices = candles.map((c) => c.close)
    const rsiValues = calculateRSI(closePrices, 14)
    const gap = chartWidth / candles.length

    // Draw overbought/oversold zones
    ctx.fillStyle = "rgba(239, 68, 68, 0.1)"
    ctx.fillRect(padding.left, padding.top, chartWidth, (chartHeight / 100) * 30)
    ctx.fillStyle = "rgba(34, 197, 94, 0.1)"
    ctx.fillRect(padding.left, padding.top + (chartHeight / 100) * 70, chartWidth, (chartHeight / 100) * 30)

    // Draw threshold lines
    ctx.strokeStyle = "#ef4444"
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])
    ctx.beginPath()
    ctx.moveTo(padding.left, padding.top + (chartHeight / 100) * 30)
    ctx.lineTo(width - padding.right, padding.top + (chartHeight / 100) * 30)
    ctx.stroke()

    ctx.strokeStyle = "#22c55e"
    ctx.beginPath()
    ctx.moveTo(padding.left, padding.top + (chartHeight / 100) * 70)
    ctx.lineTo(width - padding.right, padding.top + (chartHeight / 100) * 70)
    ctx.stroke()
    ctx.setLineDash([])

    // Draw RSI line
    ctx.strokeStyle = "#a855f7"
    ctx.lineWidth = 1.5
    ctx.beginPath()
    rsiValues.forEach((val, i) => {
      if (val !== null) {
        const x = padding.left + i * gap + gap / 2
        const y = padding.top + chartHeight - (val / 100) * chartHeight
        if (i === 0 || rsiValues[i - 1] === null) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
    })
    ctx.stroke()

    // Labels
    ctx.fillStyle = "#6b7280"
    ctx.font = "10px monospace"
    ctx.textAlign = "left"
    ctx.fillText("70", width - padding.right + 5, padding.top + (chartHeight / 100) * 30 + 4)
    ctx.fillText("30", width - padding.right + 5, padding.top + (chartHeight / 100) * 70 + 4)
    ctx.fillText("RSI", padding.left + 5, padding.top + 15)
  }, [candles, showRSI])

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className={showRSI ? "h-[70%]" : "h-full"}>
        <canvas ref={canvasRef} className="w-full h-full" />
      </div>
      {showRSI && (
        <div className="h-[30%] border-t border-border">
          <canvas ref={rsiCanvasRef} className="w-full h-full" />
        </div>
      )}
    </div>
  )
}
