"use client"

import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, type Time } from 'lightweight-charts'
import { getCandles, getWebSocketUrl, syncCandles, type Candle, type Trade } from '@/lib/api'
import { backendInterval, formatUtcDateTime, mergeCandles, toUnixSeconds, tradeMarkers } from '@/lib/chart-time'

interface ChartProps {
  symbol: string
  interval: string
  trades?: Trade[]
  onPriceUpdate?: (price: number, isUp: boolean) => void
}

function chartCandle(candle: Candle) {
  const price = (value: number | { value: number }) => Number(typeof value === 'object' ? value.value : value)
  const result = {
    time: toUnixSeconds(candle.open_time),
    open: price(candle.open), high: price(candle.high), low: price(candle.low),
    close: price(candle.close), volume: price(candle.volume),
  }
  if (!Object.values(result).every(Number.isFinite)) throw new Error('Invalid candle data')
  return result
}

type ChartCandle = ReturnType<typeof chartCandle>

export function TradingViewChart({ symbol, interval, trades = [], onPriceUpdate }: ChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const onPriceUpdateRef = useRef(onPriceUpdate)
  const tradesRef = useRef(trades)
  const updateMarkersRef = useRef<() => void>(() => {})
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { onPriceUpdateRef.current = onPriceUpdate }, [onPriceUpdate])
  useEffect(() => {
    tradesRef.current = trades
    updateMarkersRef.current()
  }, [trades])

  useEffect(() => {
    if (!containerRef.current) return
    let disposed = false
    let historyLoaded = false
    let candles: ChartCandle[] = []
    const pending = new Map<number, ChartCandle>()
    const frame = backendInterval(interval)
    setError(null)
    setLoading(true)

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0d1421' }, textColor: '#808a9d' },
      grid: { vertLines: { color: '#1e2738' }, horzLines: { color: '#1e2738' } },
      localization: { timeFormatter: (time: Time) => formatUtcDateTime(time as number) + ' UTC' },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2c3650' },
      rightPriceScale: { borderColor: '#2c3650' },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight || 500,
    })
    const series = chart.addCandlestickSeries({
      upColor: '#16c784', downColor: '#ea3943', borderVisible: false,
      wickUpColor: '#16c784', wickDownColor: '#ea3943',
    })
    const volume = chart.addHistogramSeries({ priceFormat: { type: 'volume' }, priceScaleId: 'volume' })
    chart.priceScale('right').applyOptions({ scaleMargins: { top: 0.08, bottom: 0.25 } })
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.75, bottom: 0.02 } })

    const volumePoint = (c: ChartCandle) => ({
      time: c.time, value: c.volume, color: c.close >= c.open ? '#16c78480' : '#ea394380',
    })
    const updateMarkers = () => series.setMarkers(tradeMarkers(
      candles, tradesRef.current.filter(t => t.symbol === symbol), frame,
    ))
    updateMarkersRef.current = updateMarkers
    const publishPrice = (c: ChartCandle) => onPriceUpdateRef.current?.(c.close, c.close >= c.open)

    const loadHistory = async () => {
      try {
        await syncCandles([symbol], [frame])
      } catch (err) {
        if (disposed) return
        setError('Sync failed; showing stored candles. Check the API connection.')
        console.error('Candle sync failed:', err)
      }
      if (disposed) return
      try {
        const result = await getCandles(symbol, frame)
        if (disposed) return
        candles = mergeCandles(result.candles.map(chartCandle), [...pending.values()])
      } catch (err) {
        if (disposed) return
        candles = mergeCandles([...pending.values()])
        setError('Historical candles could not be loaded. Check the API connection.')
        console.error('Candle history failed:', err)
      }
      pending.clear()
      historyLoaded = true
      series.setData(candles)
      volume.setData(candles.map(volumePoint))
      updateMarkers()
      if (candles.length) {
        publishPrice(candles[candles.length - 1])
        chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, candles.length - 100), to: candles.length })
      }
      setLoading(false)
    }

    const socket = new WebSocket(getWebSocketUrl(symbol, frame))
    socket.onmessage = event => {
      if (disposed) return
      try {
        const candle = chartCandle(JSON.parse(event.data).candle)
        if (!historyLoaded) {
          pending.set(candle.time, candle)
          return
        }
        const last = candles[candles.length - 1]
        // An old update must never move the current bar or price backwards.
        if (last && candle.time < last.time) return
        if (last?.time === candle.time) candles[candles.length - 1] = candle
        else candles.push(candle)
        series.update(candle)
        volume.update(volumePoint(candle))
        updateMarkers()
        publishPrice(candle)
      } catch (err) {
        console.error('Invalid live candle:', err)
      }
    }
    socket.onclose = () => {
      if (!disposed) setError('Live stream disconnected. Reload to reconnect.')
    }
    void loadHistory()

    const observer = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth })
    })
    observer.observe(containerRef.current)
    return () => {
      disposed = true
      socket.close()
      observer.disconnect()
      updateMarkersRef.current = () => {}
      chart.remove()
    }
  }, [symbol, interval])

  return (
    <div className="w-full h-full relative">
      <div className="absolute top-2 left-3 z-10 text-xs text-muted-foreground">UTC</div>
      {loading && <div role="status" className="absolute top-2 left-14 z-10 text-xs text-muted-foreground">Loading candles...</div>}
      {error && <div role="status" className="absolute top-8 left-3 right-3 z-10 text-xs text-amber-400">{error}</div>}
      <div ref={containerRef} className="w-full h-full" />
    </div>
  )
}
