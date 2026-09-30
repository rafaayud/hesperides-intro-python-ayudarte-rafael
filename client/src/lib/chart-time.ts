import type { SeriesMarker, UTCTimestamp } from 'lightweight-charts'

// Keep actual instants throughout the app; timezone conversion belongs in labels.
export function toUnixSeconds(value: string | number): UTCTimestamp {
  const seconds = typeof value === 'number' ? value : Date.parse(value) / 1000
  if (typeof value === 'string' && !/(Z|[+-]\d{2}:?\d{2})$/i.test(value)) {
    throw new Error(`Timestamp must include a timezone: ${value}`)
  }
  if (!Number.isFinite(seconds)) throw new Error('Invalid timestamp')
  return seconds as UTCTimestamp
}

export function formatUtcDateTime(value: string | number): string {
  return new Date(toUnixSeconds(value) * 1000).toLocaleString('en-GB', {
    timeZone: 'UTC', year: 'numeric', month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })
}

export function backendInterval(interval: string): string {
  const intervals: Record<string, string> = {
    '1m': 'M1', '5m': 'M5', '15m': 'M15', '1h': 'H1',
    '4h': 'H4', '1d': 'D1', '1w': 'W1', '1M': 'MO1',
  }
  return intervals[interval] || interval.toUpperCase()
}

export function mergeCandles<T extends { time: number }>(...batches: T[][]): T[] {
  // Later updates replace a candle; never invent a different opening time.
  return [...new Map(batches.flat().map(c => [c.time, c])).values()]
    .sort((a, b) => a.time - b.time)
}

type TimedTrade = { entry_time: string | number; exit_time: string | number }

export function tradeMarkers(
  candles: { time: number }[], trades: TimedTrade[], interval: string,
): SeriesMarker<UTCTimestamp>[] {
  const frame = backendInterval(interval)
  const durations: Record<string, number> = {
    M1: 60, M5: 300, M15: 900, H1: 3600, H4: 14400, D1: 86400, W1: 604800,
  }
  const markers: SeriesMarker<UTCTimestamp>[] = []
  for (const trade of trades) {
    for (const side of ['BUY', 'SELL'] as const) {
      const execution = toUnixSeconds(side === 'BUY' ? trade.entry_time : trade.exit_time)
      // Find the candle containing the execution, not the closest next candle.
      let low = 0
      let high = candles.length
      while (low < high) {
        const mid = (low + high) >>> 1
        if (candles[mid].time <= execution) low = mid + 1
        else high = mid
      }
      const candle = candles[low - 1]
      if (!candle) continue
      const date = new Date(candle.time * 1000)
      const end = frame === 'MO1'
        ? Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1) / 1000
        : candle.time + durations[frame]
      // Do not attach out-of-range trades or trades in missing data to a wrong bar.
      if (!(execution < end)) continue
      markers.push({
        time: candle.time as UTCTimestamp,
        position: side === 'BUY' ? 'belowBar' : 'aboveBar',
        color: side === 'BUY' ? '#16c784' : '#ea3943',
        shape: side === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: side,
      })
    }
  }
  return markers.sort((a, b) => a.time - b.time)
}
