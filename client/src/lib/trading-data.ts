// Mock data generators for the trading dashboard

export interface Candle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface Trade {
  id: string
  type: "buy" | "sell"
  price: number
  amount: number
  time: number
  strategy: string
  pnl?: number
}

export interface BacktestResult {
  totalTrades: number
  winRate: number
  totalReturn: number
  maxDrawdown: number
  sharpeRatio: number
  trades: Trade[]
}

export const CRYPTO_PAIRS = [
  { symbol: "BTCUSDT", name: "Bitcoin", icon: "₿" },
  { symbol: "ETHUSDT", name: "Ethereum", icon: "Ξ" },
  { symbol: "SOLUSDT", name: "Solana", icon: "S" },
  { symbol: "BNBUSDT", name: "BNB", icon: "B" },
  { symbol: "XRPUSDT", name: "XRP", icon: "X" },
  { symbol: "ADAUSDT", name: "Cardano", icon: "A" },
  { symbol: "AVAXUSDT", name: "Avalanche", icon: "🔺" },
  { symbol: "DOGEUSDT", name: "Dogecoin", icon: "Ð" },
  { symbol: "DOTUSDT", name: "Polkadot", icon: "●" },
  { symbol: "LINKUSDT", name: "Chainlink", icon: "⬡" },
  { symbol: "MATICUSDT", name: "Polygon", icon: "⬢" },
  { symbol: "SHIBUSDT", name: "Shiba Inu", icon: "🐕" },
  { symbol: "LTCUSDT", name: "Litecoin", icon: "Ł" },
  { symbol: "BCHUSDT", name: "Bitcoin Cash", icon: "₿" },
  { symbol: "UNIUSDT", name: "Uniswap", icon: "🦄" },
  { symbol: "NEARUSDT", name: "NEAR", icon: "N" },
  { symbol: "APTUSDT", name: "Aptos", icon: "" },
  { symbol: "SUIUSDT", name: "Sui", icon: "" },
  { symbol: "PEPEUSDT", name: "Pepe", icon: "🐸" },
  { symbol: "WIFUSDT", name: "dogwifhat", icon: "👒" },
  { symbol: "FETUSDT", name: "Fetch.ai", icon: "🤖" },
  { symbol: "RNDRUSDT", name: "Render", icon: "🎨" },
  { symbol: "TAOUSDT", name: "Bittensor", icon: "τ" },
  { symbol: "ATOMUSDT", name: "Cosmos", icon: "⚛" },
  { symbol: "STXUSDT", name: "Stacks", icon: "S" },
  { symbol: "GRTUSDT", name: "The Graph", icon: "" },
  { symbol: "FILUSDT", name: "Filecoin", icon: "F" },
  { symbol: "HBARUSDT", name: "Hedera", icon: "H" },
  { symbol: "OPUSDT", name: "Optimism", icon: "🔴" },
  { symbol: "ARBUSDT", name: "Arbitrum", icon: "🔵" },
  { symbol: "LDOUSDT", name: "Lido DAO", icon: "💧" },
  { symbol: "VETUSDT", name: "VeChain", icon: "V" },
  { symbol: "RUNEUSDT", name: "THORChain", icon: "ᚱ" },
  { symbol: "TIAUSDT", name: "Celestia", icon: "" },
  { symbol: "SEIUSDT", name: "Sei", icon: "" },
  { symbol: "INJUSDT", name: "Injective", icon: "🥷" },
  { symbol: "BONKUSDT", name: "Bonk", icon: "🐕" },
  { symbol: "FLOKIUSDT", name: "Floki", icon: "⚔️" },
  { symbol: "ORDIUSDT", name: "ORDI", icon: "" },
  { symbol: "BEAMXUSDT", name: "Beam", icon: "" },
  { symbol: "JUPUSDT", name: "Jupiter", icon: "🪐" },
  { symbol: "PYTHUSDT", name: "Pyth", icon: "" },
  { symbol: "STRKUSDT", name: "Starknet", icon: "" },
  { symbol: "ENAUSDT", name: "Ethena", icon: "" },
  { symbol: "WLDUSDT", name: "Worldcoin", icon: "🌐" },
  { symbol: "AAVEUSDT", name: "Aave", icon: "👻" },
  { symbol: "EGLDUSDT", name: "MultiversX", icon: "" },
  { symbol: "THETAUSDT", name: "Theta", icon: "" },
  { symbol: "FTMUSDT", name: "Fantom", icon: "" },
  { symbol: "ALGOUSDT", name: "Algorand", icon: "Ⱥ" },
  { symbol: "EOSUSDT", name: "EOS", icon: "" },
  { symbol: "FLOWUSDT", name: "Flow", icon: "" },
  { symbol: "MANAUSDT", name: "Decentraland", icon: "🏛️" },
  { symbol: "SANDUSDT", name: "The Sandbox", icon: "🏖️" },
  { symbol: "AXSUSDT", name: "Axie Infinity", icon: "⚔️" },
  { symbol: "NEOUSDT", name: "NEO", icon: "" },
  { symbol: "QTUMUSDT", name: "QTUM", icon: "" },
  { symbol: "IOTAUSDT", name: "IOTA", icon: "" },
  { symbol: "XLMUSDT", name: "Stellar", icon: "*" },
  { symbol: "TRXUSDT", name: "TRON", icon: "T" },
  { symbol: "ETCUSDT", name: "Ethereum Classic", icon: "Ξ" },
  { symbol: "ZECUSDT", name: "Zcash", icon: "ⓩ" },
  { symbol: "DASHUSDT", name: "Dash", icon: "D" },
  { symbol: "CHZUSDT", name: "Chiliz", icon: "🌶️" },
  { symbol: "ENJUSDT", name: "Enjin", icon: "" },
  { symbol: "ZILUSDT", name: "Zilliqa", icon: "" },
  { symbol: "BATUSDT", name: "Basic Attention", icon: "🦁" },
  { symbol: "KNCUSDT", name: "Kyber Network", icon: "" },
  { symbol: "LRCUSDT", name: "Loopring", icon: "" },
  { symbol: "COMPUSDT", name: "Compound", icon: "" },
  { symbol: "SNXUSDT", name: "Synthetix", icon: "" },
  { symbol: "YFIUSDT", name: "yearn.finance", icon: "" },
  { symbol: "SUSHIUSDT", name: "SushiSwap", icon: "🍣" },
  { symbol: "CRVUSDT", name: "Curve", icon: "" },
  { symbol: "1INCHUSDT", name: "1inch", icon: "🦄" },
  { symbol: "CAKEUSDT", name: "PancakeSwap", icon: "🥞" },
  { symbol: "GALAUSDT", name: "Gala", icon: "🕹️" },
  { symbol: "DYDXUSDT", name: "dYdX", icon: "" },
  { symbol: "ENSUSDT", name: "Ethereum Name Service", icon: "" },
  { symbol: "IMXUSDT", name: "Immutable", icon: "" },
  { symbol: "GMTUSDT", name: "STEPN", icon: "👟" },
  { symbol: "APEUSDT", name: "ApeCoin", icon: "🦍" },
  { symbol: "LUNCUSDT", name: "Terra Classic", icon: "" },
  { symbol: "USTCUSDT", name: "TerraClassicUSD", icon: "" },
  { symbol: "WUSDT", name: "Wormhole", icon: "" },
  { symbol: "NOTUSDT", name: "Notcoin", icon: "" },
  { symbol: "ZROUSDT", name: "LayerZero", icon: "" },
  { symbol: "TONUSDT", name: "Toncoin", icon: "💎" }
];

