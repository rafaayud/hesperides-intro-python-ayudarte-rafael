"use client"

import { useEffect, useRef } from "react"
import { 
  createChart, 
  ColorType,
  UTCTimestamp,
  CrosshairMode
} from "lightweight-charts"
import type { IChartApi, ISeriesApi } from "lightweight-charts"

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
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    }
  }, [symbol, interval])

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

  return (
    <div className="w-full h-full relative">
      <div ref={chartContainerRef} className="w-full h-full" />
    </div>
  )
}