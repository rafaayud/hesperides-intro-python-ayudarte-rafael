import assert from 'node:assert/strict'
import test from 'node:test'
import { formatPnl } from '../src/lib/utils.ts'

test('small trading losses remain visible instead of rounding to negative zero', () => {
  assert.equal(formatPnl(-0.002422), '-0.002422')
  assert.equal(formatPnl(0.002422), '0.002422')
  assert.equal(formatPnl(0), '0.00')
  assert.equal(formatPnl(1250.678), '1,250.68')
})