export const TIMEFRAME_LABELS: Record<string, string> = {
  "M1": "1m",
  "M5": "5m",
  "M15": "15m",
  "H1": "1h",
  "H4": "4h",
  "D1": "1d",
  "W1": "1w",
  "MO1": "1M"
};

export const TIMEFRAMES = Object.keys(TIMEFRAME_LABELS);

export const STRATEGIES = [
  {
    id: "ma_crossover",
    name: "MA Crossover",
    description: "Buy when fast MA crosses above slow MA, sell when it crosses below",
    params: { fastPeriod: 9, slowPeriod: 21 },
  },
  {
    id: "rsi",
    name: "RSI Strategy",
    description: "Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought)",
    params: { period: 14, oversold: 30, overbought: 70 },
  },
]

// Generate mock candlestick data
export function generateCandles(basePrice: number, count: number): Candle[] {
  const candles: Candle[] = []
  let currentPrice = basePrice
  const now = Date.now()

  for (let i = count - 1; i >= 0; i--) {
    const volatility = currentPrice * 0.02
    const change = (Math.random() - 0.5) * volatility
    const open = currentPrice
    const close = currentPrice + change
    const high = Math.max(open, close) + Math.random() * volatility * 0.5
    const low = Math.min(open, close) - Math.random() * volatility * 0.5

    candles.push({
      time: now - i * 3600000,
      open,
      high,
      low,
      close,
      volume: Math.random() * 1000000 + 500000,
    })

    currentPrice = close
  }

  return candles
}

