"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Plus, Trash2, Loader2, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"
import { fetchStrategies, fetchStrategyParams, createPortfolio, type Strategy, type StrategyParam, type TraderConfig } from "@/lib/api"
import { CRYPTO_PAIRS, TIMEFRAME_LABELS } from "@/lib/trading-data"

interface TraderFormData {
  symbol: string
  interval: string
  strategy: string
  params: Record<string, any>
}

interface CreatePortfolioProps {
  onSuccess?: () => void
}

export function CreatePortfolio({ onSuccess }: CreatePortfolioProps = {}) {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [success, setSuccess] = useState(false)
  
  // Portfolio form
  const [portfolioName, setPortfolioName] = useState("")
  const [portfolioId, setPortfolioId] = useState("")
  const [capital, setCapital] = useState<string>("10000")
  
  // Adapters
  const [adapters, setAdapters] = useState({
    exchange: "",
    stream: "",
    order: "",
    portfolio_storage: ""
  })
  
  // Traders
  const [traders, setTraders] = useState<TraderFormData[]>([
    { symbol: "BTCUSDT", interval: "H1", strategy: "", params: {} }
  ])
  
  // Strategy params cache
  const [strategyParamsCache, setStrategyParamsCache] = useState<Record<string, StrategyParam[]>>({})

  useEffect(() => {
    loadStrategies()
  }, [])

  const loadStrategies = async () => {
    try {
      const data = await fetchStrategies()
      setStrategies(data)
    } catch (error) {
      console.error("Failed to load strategies:", error)
    } finally {
      setLoading(false)
    }
  }

  const loadStrategyParams = async (strategyName: string) => {
    if (strategyParamsCache[strategyName]) {
      return strategyParamsCache[strategyName]
    }

    try {
      const data = await fetchStrategyParams(strategyName)
      const params = data.parameters.all
      setStrategyParamsCache(prev => ({ ...prev, [strategyName]: params }))
      return params
    } catch (error) {
      console.error(`Failed to load params for ${strategyName}:`, error)
      return []
    }
  }

  const handleStrategyChange = async (traderIndex: number, strategyName: string) => {
    const newTraders = [...traders]
    newTraders[traderIndex].strategy = strategyName
    newTraders[traderIndex].params = {}
    
    // Load params and set defaults
    const params = await loadStrategyParams(strategyName)
    params.forEach(param => {
      if (param.default !== undefined) {
        newTraders[traderIndex].params[param.name] = param.default
      }
    })
    
    setTraders(newTraders)
  }

  const handleParamChange = (traderIndex: number, paramName: string, value: any) => {
    const newTraders = [...traders]
    newTraders[traderIndex].params[paramName] = value
    setTraders(newTraders)
  }

  const addTrader = () => {
    setTraders([...traders, { symbol: "BTCUSDT", interval: "H1", strategy: "", params: {} }])
  }

  const removeTrader = (index: number) => {
    if (traders.length > 1) {
      setTraders(traders.filter((_, i) => i !== index))
    }
  }

  const renderParamInput = (traderIndex: number, param: StrategyParam) => {
    const value = traders[traderIndex].params[param.name] ?? param.default

    switch (param.type) {
      case 'number':
        return (
          <Input
            type="number"
            value={value || ''}
            onChange={(e) => handleParamChange(traderIndex, param.name, parseFloat(e.target.value) || param.default)}
            min={param.min}
            max={param.max}
            step={param.step || 1}
            placeholder={param.default?.toString()}
          />
        )
      case 'select':
        return (
          <Select
            value={value || param.default}
            onValueChange={(val) => handleParamChange(traderIndex, param.name, val)}
          >
            <SelectTrigger>
              <SelectValue placeholder={param.default} />
            </SelectTrigger>
            <SelectContent>
              {param.options?.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )
      default:
        return (
          <Input
            value={value || ''}
            onChange={(e) => handleParamChange(traderIndex, param.name, e.target.value)}
            placeholder={param.default?.toString()}
          />
        )
    }
  }

  const handleSubmit = async () => {
    if (!portfolioName || !portfolioId || traders.some(t => !t.strategy)) {
      toast.error("Please fill in all required fields", {
        description: "Portfolio name, ID, and strategy for each trader are required."
      })
      return
    }

    setCreating(true)
    setSuccess(false)

    try {
      const traderConfigs: TraderConfig[] = traders.map(trader => ({
        symbol: trader.symbol,
        interval: trader.interval,
        strategy: trader.strategy,
        strategy_params: Object.keys(trader.params).length > 0 ? trader.params : undefined
      }))

            const capitalValue = parseFloat(capital) || 0
            if (capitalValue <= 0) {
              toast.error("Invalid capital amount", {
                description: "Initial capital must be greater than 0."
              })
              return
            }

            // For now, always send None for adapters (using defaults)
            // Implementation kept for future use
            const response = await createPortfolio({
              name: portfolioName,
              portfolio_id: portfolioId,
              traders: traderConfigs,
              capital: capitalValue,
              adapters: undefined // Always use defaults for now
            })

      setSuccess(true)
      toast.success("Portfolio created successfully!", {
        description: `Portfolio "${response.portfolio_name}" with ${response.traders_count} trader(s) has been created.`
      })
      console.log("Portfolio created:", response)
      
      // Reset form after 1.5 seconds and call onSuccess
      setTimeout(() => {
        setPortfolioName("")
        setPortfolioId("")
        setCapital("10000")
        setAdapters({ exchange: "", stream: "", order: "", portfolio_storage: "" })
        setTraders([{ symbol: "BTCUSDT", interval: "H1", strategy: "", params: {} }])
        setSuccess(false)
        onSuccess?.()
      }, 1500)
    } catch (error) {
      console.error("Failed to create portfolio:", error)
      toast.error("Failed to create portfolio", {
        description: error instanceof Error ? error.message : 'Unknown error occurred'
      })
    } finally {
      setCreating(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
        {/* Portfolio Info */}
        <div className="space-y-4">
          <div>
            <Label htmlFor="portfolio-name">Portfolio Name</Label>
            <Input
              id="portfolio-name"
              value={portfolioName}
              onChange={(e) => setPortfolioName(e.target.value)}
              placeholder="My Trading Portfolio"
            />
          </div>
          <div>
            <Label htmlFor="portfolio-id">Portfolio ID</Label>
            <Input
              id="portfolio-id"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              placeholder="portfolio_1"
            />
          </div>
          <div>
            <Label htmlFor="capital">Initial Capital</Label>
            <Input
              id="capital"
              type="number"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              onBlur={(e) => {
                const numValue = parseFloat(e.target.value)
                if (isNaN(numValue) || numValue < 0) {
                  setCapital("10000")
                } else {
                  setCapital(numValue.toString())
                }
              }}
              min={0}
              step={100}
            />
          </div>
        </div>

        {/* Adapters Configuration - Hidden for now, always uses defaults */}
        {/* 
        <div className="space-y-4">
          <Label>Adapters (Optional - uses defaults if not specified)</Label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="exchange-adapter">Exchange Adapter</Label>
              <Input
                id="exchange-adapter"
                value={adapters.exchange}
                onChange={(e) => setAdapters({ ...adapters, exchange: e.target.value })}
                placeholder="binance (default)"
              />
            </div>
            <div>
              <Label htmlFor="stream-adapter">Stream Adapter</Label>
              <Input
                id="stream-adapter"
                value={adapters.stream}
                onChange={(e) => setAdapters({ ...adapters, stream: e.target.value })}
                placeholder="binance_stream (default)"
              />
            </div>
            <div>
              <Label htmlFor="order-adapter">Order Adapter</Label>
              <Input
                id="order-adapter"
                value={adapters.order}
                onChange={(e) => setAdapters({ ...adapters, order: e.target.value })}
                placeholder="binance_order (default)"
              />
            </div>
            <div>
              <Label htmlFor="portfolio-storage-adapter">Portfolio Storage</Label>
              <Input
                id="portfolio-storage-adapter"
                value={adapters.portfolio_storage}
                onChange={(e) => setAdapters({ ...adapters, portfolio_storage: e.target.value })}
                placeholder="postgres (default)"
              />
            </div>
          </div>
        </div>
        */}

        {/* Traders */}
        <div className="space-y-4 relative">
          <div className="flex items-center justify-between">
            <Label>Traders</Label>
            <Button onClick={addTrader} size="sm" variant="outline">
              <Plus className="h-4 w-4 mr-1" />
              Add Trader
            </Button>
          </div>

          {traders.map((trader, index) => (
            <Card key={index} className="p-4 space-y-4 relative" style={{ isolation: 'isolate' }}>
              <div className="flex items-center justify-between">
                <h4 className="font-medium">Trader {index + 1}</h4>
                {traders.length > 1 && (
                  <Button
                    onClick={() => removeTrader(index)}
                    size="sm"
                    variant="ghost"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Symbol</Label>
                  <Select
                    value={trader.symbol}
                    onValueChange={(val) => {
                      const newTraders = [...traders]
                      newTraders[index].symbol = val
                      setTraders(newTraders)
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CRYPTO_PAIRS.map(pair => (
                        <SelectItem key={pair.symbol} value={pair.symbol}>
                          {pair.symbol}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Interval</Label>
                  <Select
                    value={trader.interval}
                    onValueChange={(val) => {
                      const newTraders = [...traders]
                      newTraders[index].interval = val
                      setTraders(newTraders)
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TIMEFRAME_LABELS).map(([key, label]) => (
                        <SelectItem key={key} value={key}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label>Strategy</Label>
                <Select
                  value={trader.strategy}
                  onValueChange={(val) => handleStrategyChange(index, val)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a strategy" />
                  </SelectTrigger>
                  <SelectContent>
                    {strategies.map(strategy => (
                      <SelectItem key={strategy.id} value={strategy.id}>
                        {strategy.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {trader.strategy && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {strategies.find(s => s.id === trader.strategy)?.description}
                  </p>
                )}
              </div>

              {/* Strategy Parameters */}
              {trader.strategy && strategyParamsCache[trader.strategy] && (
                <div className="space-y-3 pt-2 border-t">
                  <Label className="text-sm font-medium">Strategy Parameters</Label>
                  {strategyParamsCache[trader.strategy].map(param => (
                    <div key={param.name}>
                      <Label htmlFor={`${index}-${param.name}`} className="text-xs">
                        {param.label}
                        {param.required && <span className="text-red-500 ml-1">*</span>}
                      </Label>
                      {renderParamInput(index, param)}
                      {param.description && (
                        <p className="text-xs text-muted-foreground mt-1">{param.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={creating || success || !portfolioName || !portfolioId}
          className="w-full"
        >
          {creating ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Creating Portfolio...
            </>
          ) : success ? (
            <>
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Portfolio Created!
            </>
          ) : (
            "Create Portfolio"
          )}
        </Button>
    </div>
  )
}

