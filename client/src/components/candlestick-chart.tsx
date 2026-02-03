"use client"

import { useEffect, useRef, useState } from "react"
import { 
  createChart, 
  ColorType,
  UTCTimestamp,
  CrosshairMode
} from "lightweight-charts"
import type { IChartApi, ISeriesApi, SeriesMarker, Time, MouseEventParams } from "lightweight-charts"

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

// Helper para parsear string ISO como UTC explícitamente
// Si el string no tiene 'Z' o offset de timezone, lo trata como UTC
// IMPORTANTE: Siempre parsea como UTC, nunca como hora local
function parseAsUTC(isoString: string): number {
  const trimmed = isoString.trim();
  
  // Check if it already has timezone info
  const hasTimezone = trimmed.endsWith('Z') || trimmed.match(/[+-]\d{2}:?\d{2}$/);
  
  if (hasTimezone) {
    // Already has timezone, parse directly
    return new Date(trimmed).getTime() / 1000;
  }
  
  // No timezone info - parse manually as UTC to avoid local timezone interpretation
  // Format: "2026-02-03T15:00:00" or "2026-02-03 15:00:00"
  const match = trimmed.match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?/);
  if (match) {
    const [, year, month, day, hour, minute, second, millis] = match;
    // Parse as UTC explicitly
    const utcDate = new Date(Date.UTC(
      parseInt(year), 
      parseInt(month) - 1, 
      parseInt(day), 
      parseInt(hour), 
      parseInt(minute), 
      parseInt(second || '0'),
      parseInt(millis || '0')
    ));
    return utcDate.getTime() / 1000;
  }
  
  // Fallback: try with 'Z' appended
  return new Date(trimmed + 'Z').getTime() / 1000;
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

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: "#16c784", 
      downColor: "#ea3943", 
      borderVisible: false,
      wickUpColor: "#16c784", 
      wickDownColor: "#ea3943",
    })
    
    candleSeriesRef.current = candlestickSeries

    // Añadir serie de volumen
    const volumeSeries = chart.addHistogramSeries({
      color: "#26a69a",
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    })
    
    volumeSeriesRef.current = volumeSeries

    // Configurar escala de volumen
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.75,
        bottom: 0.02,
      },
    })

    const fetchHistoricalData = async (retryCount = 0) => {
      const MAX_RETRIES = 3;
      const RETRY_DELAY = 1000; // 1 second
      
      try {
        // Convertir formato de intervalo al formato del backend
        const backendInterval = convertIntervalToBackendFormat(interval);
        
        console.log(`[Chart] Loading ${symbol}/${backendInterval} (attempt ${retryCount + 1})...`);
        
        // Sincronizar Binance -> Postgres
        const { syncCandles, getCandles } = await import('@/lib/api');
        
        try {
          console.log(`[Chart] Starting sync for ${symbol}/${backendInterval}...`);
          const syncResult = await syncCandles([symbol], [backendInterval]);
          console.log(`[Chart] Sync completed successfully:`, syncResult);
        } catch (syncError: any) {
          console.error(`[Chart] Sync failed:`, syncError);
          console.warn(`[Chart] Continuing anyway - data might already exist in DB`);
          // Continue anyway - data might already exist
        }
    
        // Leer Postgres -> Frontend
        console.log(`[Chart] Fetching historical data for ${symbol}/${backendInterval}...`);
        const result = await getCandles(symbol, backendInterval);
        console.log(`[Chart] Received ${result.candles?.length || 0} candles`);
        if (result.candles && result.candles.length > 0) {
          console.log(`[Chart] First candle:`, result.candles[0]);
          console.log(`[Chart] Last candle:`, result.candles[result.candles.length - 1]);
        }
        
        // If no candles and we can retry, wait and try again
        if ((!result.candles || result.candles.length === 0) && retryCount < MAX_RETRIES) {
          console.log(`[Chart] No candles received, retrying in ${RETRY_DELAY}ms...`);
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
          return fetchHistoricalData(retryCount + 1);
        }
        
        // Fetch trade markers if portfolioId and traderId are provided
        let tradeMarkers: TradeMarker[] = [];
        if (portfolioId && traderId) {
          try {
            console.log(`[Chart] Fetching trade markers for ${portfolioId}/${traderId}...`);
            const apiBaseUrl = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api';
            const tradesResponse = await fetch(
              `${apiBaseUrl}/portfolio/trades/${portfolioId}?trader_id=${traderId}&limit=500`
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
                  // Parse as UTC and adjust for lightweight-charts local time interpretation
                  const utcEntryTime = parseAsUTC(trade.entry_time);
                  const timezoneOffsetSeconds = -new Date().getTimezoneOffset() * 60;
                  const entryTime = utcEntryTime + timezoneOffsetSeconds;
                  markers.push({
                    time: entryTime as UTCTimestamp,
                    position: 'belowBar',
                    color: '#16c784',
                    shape: 'arrowUp',
                    text: 'BUY',
                    size: 2,
                    id: `trade-${idx}-entry`
                  });
                  
                  // Store trade data for tooltip (use UTC timestamp)
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
                  // Parse as UTC and adjust for lightweight-charts local time interpretation
                  const utcExitTime = parseAsUTC(trade.exit_time);
                  const timezoneOffsetSeconds = -new Date().getTimezoneOffset() * 60;
                  const exitTime = utcExitTime + timezoneOffsetSeconds;
                  const pnl = trade.pnl || 0;
                  markers.push({
                    time: exitTime as UTCTimestamp,
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
              timestamp = parseAsUTC(c.timestamp.timestamp);
            }
            // Opción 2: timestamp (si viene como string ISO)
            else if (c.timestamp) {
              timestamp = parseAsUTC(c.timestamp);
            }
            // Opción 3: open_time (formato ISO string) - este es el formato principal
            else if (c.open_time) {
              // Parse as UTC first
              const utcTimestamp = parseAsUTC(c.open_time);
              // lightweight-charts interprets timestamps as local time, so we need to adjust
              // Get timezone offset in seconds (negative means ahead of UTC)
              const timezoneOffsetSeconds = -new Date().getTimezoneOffset() * 60;
              // Add offset so lightweight-charts displays it correctly
              timestamp = utcTimestamp + timezoneOffsetSeconds;
            }
            // Opción 4: time (formato ISO string)
            else if (c.time) {
              timestamp = parseAsUTC(c.time);
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

            // Keep timestamps in UTC to avoid DST issues
            // lightweight-charts will display them in local time via localization
            return {
              time: timestamp as UTCTimestamp,
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
        
        // Remove duplicate timestamps and ensure strict ascending order
        // This is critical for lightweight-charts which requires strict ascending order
        const uniqueData: any[] = [];
        const seen = new Set<number>();
        let duplicateCount = 0;
        let orderViolations = 0;
        
        for (let i = 0; i < formattedData.length; i++) {
          const candle = formattedData[i];
          if (!candle) continue;
          
          let time: number = candle.time;
          const originalTime = time;
          
          // If duplicate, increment by 1 second until unique
          if (seen.has(time)) {
            duplicateCount++;
            while (seen.has(time)) {
              time = time + 1;
            }
          }
          
          // Ensure strict ascending order
          if (uniqueData.length > 0 && time <= uniqueData[uniqueData.length - 1].time) {
            orderViolations++;
            time = uniqueData[uniqueData.length - 1].time + 1;
          }
          
          seen.add(time);
          uniqueData.push({ ...candle, time: time as UTCTimestamp });
        }
        
        if (duplicateCount > 0 || orderViolations > 0) {
          console.warn(`[Chart] Fixed ${duplicateCount} duplicate timestamps and ${orderViolations} order violations`);
        }
        console.log(`[Chart] Filtered ${formattedData.length} -> ${uniqueData.length} unique candles (strictly ordered)`);
        
        // Ensure series are ready before setting data
        if (!candlestickSeries) {
          console.error("[Chart] Candlestick series not ready");
          return;
        }
        
        console.log(`[Chart] Setting ${uniqueData.length} candles to chart`);
        candlestickSeries.setData(uniqueData.map(({ volume, ...rest }) => rest));

        // Preparar datos de volumen para la serie de histograma (usar datos únicos)
        const volumeData = uniqueData.map((candle) => ({
          time: candle.time,
          value: candle.volume,
          color: candle.close >= candle.open ? '#16c78480' : '#ea394380',
        }));

        if (volumeSeriesRef.current) {
          volumeSeriesRef.current.setData(volumeData);
        }

        // Apply trade markers if available
        if (tradeMarkers.length > 0 && candleSeriesRef.current) {
          // Get all candle times as a set for quick lookup (use uniqueData)
          const candleTimes = new Set(uniqueData.map(c => c.time));
          const candleTimesArray = uniqueData.map(c => c.time).sort((a, b) => a - b);
          
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
            // En lightweight-charts v4, setMarkers funciona directamente
            candleSeriesRef.current.setMarkers(validMarkers as SeriesMarker<Time>[]);
            console.log(`[Chart] ✅ Applied ${validMarkers.length} markers to chart:`, validMarkers);
          } else {
            console.log(`[Chart] ⚠️ No valid markers to apply (all ${tradeMarkers.length} outside candle range)`);
            console.log(`[Chart] Candle time range: ${candleTimesArray[0]} - ${candleTimesArray[candleTimesArray.length - 1]}`);
            console.log(`[Chart] Trade marker times:`, tradeMarkers.map(m => m.time));
          }
        }

        // Si hay datos históricos, actualizamos el precio inicial en la App
        if (uniqueData.length > 0 && onPriceUpdate) {
          const lastCandle = uniqueData[uniqueData.length - 1];
          const isUp = lastCandle.close >= lastCandle.open;
          onPriceUpdate(lastCandle.close, isUp);
        }

      } catch (error) {
        console.error(`[Chart] Error loading data (attempt ${retryCount + 1}):`, error);
        
        // Retry on error
        if (retryCount < MAX_RETRIES) {
          console.log(`[Chart] Retrying in ${RETRY_DELAY}ms...`);
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
          return fetchHistoricalData(retryCount + 1);
        }
      }
    };

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

    // Load data - ensure chart and series are ready
    // For initial load, wait a bit for backend to be ready
    // For interval changes, load immediately
    const loadData = () => {
      // Double-check series are ready
      if (!candlestickSeries || !volumeSeriesRef.current) {
        console.warn("[Chart] Series not ready, retrying...");
        setTimeout(loadData, 100);
        return;
      }
      console.log("[Chart] Loading historical data...");
      fetchHistoricalData();
    };
    
    // Small delay on initial load to ensure backend is ready in Docker
    const initialDelay = 500;
    const timer = setTimeout(loadData, initialDelay);

    return () => {
      clearTimeout(timer);
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
    // Import dynamically to get the WebSocket URL
    const apiUrl = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api';
    const wsUrl = (apiUrl.replace('/api', '').replace('http://', 'ws://') || 'ws://localhost:8000') + `/live_candles/${symbol}/${backendInterval}`;
    const socket = new WebSocket(wsUrl);
  
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const c = data.candle;
  
      // Parse as UTC first
      const utcTime = parseAsUTC(c.open_time);
      // lightweight-charts interprets timestamps as local time, so we need to adjust
      const timezoneOffsetSeconds = -new Date().getTimezoneOffset() * 60;
      const adjustedTime = utcTime + timezoneOffsetSeconds;
      
      const liveCandle = {
        time: adjustedTime as UTCTimestamp, 
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
          time: adjustedTime as UTCTimestamp,
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