"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Play, Square, RefreshCw, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { listPortfolios, startTrading, stopTrading, getTradingStatus, type Portfolio, type TradingStatus } from "@/lib/api"

export function PortfolioSelector() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>("")
  const [tradingStatus, setTradingStatus] = useState<TradingStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)

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
              <span className="font-medium">${selectedPortfolio.initial_capital.toLocaleString()}</span>
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
      </CardContent>
    </Card>
  )
}

