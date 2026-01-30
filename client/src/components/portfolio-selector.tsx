"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Play, Square, RefreshCw, Loader2 } from "lucide-react"
import { toast } from "sonner"
import {
  listPortfolios,
  startTrading,
  stopTrading,
  getTradingStatus,
  getActivePortfolioSummary,
  getPortfolioTraders,
  getPortfolioTrades,
  type Portfolio,
  type TradingStatus,
  type ActivePortfolioSummary,
  type PortfolioTrader,
  type PortfolioTrade,
} from "@/lib/api"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"

interface PortfolioSelectorProps {
  onTraderSelect?: (payload: { symbol: string; interval: string }) => void
}

export function PortfolioSelector({ onTraderSelect }: PortfolioSelectorProps) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>("")
  const [tradingStatus, setTradingStatus] = useState<TradingStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)
  const [portfolioStatuses, setPortfolioStatuses] = useState<Record<string, TradingStatus>>({})

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogSummary, setDialogSummary] = useState<ActivePortfolioSummary | null>(null)
  const [dialogTraders, setDialogTraders] = useState<PortfolioTrader[]>([])
  const [selectedTrader, setSelectedTrader] = useState<PortfolioTrader | null>(null)
  const [traderTrades, setTraderTrades] = useState<PortfolioTrade[]>([])
  const [dialogLoading, setDialogLoading] = useState(false)

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
      // Actualizar estados de todos los portfolios
      await updatePortfolioStatuses(data)
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

  const openPortfolioDialog = async (portfolioId: string) => {
    try {
      setDialogLoading(true)
      setDialogOpen(true)

      const [summary, traders] = await Promise.all([
        getActivePortfolioSummary(portfolioId).catch(() => null),
        getPortfolioTraders(portfolioId),
      ])

      if (summary) {
        setDialogSummary(summary)
      } else {
        const fallback = portfolios.find((p) => p.id === portfolioId)
        if (fallback) {
          setDialogSummary({
            portfolio_id: fallback.id,
            portfolio_name: fallback.name,
            portfolio_capital: fallback.initial_capital,
            portfolio_traders: traders.length,
          })
        }
      }

      setDialogTraders(traders)

      if (traders.length > 0) {
        await handleSelectTrader(traders[0], portfolioId)
      } else {
        setSelectedTrader(null)
        setTraderTrades([])
      }
    } catch (error) {
      console.error("Error opening portfolio dialog:", error)
      toast.error("Error loading portfolio details", {
        description: error instanceof Error ? error.message : "Unknown error",
      })
    } finally {
      setDialogLoading(false)
    }
  }

  const handleSelectTrader = async (trader: PortfolioTrader, portfolioId?: string) => {
    try {
      setSelectedTrader(trader)

      const pid = portfolioId || selectedPortfolioId
      if (pid) {
        const trades = await getPortfolioTrades(pid, trader.id, 100)
        setTraderTrades(trades)
      }

      if (onTraderSelect) {
        const intervalMap: Record<string, string> = {
          "1m": "M1",
          "5m": "M5",
          "15m": "M15",
          "1h": "H1",
          "4h": "H4",
          "1d": "D1",
          "1w": "W1",
          "1mth": "MO1",
        }
        const rawInterval = String(trader.interval || "").toLowerCase()
        const timeframeKey = intervalMap[rawInterval] || rawInterval.toUpperCase() || "H1"

        onTraderSelect({ symbol: trader.symbol, interval: timeframeKey })
      }
    } catch (error) {
      console.error("Error loading trader trades:", error)
      toast.error("Error loading trader trades", {
        description: error instanceof Error ? error.message : "Unknown error",
      })
    }
  }

  const updatePortfolioStatuses = async (sourcePortfolios?: Portfolio[]) => {
    const list = sourcePortfolios ?? portfolios
    if (!list || list.length === 0) {
      setPortfolioStatuses({})
      return
    }

    try {
      const entries = await Promise.all(
        list.map(async (p) => {
          try {
            const status = await getTradingStatus(p.id)
            return [p.id, status] as const
          } catch (error) {
            console.error("Error checking status for portfolio", p.id, error)
            return null
          }
        })
      )

      const map: Record<string, TradingStatus> = {}
      for (const entry of entries) {
        if (!entry) continue
        const [id, status] = entry
        map[id] = status
      }
      setPortfolioStatuses(map)
    } catch (error) {
      console.error("Error updating running portfolios:", error)
    }
  }

  // Poll global running portfolios cada 10 segundos
  useEffect(() => {
    if (portfolios.length === 0) return

    updatePortfolioStatuses()
    const interval = setInterval(() => {
      updatePortfolioStatuses()
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

        {/* Lista de todos los portfolios */}
        {portfolios.length > 0 && (
          <div className="pt-3 border-t border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">
                Portfolios
              </span>
              <span className="text-xs text-muted-foreground">
                {portfolios.length}
              </span>
            </div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {portfolios.map((p) => {
                const status = portfolioStatuses[p.id]
                const isRunning = status?.is_running
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      setSelectedPortfolioId(p.id)
                      openPortfolioDialog(p.id)
                    }}
                    className="w-full text-left px-2 py-1.5 rounded-md border border-border/60 bg-muted/40 hover:bg-muted transition-colors flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="flex flex-col">
                      <span className="font-medium truncate">
                        {p.name || p.id}
                      </span>
                      <span className="text-[10px] text-muted-foreground truncate">
                        {p.id}
                      </span>
                    </div>
                    <Badge
                      variant={isRunning ? "default" : "secondary"}
                      className="text-[10px] px-2 py-0"
                    >
                      {isRunning ? "Running" : "Stopped"}
                    </Badge>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Portfolio details dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
            <DialogHeader>
              <DialogTitle>
                {dialogSummary?.portfolio_name || "Portfolio details"}
              </DialogTitle>
              {dialogSummary && (
                <DialogDescription>
                  ID: {dialogSummary.portfolio_id} • Traders: {dialogSummary.portfolio_traders}
                </DialogDescription>
              )}
            </DialogHeader>

            {dialogLoading && (
              <div className="py-6 text-sm text-muted-foreground">Loading portfolio details...</div>
            )}

            {!dialogLoading && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                {/* Traders list */}
                <div className="md:col-span-1 border border-border rounded-lg bg-muted/40">
                  <div className="px-3 py-2 border-b border-border flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">Traders</span>
                    <span className="text-xs text-muted-foreground">
                      {dialogTraders.length}
                    </span>
                  </div>
                  <ScrollArea className="h-64">
                    <div className="p-2 space-y-1">
                      {dialogTraders.map((trader) => (
                        <button
                          key={trader.id}
                          type="button"
                          onClick={() => handleSelectTrader(trader)}
                          className={`w-full text-left px-2 py-1.5 rounded-md text-xs border ${
                            selectedTrader?.id === trader.id
                              ? "border-primary bg-primary/10"
                              : "border-border/60 bg-background hover:bg-muted/60"
                          }`}
                        >
                          <div className="flex justify-between items-center gap-2">
                            <div className="flex flex-col min-w-0">
                              <span className="font-medium truncate">{trader.id}</span>
                              <span className="text-[10px] text-muted-foreground truncate">
                                {trader.symbol} • {trader.interval} • {trader.strategy}
                              </span>
                            </div>
                          </div>
                        </button>
                      ))}
                      {dialogTraders.length === 0 && (
                        <div className="text-xs text-muted-foreground px-1 py-2">
                          No traders found for this portfolio.
                        </div>
                      )}
                    </div>
                  </ScrollArea>
                </div>

                {/* Trades for selected trader */}
                <div className="md:col-span-2 border border-border rounded-lg bg-muted/40">
                  <div className="px-3 py-2 border-b border-border flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                      {selectedTrader ? `Trades for ${selectedTrader.id}` : "Trades"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {traderTrades.length}
                    </span>
                  </div>
                  <ScrollArea className="h-64">
                    <div className="p-3 space-y-2 text-xs">
                      {traderTrades.length === 0 && (
                        <div className="text-muted-foreground">No trades yet.</div>
                      )}
                      {traderTrades.map((t, idx) => (
                        <div
                          key={`${t.symbol}-${t.entry_time}-${idx}`}
                          className="border border-border rounded-md px-2 py-1.5 flex items-center justify-between gap-2 bg-background/60"
                        >
                          <div className="flex flex-col min-w-0">
                            <span className="font-medium">
                              {t.symbol} • {t.quantity?.toFixed ? t.quantity.toFixed(4) : t.quantity}
                            </span>
                            <span className="text-[10px] text-muted-foreground">
                              {t.entry_time} → {t.exit_time}
                            </span>
                          </div>
                          <div className="text-right">
                            <div className="font-mono text-xs">
                              {t.entry_price?.toFixed ? t.entry_price.toFixed(2) : t.entry_price} →{" "}
                              {t.exit_price?.toFixed ? t.exit_price.toFixed(2) : t.exit_price}
                            </div>
                            {typeof t.pnl === "number" && (
                              <div
                                className={`font-mono text-[10px] ${
                                  t.pnl >= 0 ? "text-green-500" : "text-red-500"
                                }`}
                              >
                                {t.pnl >= 0 ? "+" : ""}{t.pnl.toFixed(2)}{" "}
                                {typeof t.pnl_percentage === "number" &&
                                  `(${t.pnl_percentage >= 0 ? "+" : ""}${t.pnl_percentage.toFixed(2)}%)`}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
}

