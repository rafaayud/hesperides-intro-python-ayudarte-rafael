"use client"

import { useEffect, useState, useRef } from "react"
import { TrendingUp, TrendingDown } from "lucide-react"
import { CRYPTO_PAIRS } from "@/lib/trading-data"

interface TickerItem {
  symbol: string
  price: number
  change24h: number
  changePercent24h: number
  lastDailyClose: number // Precio de cierre de la última vela diaria cerrada
}

export function CryptoTicker() {
  const [tickerData, setTickerData] = useState<TickerItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const wsConnectionsRef = useRef<Map<string, WebSocket>>(new Map())
  // Cache de los cierres diarios: symbol -> lastDailyClose
  const dailyCloseCacheRef = useRef<Map<string, number>>(new Map())

  useEffect(() => {
    const symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
    
    // 1. Sincronizar velas diarias en la BD al inicio
    const syncDailyCandles = async () => {
      try {
        console.log("[Ticker] Syncing daily candles for symbols:", symbols)
        const response = await fetch(`http://localhost:8000/candles/sync`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbols, intervals: ["D1"] })
        })
        
        if (!response.ok) {
          throw new Error(`Sync failed: ${response.status}`)
        }
        
        const result = await response.json()
        console.log("[Ticker] Sync completed:", result)
        return true
      } catch (error) {
        console.error("[Ticker] Error syncing daily candles:", error)
        return false
      }
    }

    // 2. Obtener las últimas velas diarias y guardarlas en cache
    const fetchAndCacheDailyCloses = async () => {
      try {
        console.log("[Ticker] Fetching daily closes from database...")
        const promises = symbols.map(async (symbol) => {
          try {
            // IMPORTANTE: get_candles devuelve velas ordenadas ASC (más antigua primero)
            // Para obtener la última vela, pedimos varias y tomamos la última del array
            // Pedimos limit=10 para asegurarnos de tener la más reciente
            const response = await fetch(`http://localhost:8000/candles/${symbol}/D1?limit=10000`)
            if (!response.ok) {
              console.error(`[Ticker] Failed to fetch ${symbol}: ${response.status}`)
              return null
            }
            
            const result = await response.json()
            if (!result.candles || result.candles.length === 0) {
              console.warn(`[Ticker] No candles found for ${symbol}`)
              return null
            }

            // Las velas vienen ordenadas ASC (más antigua primero), 
            // así que la ÚLTIMA del array es la más reciente
            const candles = result.candles
            const lastCandle = candles[candles.length - 1]
            const lastDailyClose = parseFloat(lastCandle.close)
            
            console.log(`[Ticker] ${symbol} - Found ${candles.length} candles, using last (most recent) close: ${lastDailyClose}`)

            // Guardar en cache
            dailyCloseCacheRef.current.set(symbol, lastDailyClose)
            console.log(`[Ticker] Cached daily close for ${symbol}: ${lastDailyClose}`)

            return {
              symbol,
              lastDailyClose,
              price: lastDailyClose, // Precio inicial hasta que llegue el WS
              change24h: 0,
              changePercent24h: 0
            }
          } catch (error) {
            console.error(`[Ticker] Error fetching ${symbol}:`, error)
            return null
          }
        })

        const results = await Promise.all(promises)
        const validResults = results.filter((r): r is TickerItem => r !== null)
        
        if (validResults.length === 0) {
          console.error("[Ticker] No valid ticker data found")
          setIsLoading(false)
          return
        }

        setTickerData(validResults)
        setIsLoading(false)

        // 3. Conectar WebSockets para obtener precios en tiempo real
        console.log("[Ticker] Connecting WebSockets for real-time prices...")
        validResults.forEach((item) => {
          connectWebSocket(item.symbol)
        })
      } catch (error) {
        console.error("[Ticker] Error fetching ticker data:", error)
        setIsLoading(false)
      }
    }

    // 4. Conectar WebSocket para un símbolo específico
    const connectWebSocket = (symbol: string) => {
      // Obtener el cierre diario del cache
      const lastDailyClose = dailyCloseCacheRef.current.get(symbol)
      
      if (!lastDailyClose) {
        console.error(`[Ticker] No daily close cached for ${symbol}, skipping WebSocket`)
        return
      }

      // Usamos intervalo M1 para obtener el precio actual más frecuentemente
      const ws = new WebSocket(`ws://localhost:8000/candles_live/${symbol}/M1`)
      
      ws.onopen = () => {
        console.log(`[Ticker] WebSocket connected for ${symbol}`)
      }
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        const currentPrice = parseFloat(data.candle.close)
        
        // Obtener el cierre diario del cache (por si cambió)
        const cachedDailyClose = dailyCloseCacheRef.current.get(symbol) || lastDailyClose
        
        // Calcular cambio comparando precio actual del WS con el cierre diario del cache
        const change24h = currentPrice - cachedDailyClose
        const changePercent24h = cachedDailyClose > 0 ? (change24h / cachedDailyClose) * 100 : 0

        // Actualizar el estado del ticker
        setTickerData((prev) => 
          prev.map((item) => 
            item.symbol === symbol
              ? {
                  ...item,
                  price: currentPrice,
                  change24h,
                  changePercent24h
                }
              : item
          )
        )
      }

      ws.onerror = (err) => {
        console.error(`[Ticker] WebSocket error for ${symbol}:`, err)
      }

      ws.onclose = () => {
        console.log(`[Ticker] WebSocket closed for ${symbol}`)
      }

      wsConnectionsRef.current.set(symbol, ws)
    }

    // Inicializar: primero sincronizar, luego obtener y cachear, luego conectar WS
    const initialize = async () => {
      const syncSuccess = await syncDailyCandles()
      if (syncSuccess) {
        await fetchAndCacheDailyCloses()
      } else {
        // Si falla la sync, intentar obtener de todas formas (puede haber datos antiguos)
        await fetchAndCacheDailyCloses()
      }
    }

    initialize()

    // Cleanup: cerrar todas las conexiones WebSocket
    return () => {
      wsConnectionsRef.current.forEach((ws) => {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close()
        }
      })
      wsConnectionsRef.current.clear()
    }
  }, [])

  if (isLoading) {
    return (
      <div className="w-full bg-card border-b border-border py-2 px-4">
        <div className="flex items-center gap-6 animate-pulse">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-12 w-32 bg-muted rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="w-full bg-card border-b border-border py-2 overflow-hidden relative">
      <div className="flex items-center gap-6 animate-scroll whitespace-nowrap">
        {tickerData.map((item) => {
          const isPositive = item.changePercent24h >= 0
          const pairInfo = CRYPTO_PAIRS.find(p => p.symbol === item.symbol)
          
          return (
            <div
              key={item.symbol}
              className="flex items-center gap-3 min-w-[180px] px-3 py-1 rounded hover:bg-muted/50 transition-colors"
            >
              <div className="flex flex-col">
                <div className="text-xs text-muted-foreground font-medium">
                  {pairInfo?.name || item.symbol.replace('USDT', '')}
                </div>
                <div className="text-sm font-mono font-semibold">
                  ${item.price.toFixed(2)}
                </div>
              </div>
              <div className={`flex items-center gap-1 ${isPositive ? "text-profit" : "text-loss"}`}>
                {isPositive ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                <span className="text-xs font-mono">
                  {isPositive ? "+" : ""}
                  {item.changePercent24h.toFixed(2)}%
                </span>
              </div>
            </div>
          )
        })}
        {/* Duplicar para efecto de scroll continuo */}
        {tickerData.map((item) => {
          const isPositive = item.changePercent24h >= 0
          const pairInfo = CRYPTO_PAIRS.find(p => p.symbol === item.symbol)
          
          return (
            <div
              key={`${item.symbol}-dup`}
              className="flex items-center gap-3 min-w-[180px] px-3 py-1 rounded hover:bg-muted/50 transition-colors"
            >
              <div className="flex flex-col">
                <div className="text-xs text-muted-foreground font-medium">
                  {pairInfo?.name || item.symbol.replace('USDT', '')}
                </div>
                <div className="text-sm font-mono font-semibold">
                  ${item.price.toFixed(2)}
                </div>
              </div>
              <div className={`flex items-center gap-1 ${isPositive ? "text-profit" : "text-loss"}`}>
                {isPositive ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                <span className="text-xs font-mono">
                  {isPositive ? "+" : ""}
                  {item.changePercent24h.toFixed(2)}%
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

