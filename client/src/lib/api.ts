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

export interface CreatePortfolioRequest {
  name: string
  portfolio_id: string
  traders: TraderConfig[]
  capital: number
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

// Fetch all available strategies
export async function fetchStrategies(): Promise<Strategy[]> {
  const response = await fetch(`${API_BASE_URL}/trading/strategies`)
  if (!response.ok) {
    throw new Error(`Failed to fetch strategies: ${response.statusText}`)
  }
  const data = await response.json()
  return data.strategies
}

// Fetch parameters for a specific strategy
export async function fetchStrategyParams(strategyName: string): Promise<StrategyParamsResponse> {
  const response = await fetch(`${API_BASE_URL}/trading/strategies/${strategyName}/params`)
  if (!response.ok) {
    throw new Error(`Failed to fetch strategy params: ${response.statusText}`)
  }
  return await response.json()
}

// Create a new trading portfolio
export async function createPortfolio(request: CreatePortfolioRequest): Promise<CreatePortfolioResponse> {
  const response = await fetch(`${API_BASE_URL}/trading/create`, {
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

