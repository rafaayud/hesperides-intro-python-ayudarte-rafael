"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loader2, TrendingUp, TrendingDown, Activity, Target, DollarSign, BarChart3, AlertCircle } from "lucide-react"
import { toast } from "sonner"
import { 
  fetchStrategies, 
  fetchStrategyParams, 
  runBacktest,
  type Strategy, 
  type StrategyParam,
  type BacktestResponse,
  type BacktestRequest
} from "@/lib/api"
import { CRYPTO_PAIRS, TIMEFRAME_LABELS } from "@/lib/trading-data"
import { createChart, type IChartApi, type ISeriesApi, type CandlestickData, type UTCTimestamp } from "lightweight-charts"

// Helper para convertir UTC timestamp a timestamp local
function utcToLocal(utcTimestamp: number): number {
  const offsetSeconds = new Date().getTimezoneOffset() * 60
  return utcTimestamp - offsetSeconds
}

export function BacktestPanel() {
  // Form state
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [strategyParamsCache, setStrategyParamsCache] = useState<Record<string, StrategyParam[]>>({})
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  
  const [symbol, setSymbol] = useState("BTCUSDT")
  const [interval, setInterval] = useState("H1")
  const [strategy, setStrategy] = useState("")
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({})
  const [initialCapital, setInitialCapital] = useState("10000")
  
  // Results
  const [result, setResult] = useState<BacktestResponse | null>(null)
  
  // Chart refs
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)

  useEffect(() => {
    loadStrategies()
    return () => {
      chartRef.current?.remove()
    }
  }, [])

  // Initialize chart when we have candles
  useEffect(() => {
    if (result?.candles && chartContainerRef.current) {
      initChart()
    }
  }, [result?.candles])

  const loadStrategies = async () => {
    try {
      const data = await fetchStrategies()
      // Hide candle_pattern strategy from backtest options
      const filtered = data.filter(s => s.id !== "candle_pattern")
      setStrategies(filtered)
    } catch (error) {
      console.error("Failed to load strategies:", error)
      toast.error("Failed to load strategies")
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

  const handleStrategyChange = async (strategyName: string) => {
    setStrategy(strategyName)
    setStrategyParams({})
    
    const params = await loadStrategyParams(strategyName)
    const defaults: Record<string, any> = {}
    params.forEach(param => {
      if (param.default !== undefined) {
        defaults[param.name] = param.default
      }
    })
    setStrategyParams(defaults)
  }

  const handleParamChange = (paramName: string, value: any) => {
    setStrategyParams(prev => ({ ...prev, [paramName]: value }))
  }

  const initChart = () => {
    if (!chartContainerRef.current || !result?.candles) return
    
    // Remove existing chart
    chartRef.current?.remove()
    
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
    })
    
    chartRef.current = chart
    
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#16c784',
      downColor: '#ea3943',
      borderUpColor: '#16c784',
      borderDownColor: '#ea3943',
      wickUpColor: '#16c784',
      wickDownColor: '#ea3943',
    })
    
    candleSeriesRef.current = candleSeries
    
    // Set candle data (convert UTC to local time)
    const candleData: CandlestickData[] = result.candles.map(c => ({
      time: utcToLocal(c.time) as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }))
    
    candleSeries.setData(candleData)
    
    // Set trade markers if available (also convert to local time)
    if (result.trades && result.trades.length > 0) {
      const markers = result.trades.flatMap(trade => {
        const entryTimeUtc = typeof trade.entry_time === 'string' 
          ? Math.floor(new Date(trade.entry_time).getTime() / 1000)
          : trade.entry_time
        const exitTimeUtc = typeof trade.exit_time === 'string'
          ? Math.floor(new Date(trade.exit_time).getTime() / 1000)
          : trade.exit_time
        
        return [
          {
            time: utcToLocal(entryTimeUtc) as UTCTimestamp,
            position: 'belowBar' as const,
            color: '#16c784',
            shape: 'arrowUp' as const,
            text: 'BUY',
            size: 1,
          },
          {
            time: utcToLocal(exitTimeUtc) as UTCTimestamp,
            position: 'aboveBar' as const,
            color: '#ea3943',
            shape: 'arrowDown' as const,
            text: 'SELL',
            size: 1,
          }
        ]
      })
      
      candleSeries.setMarkers(markers)
    }
    
    chart.timeScale().fitContent()
    
    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }

  const handleRunBacktest = async () => {
    if (!strategy) {
      toast.error("Please select a strategy")
      return
    }
    
    const capital = parseFloat(initialCapital)
    if (isNaN(capital) || capital <= 0) {
      toast.error("Invalid initial capital")
      return
    }
    
    setRunning(true)
    setResult(null)
    
    try {
      const request: BacktestRequest = {
        symbol,
        interval: TIMEFRAME_LABELS[interval],  // Convert "H1" -> "1h"
        strategy,
        strategy_params: Object.keys(strategyParams).length > 0 ? strategyParams : undefined,
        initial_capital: capital,
      }
      
      const response = await runBacktest(request)
      setResult(response)
      
      toast.success("Backtest completed!", {
        description: `${response.total_trades} trades executed`
      })
    } catch (error) {
      console.error("Backtest failed:", error)
      toast.error("Backtest failed", {
        description: error instanceof Error ? error.message : 'Unknown error'
      })
    } finally {
      setRunning(false)
    }
  }

  const renderParamInput = (param: StrategyParam) => {
    const value = strategyParams[param.name] ?? param.default

    switch (param.type) {
      case 'number':
        return (
          <Input
            type="number"
            value={value ?? ''}
            onChange={(e) => {
              const val = e.target.value
              handleParamChange(param.name, val === '' ? '' : parseFloat(val))
            }}
            onBlur={(e) => {
              // Restore default if empty on blur
              if (e.target.value === '' || isNaN(parseFloat(e.target.value))) {
                handleParamChange(param.name, param.default)
              }
            }}
            min={param.min}
            max={param.max}
            step={param.step || 1}
            placeholder={param.default?.toString()}
            className="h-8"
          />
        )
      case 'select':
        return (
          <Select
            value={value || param.default}
            onValueChange={(val) => handleParamChange(param.name, val)}
          >
            <SelectTrigger className="h-8">
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
      case 'readonly':
        return (
          <div className="h-8 px-3 py-1.5 rounded-md border bg-muted/50 text-sm text-muted-foreground flex items-center">
            {param.default}
          </div>
        )
      default:
        return (
          <Input
            value={value || ''}
            onChange={(e) => handleParamChange(param.name, e.target.value)}
            placeholder={param.default?.toString()}
            className="h-8"
          />
        )
    }
  }

  const isProfitable = result && result.total_pnl >= 0

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
      {/* Configuration Panel */}
      <Card className="lg:col-span-1">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Backtest Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Symbol */}
          <div className="space-y-1.5">
            <Label className="text-xs">Symbol</Label>
            <Select value={symbol} onValueChange={setSymbol}>
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CRYPTO_PAIRS.slice(0, 20).map(pair => (
                  <SelectItem key={pair.symbol} value={pair.symbol}>
                    <span className="flex items-center gap-2">
                      <span>{pair.icon}</span>
                      <span>{pair.symbol}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Interval */}
          <div className="space-y-1.5">
            <Label className="text-xs">Interval</Label>
            <Select value={interval} onValueChange={setInterval}>
              <SelectTrigger className="h-9">
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
          
          {/* Strategy */}
          <div className="space-y-1.5">
            <Label className="text-xs">Strategy</Label>
            {loading ? (
              <Skeleton className="h-9 w-full" />
            ) : (
              <Select value={strategy} onValueChange={handleStrategyChange}>
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="Select strategy..." />
                </SelectTrigger>
                <SelectContent>
                  {strategies.map(s => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {strategy && strategies.find(s => s.id === strategy)?.description && (
              <p className="text-xs text-muted-foreground">
                {strategies.find(s => s.id === strategy)?.description}
              </p>
            )}
          </div>
          
          {/* Strategy Parameters */}
          {strategy && strategyParamsCache[strategy] && strategyParamsCache[strategy].length > 0 && (
            <div className="space-y-3 pt-2 border-t">
              <Label className="text-xs font-medium text-muted-foreground">Strategy Parameters</Label>
              {strategyParamsCache[strategy].map(param => (
                <div key={param.name} className="space-y-1">
                  <Label className="text-xs">{param.label}</Label>
                  {renderParamInput(param)}
                </div>
              ))}
            </div>
          )}
          
          {/* Initial Capital */}
          <div className="space-y-1.5 pt-2 border-t">
            <Label className="text-xs">Initial Capital ($)</Label>
            <Input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              min={100}
              step={1000}
              className="h-9"
            />
          </div>
          
          {/* Run Button */}
          <Button 
            onClick={handleRunBacktest} 
            disabled={running || !strategy}
            className="w-full"
          >
            {running ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Running Backtest...
              </>
            ) : (
              <>
                <Activity className="h-4 w-4 mr-2" />
                Run Backtest
              </>
            )}
          </Button>
        </CardContent>
      </Card>
      
      {/* Results Panel */}
      <div className="lg:col-span-2 space-y-4">
        {running ? (
          <Card>
            <CardContent className="py-8">
              <div className="flex flex-col items-center justify-center gap-4">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-muted-foreground">Running backtest...</p>
              </div>
            </CardContent>
          </Card>
        ) : result ? (
          <>
            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Card className={isProfitable ? "border-green-500/30" : "border-red-500/30"}>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    {isProfitable ? <TrendingUp className="h-3 w-3 text-green-500" /> : <TrendingDown className="h-3 w-3 text-red-500" />}
                    Total PnL
                  </div>
                  <div className={`text-xl font-bold ${isProfitable ? 'text-green-500' : 'text-red-500'}`}>
                    ${result.total_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className={`text-xs ${isProfitable ? 'text-green-500/80' : 'text-red-500/80'}`}>
                    {isProfitable ? '+' : ''}{result.total_pnl_percentage.toFixed(2)}%
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Target className="h-3 w-3" />
                    Win Rate
                  </div>
                  <div className="text-xl font-bold">
                    {result.win_rate.toFixed(1)}%
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Activity className="h-3 w-3" />
                    Total Trades
                  </div>
                  <div className="text-xl font-bold">
                    {result.total_trades}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Avg: ${result.avg_pnl_per_trade.toFixed(2)}/trade
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <DollarSign className="h-3 w-3" />
                    Capital
                  </div>
                  <div className="text-xl font-bold">
                    ${result.final_capital.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    From ${result.initial_capital.toLocaleString()}
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Chart */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center justify-between">
                  <span>Price Chart with Trades</span>
                  <Badge variant="outline" className="text-xs">
                    {result.symbol} • {result.interval}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.candles && result.candles.length > 0 ? (
                  <div ref={chartContainerRef} className="w-full h-[300px]" />
                ) : (
                  <div className="h-[200px] flex flex-col items-center justify-center gap-3 text-muted-foreground bg-secondary/30 rounded-lg">
                    <AlertCircle className="h-8 w-8" />
                    <div className="text-center">
                      <p className="font-medium">Chart data not available</p>
                      <p className="text-xs mt-1">
                        Backend needs to return 'candles' array for chart visualization
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
            
            {/* Trades Table */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Trade History</CardTitle>
              </CardHeader>
              <CardContent>
                {result.trades && result.trades.length > 0 ? (
                  <ScrollArea className="h-[250px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-xs">Entry Time</TableHead>
                          <TableHead className="text-xs">Exit Time</TableHead>
                          <TableHead className="text-xs text-right">Entry</TableHead>
                          <TableHead className="text-xs text-right">Exit</TableHead>
                          <TableHead className="text-xs text-right">PnL</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {result.trades.map((trade, i) => (
                          <TableRow key={i}>
                            <TableCell className="text-xs">
                              {typeof trade.entry_time === 'string' 
                                ? new Date(trade.entry_time).toLocaleString()
                                : new Date(trade.entry_time * 1000).toLocaleString()}
                            </TableCell>
                            <TableCell className="text-xs">
                              {typeof trade.exit_time === 'string'
                                ? new Date(trade.exit_time).toLocaleString()
                                : new Date(trade.exit_time * 1000).toLocaleString()}
                            </TableCell>
                            <TableCell className="text-xs text-right">
                              ${trade.entry_price.toLocaleString()}
                            </TableCell>
                            <TableCell className="text-xs text-right">
                              ${trade.exit_price.toLocaleString()}
                            </TableCell>
                            <TableCell className={`text-xs text-right font-medium ${trade.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                              <span className="text-muted-foreground ml-1">
                                ({trade.pnl_percentage >= 0 ? '+' : ''}{trade.pnl_percentage.toFixed(2)}%)
                              </span>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                ) : (
                  <div className="h-[150px] flex flex-col items-center justify-center gap-3 text-muted-foreground bg-secondary/30 rounded-lg">
                    <AlertCircle className="h-6 w-6" />
                    <div className="text-center">
                      <p className="font-medium text-sm">Trade details not available</p>
                      <p className="text-xs mt-1">
                        Backend needs to return 'trades' array for trade history
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        ) : (
          <Card className="h-[400px]">
            <CardContent className="h-full flex flex-col items-center justify-center gap-4 text-muted-foreground">
              <BarChart3 className="h-12 w-12 opacity-30" />
              <div className="text-center">
                <p className="font-medium">No backtest results yet</p>
                <p className="text-sm mt-1">
                  Configure parameters and run a backtest to see results
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

