// API service for trading endpoints

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export interface Strategy {
  id: string
  name: string
  display_name: string
  description: string
}

export interface StrategyParam {
  name: string
  type: 'number' | 'select' | 'array' | 'text'
  label: string
  description: string
  default?: any
  required?: boolean
  min?: number
  max?: number
  step?: number
  options?: Array<{ value: string; label: string }>
}

export interface StrategyParamsResponse {
  strategy_name: string
  parameters: {
    common: StrategyParam[]
    specific: StrategyParam[]
    all: StrategyParam[]
  }
}

export interface TraderConfig {
  symbol: string
  interval: string
  strategy: string
  strategy_params?: Record<string, any>
}

export interface AdapterConfig {
  exchange?: string
  stream?: string
  order?: string
  portfolio_storage?: string
}

export interface CreatePortfolioRequest {
  name: string
  portfolio_id: string
  traders: TraderConfig[]
  capital: number
  adapters?: AdapterConfig
}

export interface CreatePortfolioResponse {
  status: string
  portfolio_id: string
  portfolio_name: string
  traders_count: number
  capital: number
  traders: Array<{
    id: string
    symbol: string
    interval: string
    strategy: string
    min_candles: number
  }>
}

export interface Portfolio {
  id: string
  name: string
  initial_capital: number
}

export interface TradingStatus {
  portfolio_id: string
  is_running: boolean
  status: string
  running?: boolean
  task_done?: boolean
  traders_count?: number
}

// Fetch all available strategies
export async function fetchStrategies(): Promise<Strategy[]> {
  const response = await fetch(`${API_BASE_URL}/portfolio/strategies`)
  if (!response.ok) {
    throw new Error(`Failed to fetch strategies: ${response.statusText}`)
  }
  const data = await response.json()
  return data.strategies
}

// Fetch parameters for a specific strategy
export async function fetchStrategyParams(strategyName: string): Promise<StrategyParamsResponse> {
  const response = await fetch(`${API_BASE_URL}/portfolio/strategies/${strategyName}/params`)
  if (!response.ok) {
    throw new Error(`Failed to fetch strategy params: ${response.statusText}`)
  }
  return await response.json()
}

// Create a new trading portfolio
export async function createPortfolio(request: CreatePortfolioRequest): Promise<CreatePortfolioResponse> {
  const response = await fetch(`${API_BASE_URL}/portfolio/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to create portfolio: ${response.statusText}`)
  }
  
  return await response.json()
}

// List all portfolios
export async function listPortfolios(): Promise<Portfolio[]> {
  const response = await fetch(`${API_BASE_URL}/portfolio/list`)
  if (!response.ok) {
    throw new Error(`Failed to list portfolios: ${response.statusText}`)
  }
  const data = await response.json()
  return data.portfolios
}

// Start trading for a portfolio
export async function startTrading(portfolioId: string): Promise<{ status: string; portfolio_id: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/trading/start/${portfolioId}`, {
    method: 'POST',
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to start trading: ${response.statusText}`)
  }
  
  return await response.json()
}

// Stop trading for a portfolio
export async function stopTrading(portfolioId: string): Promise<{ status: string; portfolio_id: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/trading/stop/${portfolioId}`, {
    method: 'POST',
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to stop trading: ${response.statusText}`)
  }
  
  return await response.json()
}

// Get trading status for a portfolio
export async function getTradingStatus(portfolioId: string): Promise<TradingStatus> {
  const response = await fetch(`${API_BASE_URL}/trading/status/${portfolioId}`)
  if (!response.ok) {
    throw new Error(`Failed to get trading status: ${response.statusText}`)
  }
  return await response.json()
}

// ============ Portfolio Details ============

export interface Trader {
  id: string
  symbol: string
  interval: string
  strategy: string
  strategy_name?: string
}

export interface PortfolioDetails {
  status: string
  portfolio_id: string
  portfolio_name: string
  traders_count: number
  capital: number
  traders: Trader[]
}

export interface Trade {
  id: string
  trader_id: string
  symbol: string
  side: 'BUY' | 'SELL'
  entry_price: number
  exit_price: number
  quantity: number
  entry_time: string
  exit_time: string
  pnl: number
  pnl_percentage: number
  status: string
}

export interface ChartCandle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface TradeMarker {
  time: number
  position: 'aboveBar' | 'belowBar'
  color: string
  shape: 'arrowUp' | 'arrowDown'
  text: string
  id: string
}

export interface ChartData {
  candles: ChartCandle[]
  trades: TradeMarker[]
}

// Get portfolio details with traders
export async function getPortfolioDetails(portfolioId: string): Promise<PortfolioDetails> {
  const response = await fetch(`${API_BASE_URL}/portfolio/${portfolioId}`)
  if (!response.ok) {
    throw new Error(`Failed to get portfolio details: ${response.statusText}`)
  }
  return await response.json()
}

