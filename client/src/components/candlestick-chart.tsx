"use client"

import { useEffect, useRef } from "react"
import { 
  createChart, 
  ColorType, 
  ISeriesApi, 
  UTCTimestamp,
  CandlestickSeries,
  HistogramSeries,
  IChartApi
} from "lightweight-charts"

// 1. Definimos la interfaz para aceptar la función 'onPriceUpdate'
interface ChartProps {
  symbol: string
  interval: string
  onPriceUpdate?: (price: number, isUp: boolean) => void
}

// Helper para convertir formato de intervalo del frontend al backend
function convertIntervalToBackendFormat(interval: string): string {
  const intervalMap: Record<string, string> = {
    "1m": "M1", "5m": "M5", "15m": "M15",
    "1h": "H1", "4h": "H4",
    "1d": "D1", "1w": "W1", "1M": "MO1"
  };
  return intervalMap[interval.toLowerCase()] || interval.toUpperCase();
}

export function TradingViewChart({ symbol, interval, onPriceUpdate }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null)

  // EFECTO 1: Inicialización del Gráfico y Carga de Histórico
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: { 
        background: { type: ColorType.Solid, color: "#1a1a2e" }, 
        textColor: "#d1d5db" 
      },
      grid: { 
        vertLines: { color: "#2a2a4e" }, 
        horzLines: { color: "#2a2a4e" } 
      },
      timeScale: {
        timeVisible: true,        // muestra HH:MM cuando hay suficiente zoom
        secondsVisible: false,    // puedes poner true si quieres ver también segundos
        borderColor: "#2a2a4e",
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
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
      upColor: "#22c55e", 
      downColor: "#ef4444", 
      borderVisible: false,
      wickUpColor: "#22c55e", 
      wickDownColor: "#ef4444",
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
    
        candlestickSeries.setData(formattedData.map(({ volume, ...rest }) => rest));

        // Preparar datos de volumen para la serie de histograma
        const volumeData = formattedData.map((candle) => ({
          time: candle.time,
          value: candle.volume,
          color: candle.close >= candle.open ? '#22c55e80' : '#ef444480',
        }));

        if (volumeSeriesRef.current) {
          volumeSeriesRef.current.setData(volumeData);
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

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    }
  }, [symbol, interval]) // No incluimos onPriceUpdate aquí para evitar recargar el histórico innecesariamente

  // EFECTO 2: WebSocket para tiempo real
  useEffect(() => {
    const backendInterval = convertIntervalToBackendFormat(interval);
    const socket = new WebSocket(`ws://localhost:8000/live_candles/${symbol}/${backendInterval}`);
  
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const c = data.candle;
  
      const liveCandle = {
        time: Math.floor(new Date(c.open_time).getTime() / 1000) as UTCTimestamp, 
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
          time: liveCandle.time,
          value: c.volume,
          color: c.close >= c.open ? '#22c55e80' : '#ef444480',
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
    <div className="w-full bg-[#1a1a2e] p-4 rounded-lg border border-[#2a2a4e]">
      <div ref={chartContainerRef} className="w-full" />
    </div>
  )
}