"use client"

import { useEffect, useRef, useState } from "react"
import { 
  createChart, 
  ColorType, 
  ISeriesApi, 
  UTCTimestamp,
  CandlestickSeries,
  HistogramSeries,
  IChartApi,
  MouseEventParams
} from "lightweight-charts"

// Interface for trade markers
interface TradeMarker {
  time: number
  position: 'aboveBar' | 'belowBar'
  color: string
  shape: 'arrowUp' | 'arrowDown'
  text: string
  size?: number
  id?: string
}

// Extended trade data for tooltips
interface TradeData {
  time: number
  type: 'entry' | 'exit'
  price: number
  quantity?: number
  pnl?: number
  pnlPercentage?: number
  timestamp: string
}

// 1. Definimos la interfaz para aceptar la función 'onPriceUpdate'
interface ChartProps {
  symbol: string
  interval: string
  portfolioId?: string
  traderId?: string
  onPriceUpdate?: (price: number, isUp: boolean) => void
}

// Helper para convertir formato de intervalo del frontend al backend
function convertIntervalToBackendFormat(interval: string): string {
  const intervalMap: Record<string, string> = {
    "1m": "M1", "5m": "M5", "15m": "M15",
    "1h": "H1", "4h": "H4",
    "1d": "D1", "1w": "W1", "1M": "MO1"
  };
  // Si ya está en formato backend, devolverlo tal cual
  const backendFormats = ["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MO1"];
  if (backendFormats.includes(interval.toUpperCase())) {
    return interval.toUpperCase();
  }
  return intervalMap[interval.toLowerCase()] || interval.toUpperCase();
}

// Helper para convertir UTC timestamp a timestamp local (para que las etiquetas muestren hora local)
function utcToLocal(utcTimestamp: number): number {
  // getTimezoneOffset() devuelve minutos, con signo invertido
  // En España UTC+1: getTimezoneOffset() = -60
  const offsetSeconds = new Date().getTimezoneOffset() * 60;
  return utcTimestamp - offsetSeconds;
}

