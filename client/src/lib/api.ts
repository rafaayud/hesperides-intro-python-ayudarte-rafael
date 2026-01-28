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

