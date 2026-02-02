"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { 
  RefreshCw, 
  Play, 
  Square, 
  ChevronDown,
  ChevronUp,
  Briefcase,
  TrendingUp,
  Users,
  DollarSign,
  Trash2,
  Loader2,
  Plus
} from "lucide-react"
import { toast } from "sonner"
import { 
  listPortfolios, 
  getTradingStatus, 
  startTrading, 
  stopTrading,
  getPortfolioTraders,
  getPortfolioTrades,
  deletePortfolio,
  type Portfolio, 
  type TradingStatus,
  type Trader,
  type Trade
} from "@/lib/api"
import { PortfolioDetail } from "@/components/portfolio/PortfolioDetail"
import { CreatePortfolio } from "@/components/create-portfolio"
import type { ChartConfig } from "@/components/layout/MainLayout"

interface PortfoliosViewProps {
  onTraderSelect: (config: ChartConfig) => void
}

interface PortfolioWithStatus extends Portfolio {
  status?: TradingStatus
  traders?: Trader[]
  trades?: Trade[]
}

export function PortfoliosView({ onTraderSelect }: PortfoliosViewProps) {
  const [portfolios, setPortfolios] = useState<PortfolioWithStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedPortfolio, setSelectedPortfolio] = useState<PortfolioWithStatus | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const hasAutoSelected = useRef(false)

  const selectPortfolioDetails = useCallback(async (portfolio: PortfolioWithStatus) => {
    try {
      const tradersResult = await getPortfolioTraders(portfolio.id)
      const tradesResult = await getPortfolioTrades(portfolio.id)
      
      setSelectedPortfolio({
        ...portfolio,
        traders: tradersResult.traders,
        trades: tradesResult.trades
      })
    } catch (error) {
      toast.error("Error loading portfolio details", {
        description: error instanceof Error ? error.message : "Unknown error"
      })
      setSelectedPortfolio(portfolio)
    }
  }, [])

  const loadPortfolios = useCallback(async () => {
    try {
      setRefreshing(true)
      const data = await listPortfolios()
      
      // Fetch status for each portfolio
      const portfoliosWithStatus = await Promise.all(
        data.map(async (portfolio) => {
          try {
            const status = await getTradingStatus(portfolio.id)
            return { ...portfolio, status }
          } catch {
            return portfolio
          }
        })
      )
      
      setPortfolios(portfoliosWithStatus)
      
      // Auto-select first portfolio only once
      if (portfoliosWithStatus.length > 0 && !hasAutoSelected.current) {
        hasAutoSelected.current = true
        selectPortfolioDetails(portfoliosWithStatus[0])
      }
    } catch (error) {
      toast.error("Error loading portfolios", {
        description: error instanceof Error ? error.message : "Unknown error"
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [selectPortfolioDetails])

  useEffect(() => {
    loadPortfolios()
  }, [loadPortfolios])

  const handleSelectPortfolio = async (portfolio: PortfolioWithStatus) => {
    await selectPortfolioDetails(portfolio)
  }

  const handleStartTrading = async (portfolioId: string) => {
    try {
      setActionLoading(portfolioId)
      await startTrading(portfolioId)
      toast.success("Trading started", {
        description: `Portfolio ${portfolioId} is now trading`
      })
      await loadPortfolios()
    } catch (error) {
      toast.error("Error starting trading", {
        description: error instanceof Error ? error.message : "Unknown error"
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleStopTrading = async (portfolioId: string) => {
    try {
      setActionLoading(portfolioId)
      await stopTrading(portfolioId)
      toast.success("Trading stopped", {
        description: `Portfolio ${portfolioId} trading stopped`
      })
      await loadPortfolios()
    } catch (error) {
      toast.error("Error stopping trading", {
        description: error instanceof Error ? error.message : "Unknown error"
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDeletePortfolio = async (portfolioId: string) => {
    if (!confirm(`Are you sure you want to delete portfolio "${portfolioId}"?`)) {
      return
    }
    
    try {
      setActionLoading(portfolioId)
      await deletePortfolio(portfolioId)
      toast.success("Portfolio deleted", {
        description: `Portfolio ${portfolioId} has been deleted`
      })
      if (selectedPortfolio?.id === portfolioId) {
        setSelectedPortfolio(null)
      }
      await loadPortfolios()
    } catch (error) {
      toast.error("Error deleting portfolio", {
        description: error instanceof Error ? error.message : "Unknown error"
      })
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-1 space-y-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
          <div className="lg:col-span-3">
            <Skeleton className="h-96 w-full" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
      {/* Left sidebar - Portfolio list */}
      <div className="lg:col-span-1 space-y-3">
        {/* Header with create button */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-primary" />
            Portfolios
          </h2>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="h-8 w-8 p-0"
            >
              <Plus className={`h-4 w-4 transition-transform ${showCreateForm ? 'rotate-45' : ''}`} />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadPortfolios}
              disabled={refreshing}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
        
        {/* Create Portfolio Form - Collapsible */}
        {showCreateForm && (
          <Card className="border-primary/30 bg-primary/5">
            <CardHeader className="pb-2 pt-3 px-4">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Plus className="h-4 w-4" />
                New Portfolio
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <CreatePortfolio onSuccess={() => {
                setShowCreateForm(false)
                loadPortfolios()
              }} />
            </CardContent>
          </Card>
        )}
        
        {/* Portfolio List */}
        {portfolios.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-8 text-center">
              <Briefcase className="h-12 w-12 text-muted-foreground/50 mb-3" />
              <p className="text-muted-foreground">No portfolios yet</p>
              <Button 
                variant="link" 
                className="text-primary mt-2"
                onClick={() => setShowCreateForm(true)}
              >
                Create your first portfolio
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {portfolios.map((portfolio) => (
              <Card 
                key={portfolio.id}
                className={`cursor-pointer transition-all card-hover ${
                  selectedPortfolio?.id === portfolio.id 
                    ? 'border-primary bg-primary/5' 
                    : 'border-border/50'
                }`}
                onClick={() => handleSelectPortfolio(portfolio)}
              >
                <CardContent className="p-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium truncate text-sm">{portfolio.name}</h3>
                      <p className="text-[10px] text-muted-foreground truncate">{portfolio.id}</p>
                    </div>
                    <Badge 
                      variant="outline"
                      className={`text-[10px] ${portfolio.status?.is_running ? 'status-running' : 'status-stopped'}`}
                    >
                      {portfolio.status?.is_running ? 'Running' : 'Stopped'}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center gap-3 text-xs text-muted-foreground mb-2">
                    <div className="flex items-center gap-1">
                      <DollarSign className="h-3 w-3" />
                      <span>${Math.round(portfolio.initial_capital || 0).toLocaleString()}</span>
                    </div>
                    {portfolio.status?.traders_count !== undefined && (
                      <div className="flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        <span>{portfolio.status.traders_count}</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-1.5">
                    {portfolio.status?.is_running ? (
                      <Button
                        size="sm"
                        variant="destructive"
                        className="flex-1 h-7 text-xs"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleStopTrading(portfolio.id)
                        }}
                        disabled={actionLoading === portfolio.id}
                      >
                        {actionLoading === portfolio.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <>
                            <Square className="h-3 w-3 mr-1" />
                            Stop
                          </>
                        )}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        className="flex-1 h-7 text-xs"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleStartTrading(portfolio.id)
                        }}
                        disabled={actionLoading === portfolio.id}
                      >
                        {actionLoading === portfolio.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <>
                            <Play className="h-3 w-3 mr-1" />
                            Start
                          </>
                        )}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeletePortfolio(portfolio.id)
                      }}
                      disabled={actionLoading === portfolio.id}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
      
      {/* Main content - Portfolio Detail */}
      <div className="lg:col-span-3">
        {selectedPortfolio ? (
          <PortfolioDetail 
            portfolio={selectedPortfolio}
            onTraderSelect={onTraderSelect}
            onRefresh={() => handleSelectPortfolio(selectedPortfolio)}
          />
        ) : (
          <Card className="h-full min-h-[500px] border-dashed bg-gradient-to-br from-card to-secondary/20">
            <CardContent className="flex flex-col items-center justify-center h-full text-center">
              <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <TrendingUp className="h-10 w-10 text-primary/50" />
              </div>
              <h3 className="text-xl font-semibold text-foreground/80">
                Select a Portfolio
              </h3>
              <p className="text-sm text-muted-foreground mt-2 max-w-md">
                Choose a portfolio from the list to view detailed statistics, 
                manage traders, and analyze trade history
              </p>
              {portfolios.length === 0 && (
                <Button 
                  className="mt-6"
                  onClick={() => setShowCreateForm(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Portfolio
                </Button>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