// Get traders for a portfolio
export async function getPortfolioTraders(portfolioId: string): Promise<{ status: string; traders: Trader[] }> {
  const response = await fetch(`${API_BASE_URL}/portfolio/traders/${portfolioId}`)
  if (!response.ok) {
    throw new Error(`Failed to get portfolio traders: ${response.statusText}`)
  }
  return await response.json()
}

// Get trades for a portfolio/trader
export async function getPortfolioTrades(
  portfolioId: string, 
  traderId?: string, 
  limit: number = 100
): Promise<{ status: string; trades: Trade[] }> {
  const params = new URLSearchParams()
  if (traderId) params.append('trader_id', traderId)
  params.append('limit', limit.toString())
  
  const response = await fetch(`${API_BASE_URL}/portfolio/trades/${portfolioId}?${params}`)
  if (!response.ok) {
    throw new Error(`Failed to get trades: ${response.statusText}`)
  }
  return await response.json()
}

// Get chart data with trade markers for a trader
export async function getTraderChartData(
  portfolioId: string,
  traderId: string,
  limit: number = 500
): Promise<ChartData> {
  const response = await fetch(
    `${API_BASE_URL}/portfolio/chart/${portfolioId}/${traderId}?limit=${limit}`
  )
  if (!response.ok) {
    throw new Error(`Failed to get chart data: ${response.statusText}`)
  }
  return await response.json()
}

// Delete a portfolio
export async function deletePortfolio(portfolioId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/portfolio/${portfolioId}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to delete portfolio: ${response.statusText}`)
  }
  return await response.json()
}

// ============ Global Stats & Positions ============

export interface GlobalStats {
  total_portfolios: number
  running_portfolios: number
  total_capital: number
  total_pnl: number
  total_pnl_percentage?: number
  total_trades: number
  winning_trades?: number
  win_rate: number
  best_portfolio?: { id: string | null; pnl: number | null }
  worst_portfolio?: { id: string | null; pnl: number | null }
}

export interface OpenPosition {
  portfolio_id?: string
  symbol: string
  side: string
  entry_price: number
  quantity: number
  entry_time: string
  current_value: number
  status?: string
}

export interface OpenPositionsResponse {
  positions: OpenPosition[]
  total_value: number
  by_symbol: Record<string, number>
}

// Get global stats for all portfolios
export async function getGlobalStats(): Promise<GlobalStats> {
  const response = await fetch(`${API_BASE_URL}/portfolio/stats/global`)
  if (!response.ok) {
    throw new Error(`Failed to get global stats: ${response.statusText}`)
  }
  const data = await response.json()
  // Backend returns { status: "success", stats: {...} }
  return data.stats || data
}

// ============ Backtest ============

export interface BacktestRequest {
  symbol: string
  interval: string
  strategy: string
  strategy_params?: Record<string, any>
  initial_capital: number
}

export interface BacktestTrade {
  entry_time: string | number
  exit_time: string | number
  side: 'BUY' | 'SELL'
  entry_price: number
  exit_price: number
  quantity?: number
  pnl: number
  pnl_percentage: number
}

export interface BacktestCandle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface BacktestResponse {
  symbol: string
  interval: string
  strategy_name: string
  initial_capital: number
  final_capital: number
  total_pnl: number
  total_pnl_percentage: number
  total_trades: number
  total_winners: number
  total_losers: number
  win_rate: number
  avg_pnl_per_trade: number
  // Optional fields - backend needs update to provide these
  trades?: BacktestTrade[]
  candles?: BacktestCandle[]
  equity_curve?: Array<{ time: number; value: number }>
}

export async function runBacktest(request: BacktestRequest): Promise<BacktestResponse> {
  const response = await fetch(`${API_BASE_URL}/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Failed to run backtest')
  }
  
  return await response.json()
}

// Get all open positions
export async function getOpenPositions(): Promise<OpenPositionsResponse> {
  const response = await fetch(`${API_BASE_URL}/portfolio/positions/open`)
  if (!response.ok) {
    throw new Error(`Failed to get open positions: ${response.statusText}`)
  }
  const data = await response.json()
  
  // Process positions to calculate totals
  const positions = data.positions || []
  let total_value = 0
  const by_symbol: Record<string, number> = {}
  
  for (const pos of positions) {
    const value = pos.current_value || (pos.entry_price * pos.quantity)
    total_value += value
    by_symbol[pos.symbol] = (by_symbol[pos.symbol] || 0) + value
  }
  
  return {
    positions,
    total_value,
    by_symbol
  }
}

