"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { 
  TrendingUp, 
  TrendingDown, 
  Briefcase, 
  DollarSign,
  Activity,
  Target,
  Trophy,
  AlertTriangle
} from "lucide-react"
import { getGlobalStats, type GlobalStats as GlobalStatsType } from "@/lib/api"

export function GlobalStats() {
  const [stats, setStats] = useState<GlobalStatsType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStats()
    // Refresh every 30 seconds
    const interval = setInterval(loadStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadStats = async () => {
    try {
      const data = await getGlobalStats()
      setStats(data)
      setError(null)
    } catch (err) {
      // Use mock data if endpoint not available yet
      setStats({
        total_portfolios: 0,
        running_portfolios: 0,
        total_capital: 0,
        total_pnl: 0,
        total_pnl_percentage: 0,
        total_trades: 0,
        win_rate: 0
      })
      setError("Stats endpoint not available")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </CardContent>
      </Card>
    )
  }

  const isProfitable = (stats?.total_pnl || 0) >= 0

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Global Stats
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Capital & PnL Row */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1.5 text-muted-foreground text-[10px] uppercase tracking-wide mb-1">
              <DollarSign className="h-3 w-3" />
              Capital
            </div>
            <div className="text-lg font-bold font-mono">
              ${Math.round(stats?.total_capital || 0).toLocaleString()}
            </div>
          </div>
          
          <div className={`rounded-lg p-3 ${isProfitable ? 'bg-profit/10' : 'bg-loss/10'}`}>
            <div className="flex items-center gap-1.5 text-muted-foreground text-[10px] uppercase tracking-wide mb-1">
              {isProfitable ? (
                <TrendingUp className="h-3 w-3 text-profit" />
              ) : (
                <TrendingDown className="h-3 w-3 text-loss" />
              )}
              PnL
            </div>
            <div className={`text-lg font-bold font-mono ${isProfitable ? 'text-profit' : 'text-loss'}`}>
              {isProfitable ? '+' : ''}{(stats?.total_pnl || 0).toFixed(2)}
            </div>
          </div>
        </div>

        {/* Portfolios & Win Rate Row */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1.5 text-muted-foreground text-[10px] uppercase tracking-wide mb-1">
              <Briefcase className="h-3 w-3" />
              Portfolios
            </div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold">{stats?.total_portfolios || 0}</span>
              <Badge variant="outline" className="status-running text-[10px] px-1.5 py-0">
                {stats?.running_portfolios || 0} active
              </Badge>
            </div>
          </div>
          
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1.5 text-muted-foreground text-[10px] uppercase tracking-wide mb-1">
              <Target className="h-3 w-3" />
              Win Rate
            </div>
            <div className="flex items-baseline gap-1">
              <span className={`text-lg font-bold ${(stats?.win_rate || 0) >= 50 ? 'text-profit' : 'text-loss'}`}>
                {(stats?.win_rate || 0).toFixed(1)}%
              </span>
              <span className="text-xs text-muted-foreground">
                ({stats?.total_trades || 0})
              </span>
            </div>
          </div>
        </div>

        {/* Best/Worst portfolios */}
        {stats?.best_portfolio?.id && stats?.worst_portfolio?.id && 
         stats.best_portfolio.id !== stats.worst_portfolio.id && (
          <div className="space-y-2 pt-2 border-t border-border/50">
            <div className="flex items-center justify-between p-2 rounded-lg bg-profit/5 border border-profit/20">
              <div className="flex items-center gap-2">
                <Trophy className="h-3.5 w-3.5 text-profit" />
                <span className="text-xs truncate max-w-[100px]">{stats.best_portfolio.id}</span>
              </div>
              <span className="text-profit font-mono text-sm font-semibold">
                +{(stats.best_portfolio.pnl ?? 0).toFixed(2)}
              </span>
            </div>
            
            <div className="flex items-center justify-between p-2 rounded-lg bg-loss/5 border border-loss/20">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-loss" />
                <span className="text-xs truncate max-w-[100px]">{stats.worst_portfolio.id}</span>
              </div>
              <span className="text-loss font-mono text-sm font-semibold">
                {(stats.worst_portfolio.pnl ?? 0).toFixed(2)}
              </span>
            </div>
          </div>
        )}

        {error && (
          <div className="text-[10px] text-center text-muted-foreground pt-1">
            {error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