export function TradingViewChart({ symbol, interval, portfolioId, traderId, onPriceUpdate }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const markersRef = useRef<TradeMarker[]>([])
  const tradeDataRef = useRef<Map<number, TradeData[]>>(new Map())
  
  // Tooltip state
  const [tooltip, setTooltip] = useState<{
    visible: boolean
    x: number
    y: number
    trades: TradeData[]
  }>({ visible: false, x: 0, y: 0, trades: [] })

  // EFECTO 1: Inicialización del Gráfico y Carga de Histórico
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: { 
        background: { type: ColorType.Solid, color: "#0d1421" }, 
        textColor: "#808a9d" 
      },
      grid: { 
        vertLines: { color: "#1e2738" }, 
        horzLines: { color: "#1e2738" } 
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: "#2c3650",
      },
      rightPriceScale: {
        borderColor: "#2c3650",
      },
      crosshair: {
        vertLine: {
          color: '#3861fb',
          width: 1,
          style: 2,
          labelBackgroundColor: '#3861fb',
        },
        horzLine: {
          color: '#3861fb',
          width: 1,
          style: 2,
          labelBackgroundColor: '#3861fb',
        },
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight || 500,
    })

    chartRef.current = chart

    // Escala principal (velas): dejamos espacio inferior para el volumen
    chart.priceScale('right').applyOptions({
      scaleMargins: {
        top: 0.05,
        bottom: 0.25,
      },
    })

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#16c784", 
      downColor: "#ea3943", 
      borderVisible: false,
      wickUpColor: "#16c784", 
      wickDownColor: "#ea3943",
    })
    
    candleSeriesRef.current = candlestickSeries

    // Añadir serie de volumen
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#26a69a",
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
      scaleMargins: {
        top: 0.75,
        bottom: 0.02,
      },
    })
    
    volumeSeriesRef.current = volumeSeries

    // Configurar escala de volumen
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.75,
        bottom: 0.02,
      },
    })

    const fetchHistoricalData = async () => {
      try {
        // Convertir formato de intervalo al formato del backend
        const backendInterval = convertIntervalToBackendFormat(interval);
        
        console.log(`[Chart] Syncing ${symbol}/${backendInterval}...`);
        
        // Sincronizar Binance -> Postgres
        const syncResponse = await fetch(`http://localhost:8000/candles/sync`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbols: [symbol], intervals: [backendInterval] })
        });

        if (!syncResponse.ok) {
          const errorText = await syncResponse.text();
          throw new Error(`Sync failed: ${syncResponse.status} - ${errorText}`);
        }

        const syncResult = await syncResponse.json();
        console.log(`[Chart] Sync completed:`, syncResult);
    
        // Leer Postgres -> Frontend
        console.log(`[Chart] Fetching historical data for ${symbol}/${backendInterval}...`);
        const response = await fetch(`http://localhost:8000/candles/${symbol}/${backendInterval}?limit=10000`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch candles: ${response.status}`);
        }
        
        const result = await response.json();
        console.log(`[Chart] Received ${result.candles?.length || 0} candles`);
        
        // Fetch trade markers if portfolioId and traderId are provided
        let tradeMarkers: TradeMarker[] = [];
        if (portfolioId && traderId) {
          try {
            console.log(`[Chart] Fetching trade markers for ${portfolioId}/${traderId}...`);
            const tradesResponse = await fetch(
              `http://localhost:8000/api/portfolio/trades/${portfolioId}?trader_id=${traderId}&limit=500`
            );
            if (tradesResponse.ok) {
              const tradesResult = await tradesResponse.json();
              const trades = tradesResult.trades || [];
              console.log(`[Chart] Received ${trades.length} trades from API:`, trades);
              
              // Convert trades to markers and store trade data for tooltips
              const tradeDataMap = new Map<number, TradeData[]>();
              
              tradeMarkers = trades.flatMap((trade: any, idx: number) => {
                const markers: TradeMarker[] = [];
                
                // Entry marker (BUY)
                if (trade.entry_time) {
                  // Convert to local timestamp (same as candles)
                  const entryTimeUtc = Math.floor(new Date(trade.entry_time).getTime() / 1000);
                  const entryTime = utcToLocal(entryTimeUtc);
                  console.log(`[Chart] Trade ${idx}: Entry at ${trade.entry_time} -> ${entryTime} (local)`);
                  markers.push({
                    time: entryTime,
                    position: 'belowBar',
                    color: '#16c784',
                    shape: 'arrowUp',
                    text: 'BUY',
                    size: 2,
                    id: `trade-${idx}-entry`
                  });
                  
                  // Store trade data for tooltip
                  const entryData: TradeData = {
                    time: entryTime,
                    type: 'entry',
                    price: trade.entry_price || 0,
                    quantity: trade.quantity,
                    timestamp: trade.entry_time
                  };
                  if (!tradeDataMap.has(entryTime)) {
                    tradeDataMap.set(entryTime, []);
                  }
                  tradeDataMap.get(entryTime)!.push(entryData);
                }
                
                // Exit marker (SELL)
                if (trade.exit_time) {
                  const exitTimeUtc = Math.floor(new Date(trade.exit_time).getTime() / 1000);
                  const exitTime = utcToLocal(exitTimeUtc);
                  const pnl = trade.pnl || 0;
                  console.log(`[Chart] Trade ${idx}: Exit at ${trade.exit_time} -> ${exitTime} (local), PnL: ${pnl}`);
                  markers.push({
                    time: exitTime,
                    position: 'aboveBar',
                    color: '#ea3943',
                    shape: 'arrowDown',
                    text: 'SELL',
                    size: 2,
                    id: `trade-${idx}-exit`
                  });
                  
                  // Store trade data for tooltip
                  const exitData: TradeData = {
                    time: exitTime,
                    type: 'exit',
                    price: trade.exit_price || 0,
                    quantity: trade.quantity,
                    pnl: pnl,
                    pnlPercentage: trade.pnl_percentage,
                    timestamp: trade.exit_time
                  };
                  if (!tradeDataMap.has(exitTime)) {
                    tradeDataMap.set(exitTime, []);
                  }
                  tradeDataMap.get(exitTime)!.push(exitData);
                }
                
                return markers;
              });
              
              console.log(`[Chart] Created ${tradeMarkers.length} trade markers`);
              markersRef.current = tradeMarkers;
              tradeDataRef.current = tradeDataMap;
            } else {
              console.log(`[Chart] Trades response not ok: ${tradesResponse.status}`);
            }
          } catch (error) {
            console.error("[Chart] Error fetching trade markers:", error);
          }
        }

        // Validar que tenemos datos
        if (!result.candles || !Array.isArray(result.candles)) {
          console.error("Invalid response format:", result);
          return;
        }

        // Formatear datos y validar que el tiempo sea válido
        const formattedData = result.candles
          .map((c: any) => {
            // Intentar obtener el timestamp de diferentes campos posibles
            let timestamp: number | null = null;
            
            // Opción 1: timestamp.timestamp (si viene como objeto Timestamp)
            if (c.timestamp?.timestamp) {
              timestamp = new Date(c.timestamp.timestamp).getTime() / 1000;
            }
            // Opción 2: timestamp (si viene como string ISO)
            else if (c.timestamp) {
              timestamp = new Date(c.timestamp).getTime() / 1000;
            }
            // Opción 3: open_time (formato ISO string)
            else if (c.open_time) {
              timestamp = new Date(c.open_time).getTime() / 1000;
            }
            // Opción 4: time (formato ISO string)
            else if (c.time) {
              timestamp = new Date(c.time).getTime() / 1000;
            }

            // Validar que el timestamp sea válido
            if (!timestamp || isNaN(timestamp)) {
              console.warn("Invalid timestamp in candle:", c);
              return null;
            }

            // Validar que los precios sean números válidos
            const open = typeof c.open === 'object' && c.open?.value ? parseFloat(c.open.value) : parseFloat(c.open);
            const high = typeof c.high === 'object' && c.high?.value ? parseFloat(c.high.value) : parseFloat(c.high);
            const low = typeof c.low === 'object' && c.low?.value ? parseFloat(c.low.value) : parseFloat(c.low);
            const close = typeof c.close === 'object' && c.close?.value ? parseFloat(c.close.value) : parseFloat(c.close);

            if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) {
              console.warn("Invalid price in candle:", c);
              return null;
            }

            // Obtener volumen
            const volume = typeof c.volume === 'object' && c.volume?.value ? parseFloat(c.volume.value) : parseFloat(c.volume || 0);

            return {
              time: utcToLocal(timestamp) as UTCTimestamp,
              open,
              high,
              low,
              close,
              volume: isNaN(volume) ? 0 : volume,
            };
          })
          .filter((c: any) => c !== null) // Filtrar candles inválidos
          .sort((a: any, b: any) => a.time - b.time); // Ordenar por tiempo ascendente

        if (formattedData.length === 0) {
          console.error("No valid candles found after formatting");
          return;
        }
    
        candlestickSeries.setData(formattedData.map(({ volume, ...rest }) => rest));

        // Preparar datos de volumen para la serie de histograma
        const volumeData = formattedData.map((candle) => ({
          time: candle.time,
          value: candle.volume,
          color: candle.close >= candle.open ? '#16c78480' : '#ea394380',
        }));

        if (volumeSeriesRef.current) {
          volumeSeriesRef.current.setData(volumeData);
        }

        // Apply trade markers if available
        if (tradeMarkers.length > 0 && candleSeriesRef.current) {
          // Get all candle times as a set for quick lookup
          const candleTimes = new Set(formattedData.map(c => c.time));
          const candleTimesArray = formattedData.map(c => c.time).sort((a, b) => a - b);
          
          // Log time ranges for debugging
          const candleStart = new Date(candleTimesArray[0] * 1000).toISOString();
          const candleEnd = new Date(candleTimesArray[candleTimesArray.length - 1] * 1000).toISOString();
          console.log(`[Chart] Candle range: ${candleStart} to ${candleEnd}`);
          
          const markerTimes = tradeMarkers.map(m => m.time);
          const markerStart = new Date(Math.min(...markerTimes) * 1000).toISOString();
          const markerEnd = new Date(Math.max(...markerTimes) * 1000).toISOString();
          console.log(`[Chart] Marker range: ${markerStart} to ${markerEnd}`);
          
          // Function to find closest candle time
          const findClosestCandleTime = (targetTime: number): number | null => {
            // Exact match
            if (candleTimes.has(targetTime)) return targetTime;
            
            // Find closest time in the candle data using binary search approach
            let closest = candleTimesArray[0];
            let minDiff = Math.abs(targetTime - closest);
            
            for (const time of candleTimesArray) {
              const diff = Math.abs(targetTime - time);
              if (diff < minDiff) {
                minDiff = diff;
                closest = time;
              }
              // Early exit if we found exact or passed the target
              if (diff === 0 || (time > targetTime && minDiff < 120)) break;
            }
            
            console.log(`[Chart] Finding closest candle for ${new Date(targetTime * 1000).toLocaleString()}: found ${new Date(closest * 1000).toLocaleString()} (diff: ${minDiff}s = ${(minDiff/60).toFixed(1)}min)`);
            
            // Accept if within 5 minutes (for 1m candles) or 2 hours (for larger intervals)
            return minDiff <= 7200 ? closest : null;
          };
          
          // Map markers to valid candle times and update tradeDataRef with adjusted times
          const newTradeDataMap = new Map<number, TradeData[]>();
          
          const validMarkers = tradeMarkers
            .map(m => {
              const adjustedTime = findClosestCandleTime(m.time);
              if (adjustedTime === null) {
                console.log(`[Chart] Marker at ${new Date(m.time * 1000).toISOString()} has no matching candle, skipping`);
                return null;
              }
              
              // Copy trade data to adjusted time for tooltip
              const originalData = tradeDataRef.current.get(m.time);
              if (originalData) {
                if (!newTradeDataMap.has(adjustedTime)) {
                  newTradeDataMap.set(adjustedTime, []);
                }
                newTradeDataMap.get(adjustedTime)!.push(...originalData);
              }
              
              return {
                time: adjustedTime as UTCTimestamp,
                position: m.position,
                color: m.color,
                shape: m.shape,
                text: m.text,
                size: m.size || 2
              };
            })
            .filter(m => m !== null)
            .sort((a, b) => a!.time - b!.time);
          
          // Update trade data ref with adjusted times
          if (newTradeDataMap.size > 0) {
            tradeDataRef.current = newTradeDataMap;
          }
          
          if (validMarkers.length > 0) {
            candleSeriesRef.current.setMarkers(validMarkers as any);
            console.log(`[Chart] ✅ Applied ${validMarkers.length} markers to chart:`, validMarkers);
          } else {
            console.log(`[Chart] ⚠️ No valid markers to apply (all ${tradeMarkers.length} outside candle range)`);
            console.log(`[Chart] Candle time range: ${candleTimesArray[0]} - ${candleTimesArray[candleTimesArray.length - 1]}`);
            console.log(`[Chart] Trade marker times:`, tradeMarkers.map(m => m.time));
          }
        }

        // Si hay datos históricos, actualizamos el precio inicial en la App
        if (formattedData.length > 0 && onPriceUpdate) {
          const lastCandle = formattedData[formattedData.length - 1];
          const isUp = lastCandle.close >= lastCandle.open;
          onPriceUpdate(lastCandle.close, isUp);
        }

      } catch (error) {
        console.error("Error cargando histórico:", error);
      }
    };

    fetchHistoricalData()

    // Subscribe to crosshair move for trade tooltips
    const handleCrosshairMove = (param: MouseEventParams) => {
      if (!param.time || !param.point || !chartContainerRef.current) {
        setTooltip(prev => ({ ...prev, visible: false }));
        return;
      }

      const time = param.time as number;
      const trades = tradeDataRef.current.get(time);

      if (trades && trades.length > 0) {
        const containerRect = chartContainerRef.current.getBoundingClientRect();
        setTooltip({
          visible: true,
          x: param.point.x,
          y: param.point.y,
          trades
        });
      } else {
        setTooltip(prev => ({ ...prev, visible: false }));
      }
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ 
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight || 500
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    }
  }, [symbol, interval, portfolioId, traderId]) // Incluimos portfolioId y traderId para recargar markers cuando cambien

  // EFECTO 2: WebSocket para tiempo real
  useEffect(() => {
    const backendInterval = convertIntervalToBackendFormat(interval);
    const socket = new WebSocket(`ws://localhost:8000/live_candles/${symbol}/${backendInterval}`);
  
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const c = data.candle;
  
      // Convertir a hora local para consistencia con las velas históricas
      const utcTime = Math.floor(new Date(c.open_time).getTime() / 1000);
      const localTime = utcToLocal(utcTime);
      
      const liveCandle = {
        time: localTime as UTCTimestamp, 
        open: c.open, 
        high: c.high, 
        low: c.low, 
        close: c.close,
      };
  
      if (candleSeriesRef.current) {
        candleSeriesRef.current.update(liveCandle);
      }

      // Actualizar volumen en tiempo real
      if (volumeSeriesRef.current && c.volume !== undefined) {
        const volumeUpdate = {
          time: localTime as UTCTimestamp,
          value: c.volume,
          color: c.close >= c.open ? '#16c78480' : '#ea394380',
        };
        volumeSeriesRef.current.update(volumeUpdate);
      }

      // 2. AQUÍ ES DONDE AVISAMOS A LA APP PRINCIPAL DEL NUEVO PRECIO
      if (onPriceUpdate) {
        const isUp = c.close >= c.open;
        onPriceUpdate(c.close, isUp);
      }
    };
  
    socket.onerror = (err) => console.error("Error WebSocket:", err);
  
    return () => socket.close();
  }, [symbol, interval, onPriceUpdate]); // Aquí sí incluimos onPriceUpdate

  // Format date for tooltip
  const formatTooltipDate = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="w-full h-full relative">
      <div ref={chartContainerRef} className="w-full h-full" />
      
      {/* Trade Tooltip */}
      {tooltip.visible && tooltip.trades.length > 0 && (
        <div 
          className="absolute z-50 pointer-events-none"
          style={{
            left: tooltip.x + 15,
            top: tooltip.y - 10,
            transform: tooltip.x > (chartContainerRef.current?.clientWidth || 0) / 2 
              ? 'translateX(-110%)' 
              : 'translateX(0)'
          }}
        >
          <div className="bg-[#1a1f2e] border border-[#2c3650] rounded-lg shadow-xl p-3 min-w-[180px]">
            {tooltip.trades.map((trade, idx) => (
              <div key={idx} className={idx > 0 ? 'mt-2 pt-2 border-t border-[#2c3650]' : ''}>
                {/* Trade Type Badge */}
                <div className="flex items-center justify-between mb-2">
                  <span 
                    className={`text-xs font-bold px-2 py-0.5 rounded ${
                      trade.type === 'entry' 
                        ? 'bg-[#16c784]/20 text-[#16c784]' 
                        : 'bg-[#ea3943]/20 text-[#ea3943]'
                    }`}
                  >
                    {trade.type === 'entry' ? '▲ BUY' : '▼ SELL'}
                  </span>
                  <span className="text-[10px] text-[#808a9d]">
                    {formatTooltipDate(trade.timestamp)}
                  </span>
                </div>
                
                {/* Price */}
                <div className="flex justify-between items-center text-sm mb-1">
                  <span className="text-[#808a9d]">Price:</span>
                  <span className="font-mono font-medium text-white">
                    ${trade.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                  </span>
                </div>
                
                {/* Quantity */}
                {trade.quantity && (
                  <div className="flex justify-between items-center text-sm mb-1">
                    <span className="text-[#808a9d]">Qty:</span>
                    <span className="font-mono text-white">{trade.quantity.toFixed(4)}</span>
                  </div>
                )}
                
                {/* PnL (only for exit) */}
                {trade.type === 'exit' && trade.pnl !== undefined && (
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-[#808a9d]">PnL:</span>
                    <span className={`font-mono font-semibold ${trade.pnl >= 0 ? 'text-[#16c784]' : 'text-[#ea3943]'}`}>
                      {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                      {trade.pnlPercentage !== undefined && (
                        <span className="text-xs ml-1">
                          ({trade.pnlPercentage >= 0 ? '+' : ''}{trade.pnlPercentage.toFixed(2)}%)
                        </span>
                      )}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}