// Calculate Simple Moving Average
export function calculateSMA(data: number[], period: number): (number | null)[] {
  const sma: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      sma.push(null)
    } else {
      const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
      sma.push(sum / period)
    }
  }
  return sma
}

// Calculate RSI
export function calculateRSI(prices: number[], period = 14): (number | null)[] {
  const rsi: (number | null)[] = []
  const gains: number[] = []
  const losses: number[] = []

  for (let i = 1; i < prices.length; i++) {
    const change = prices[i] - prices[i - 1]
    gains.push(change > 0 ? change : 0)
    losses.push(change < 0 ? -change : 0)
  }

  for (let i = 0; i < prices.length; i++) {
    if (i < period) {
      rsi.push(null)
    } else {
      const avgGain = gains.slice(i - period, i).reduce((a, b) => a + b, 0) / period
      const avgLoss = losses.slice(i - period, i).reduce((a, b) => a + b, 0) / period

      if (avgLoss === 0) {
        rsi.push(100)
      } else {
        const rs = avgGain / avgLoss
        rsi.push(100 - 100 / (1 + rs))
      }
    }
  }

  return rsi
}

// Run backtest simulation
export function runBacktest(candles: Candle[], strategyId: string, initialCapital = 10000): BacktestResult {
  const trades: Trade[] = []
  const prices = candles.map((c) => c.close)
  let position: "long" | "none" = "none"
  let entryPrice = 0
  let capital = initialCapital
  let peakCapital = initialCapital
  let maxDrawdown = 0

  if (strategyId === "ma_crossover") {
    const fastMA = calculateSMA(prices, 9)
    const slowMA = calculateSMA(prices, 21)

    for (let i = 21; i < candles.length; i++) {
      const fast = fastMA[i]
      const slow = slowMA[i]
      const prevFast = fastMA[i - 1]
      const prevSlow = slowMA[i - 1]

      if (fast && slow && prevFast && prevSlow) {
        // Golden cross - buy signal
        if (prevFast <= prevSlow && fast > slow && position === "none") {
          position = "long"
          entryPrice = candles[i].close
          trades.push({
            id: `trade-${trades.length}`,
            type: "buy",
            price: entryPrice,
            amount: capital / entryPrice,
            time: candles[i].time,
            strategy: "MA Crossover",
          })
        }
        // Death cross - sell signal
        else if (prevFast >= prevSlow && fast < slow && position === "long") {
          const exitPrice = candles[i].close
          const pnl = ((exitPrice - entryPrice) / entryPrice) * 100
          capital = capital * (1 + pnl / 100)

          trades.push({
            id: `trade-${trades.length}`,
            type: "sell",
            price: exitPrice,
            amount: capital / exitPrice,
            time: candles[i].time,
            strategy: "MA Crossover",
            pnl,
          })

          position = "none"
          peakCapital = Math.max(peakCapital, capital)
          maxDrawdown = Math.max(maxDrawdown, ((peakCapital - capital) / peakCapital) * 100)
        }
      }
    }
  } else if (strategyId === "rsi") {
    const rsi = calculateRSI(prices, 14)

    for (let i = 14; i < candles.length; i++) {
      const currentRSI = rsi[i]

      if (currentRSI !== null) {
        // Oversold - buy signal
        if (currentRSI < 30 && position === "none") {
          position = "long"
          entryPrice = candles[i].close
          trades.push({
            id: `trade-${trades.length}`,
            type: "buy",
            price: entryPrice,
            amount: capital / entryPrice,
            time: candles[i].time,
            strategy: "RSI Strategy",
          })
        }
        // Overbought - sell signal
        else if (currentRSI > 70 && position === "long") {
          const exitPrice = candles[i].close
          const pnl = ((exitPrice - entryPrice) / entryPrice) * 100
          capital = capital * (1 + pnl / 100)

          trades.push({
            id: `trade-${trades.length}`,
            type: "sell",
            price: exitPrice,
            amount: capital / exitPrice,
            time: candles[i].time,
            strategy: "RSI Strategy",
            pnl,
          })

          position = "none"
          peakCapital = Math.max(peakCapital, capital)
          maxDrawdown = Math.max(maxDrawdown, ((peakCapital - capital) / peakCapital) * 100)
        }
      }
    }
  }

  const winningTrades = trades.filter((t) => t.pnl && t.pnl > 0).length
  const sellTrades = trades.filter((t) => t.type === "sell").length

  return {
    totalTrades: sellTrades,
    winRate: sellTrades > 0 ? (winningTrades / sellTrades) * 100 : 0,
    totalReturn: ((capital - initialCapital) / initialCapital) * 100,
    maxDrawdown,
    sharpeRatio: Math.random() * 2 + 0.5,
    trades,
  }
}
