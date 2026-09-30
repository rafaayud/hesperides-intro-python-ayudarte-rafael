import assert from 'node:assert/strict'
import { test } from 'node:test'
import { backendInterval, formatUtcDateTime, mergeCandles, toUnixSeconds, tradeMarkers } from '../src/lib/chart-time'

test('ISO offsets and fractional seconds identify the same instant in every timezone', () => {
  const original = process.env.TZ
  try {
    for (const tz of ['UTC', 'Europe/Madrid', 'America/New_York']) {
      process.env.TZ = tz
      for (const iso of ['2026-01-15T12:00:00.123Z', '2026-07-15T12:00:00.123Z', '2026-10-25T01:30:00.123Z']) {
        assert.equal(toUnixSeconds(iso), Date.parse(iso) / 1000)
        assert.equal(formatUtcDateTime(iso).endsWith(iso.slice(11, 19)), true)
      }
      assert.equal(toUnixSeconds('2026-07-15T14:00:00.123456+02:00'), toUnixSeconds('2026-07-15T12:00:00.123Z'))
    }
  } finally {
    if (original === undefined) delete process.env.TZ
    else process.env.TZ = original
  }
  assert.throws(() => toUnixSeconds('2026-01-15T12:00:00'), /timezone/)
  assert.throws(() => toUnixSeconds('invalidZ'), /Invalid/)
  assert.equal(toUnixSeconds(0), 0)
})

test('history and early live updates merge without manufacturing extra seconds', () => {
  const history = [{ time: 120, close: 1 }, { time: 60, close: 2 }, { time: 120, close: 3 }]
  assert.deepEqual(mergeCandles(history, [{ time: 120, close: 4 }, { time: 180, close: 5 }]), [
    { time: 60, close: 2 }, { time: 120, close: 4 }, { time: 180, close: 5 },
  ])
})

test('markers stay within the executed candle and are sorted across overlapping trades', () => {
  const markers = tradeMarkers([{ time: 60 }, { time: 120 }, { time: 240 }], [
    { entry_time: 121.234, exit_time: 250 },
    { entry_time: 60, exit_time: 120 },
    { entry_time: 59, exit_time: 190 }, // outside history, then a missing candle
    { entry_time: 299.999, exit_time: 300 }, // outside the last candle
  ], 'M1')
  assert.deepEqual(markers.map(m => [m.time, m.text]), [
    [60, 'BUY'], [120, 'BUY'], [120, 'SELL'], [240, 'SELL'], [240, 'BUY'],
  ])
})

test('daylight saving repeated local hours remain distinct UTC candles', () => {
  const first = toUnixSeconds('2026-10-25T02:00:00+02:00')
  const second = toUnixSeconds('2026-10-25T02:00:00+01:00')
  assert.equal(second - first, 3600)
  const markers = tradeMarkers([{ time: first }, { time: second }], [
    { entry_time: '2026-10-25T02:45:00+02:00', exit_time: '2026-10-25T02:15:00+01:00' },
  ], '1h')
  assert.deepEqual(markers.map(m => m.time), [first, second])
})

test('month intervals preserve case and use calendar boundaries including leap years', () => {
  assert.equal(backendInterval('1M'), 'MO1')
  assert.equal(backendInterval('1m'), 'M1')
  const february = toUnixSeconds('2024-02-01T00:00:00Z')
  const markers = tradeMarkers([{ time: february }], [
    { entry_time: '2024-02-29T23:59:59Z', exit_time: '2024-03-01T00:00:00Z' },
  ], 'MO1')
  assert.deepEqual(markers.map(m => [m.time, m.text]), [[february, 'BUY']])
})
