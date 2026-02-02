"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Play, Square, RefreshCw, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { listPortfolios, startTrading, stopTrading, getTradingStatus, type Portfolio, type TradingStatus } from "@/lib/api"

type RunningPortfolio = {
  id: string
  name: string
  status: TradingStatus
}

export function PortfolioSelector() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>("")
  const [tradingStatus, setTradingStatus] = useState<TradingStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)
  const [runningPortfolios, setRunningPortfolios] = useState<RunningPortfolio[]>([])

  useEffect(() => {
    loadPortfolios()
  }, [])

  useEffect(() => {
    if (selectedPortfolioId) {
      checkStatus()
      // Poll status every 5 seconds if trading is running
      const interval = setInterval(() => {
        if (tradingStatus?.is_running) {
          checkStatus()
        }
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [selectedPortfolioId, tradingStatus?.is_running])

  const loadPortfolios = async () => {
    try {
      setRefreshing(true)
      const data = await listPortfolios()
      setPortfolios(data)
      if (data.length > 0 && !selectedPortfolioId) {
        setSelectedPortfolioId(data[0].id)
      }
      // Actualizar lista de portfolios corriendo
      await updateRunningPortfolios(data)
    } catch (error) {
      toast.error("Error loading portfolios", {
        description: error instanceof Error ? error.message : "Unknown error"
      })
    } finally {
      setRefreshing(false)
    }
  }

  const checkStatus = async () => {
    if (!selectedPortfolioId) return
    
    try {
      setStatusLoading(true)
      const status = await getTradingStatus(selectedPortfolioId)
      setTradingStatus(status)
    } catch (error) {
      console.error("Error checking status:", error)
    } finally {
      setStatusLoading(false)
    }
  }

  const updateRunningPortfolios = async (sourcePortfolios?: Portfolio[]) => {
    const list = sourcePortfolios ?? portfolios
    if (!list || list.length === 0) {
      setRunningPortfolios([])
      return
    }

    try {
      const results = await Promise.all(
        list.map(async (p) => {
          try {
            const status = await getTradingStatus(p.id)
            if (status.is_running) {
              return { id: p.id, name: p.name, status }
            }
            return null
          } catch (error) {
            console.error("Error checking status for portfolio", p.id, error)
            return null
          }
        })
      )

      const filtered = results.filter((p): p is RunningPortfolio => p !== null)
      setRunningPortfolios(filtered)
    } catch (error) {
      console.error("Error updating running portfolios:", error)
    }
  }

  // Poll global running portfolios cada 10 segundos
  useEffect(() => {
    if (portfolios.length === 0) return

    updateRunningPortfolios()
    const interval = setInterval(() => {
      updateRunningPortfolios()
    }, 10000)

    return () => clearInterval(interval)
  }, [portfolios])

  const handleStart = async () => {
    if (!selectedPortfolioId) {
      toast.error("Please select a portfolio")
      return
    }

    try {
      setLoading(true)
      await startTrading(selectedPortfolioId)
      toast.success("Trading started", {
        description: `Portfolio ${selectedPortfolioId} is now trading`
      })
      await checkStatus()
    } catch (error) {
      toast.error("Error starting trading", {
        description: error instanceof Error ? error.message : "Unknown error"
      })
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
    if (!selectedPortfolioId) {
      toast.error("Please select a portfolio")
      return
    }

    try {
      setLoading(true)
      await stopTrading(selectedPortfolioId)
      toast.success("Trading stopped", {
        description: `Portfolio ${selectedPortfolioId} trading stopped`
      })
      await checkStatus()
    } catch (error) {
      toast.error("Error stopping trading", {
        description: error instanceof Error ? error.message : "Unknown error"
      })
    } finally {
      setLoading(false)
    }
  }

  const selectedPortfolio = portfolios.find(p => p.id === selectedPortfolioId)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Portfolio Trading</CardTitle>
            <CardDescription>Select and manage trading portfolios</CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={loadPortfolios}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Portfolio Selector */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Select Portfolio</label>
          <Select
            value={selectedPortfolioId}
            onValueChange={setSelectedPortfolioId}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a portfolio" />
            </SelectTrigger>
            <SelectContent>
              {portfolios.length === 0 ? (
                <SelectItem value="none" disabled>No portfolios available</SelectItem>
              ) : (
                portfolios.map((portfolio) => (
                  <SelectItem key={portfolio.id} value={portfolio.id}>
                    {portfolio.name} ({portfolio.id})
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        {/* Portfolio Info */}
        {selectedPortfolio && (
          <div className="space-y-2 p-3 bg-muted rounded-md">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Capital:</span>
              <span className="font-medium">${Math.round(selectedPortfolio.initial_capital).toLocaleString()}</span>
            </div>
            {tradingStatus && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status:</span>
                <Badge variant={tradingStatus.is_running ? "default" : "secondary"}>
                  {tradingStatus.is_running ? "Running" : "Stopped"}
                </Badge>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            onClick={handleStart}
            disabled={loading || !selectedPortfolioId || tradingStatus?.is_running}
            className="flex-1"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Start
          </Button>
          <Button
            onClick={handleStop}
            disabled={loading || !selectedPortfolioId || !tradingStatus?.is_running}
            variant="destructive"
            className="flex-1"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Square className="h-4 w-4 mr-2" />
            )}
            Stop
          </Button>
        </div>

        {statusLoading && (
          <div className="text-xs text-muted-foreground text-center">
            Checking status...
          </div>
        )}

        {/* Running portfolios list */}
        {runningPortfolios.length > 0 && (
          <div className="pt-3 border-t border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">
                Running portfolios
              </span>
              <span className="text-xs text-muted-foreground">
                {runningPortfolios.length}
              </span>
            </div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {runningPortfolios.map((rp) => (
                <button
                  key={rp.id}
                  type="button"
                  onClick={() => setSelectedPortfolioId(rp.id)}
                  className="w-full text-left px-2 py-1.5 rounded-md border border-border/60 bg-muted/40 hover:bg-muted transition-colors flex items-center justify-between gap-2 text-xs"
                >
                  <div className="flex flex-col">
                    <span className="font-medium truncate">
                      {rp.name || rp.id}
                    </span>
                    <span className="text-[10px] text-muted-foreground truncate">
                      {rp.id}
                    </span>
                  </div>
                  <Badge variant="default" className="text-[10px] px-2 py-0">
                    Running
                  </Badge>
                </button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

