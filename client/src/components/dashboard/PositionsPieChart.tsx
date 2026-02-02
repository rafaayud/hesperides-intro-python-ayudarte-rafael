"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts"
import { PieChartIcon, TrendingUp } from "lucide-react"
import { getOpenPositions, type OpenPositionsResponse } from "@/lib/api"

// Colors for different symbols
const COLORS = [
  '#3861fb', // primary blue
  '#16c784', // profit green
  '#f0b90b', // warning yellow
  '#ea3943', // loss red
  '#8b5cf6', // purple
  '#06b6d4', // cyan
  '#f97316', // orange
  '#ec4899', // pink
]

export function PositionsPieChart() {
  const [data, setData] = useState<OpenPositionsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPositions()
    // Refresh every 30 seconds
    const interval = setInterval(loadPositions, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadPositions = async () => {
    try {
      const response = await getOpenPositions()
      setData(response)
      setError(null)
    } catch (err) {
      // Use mock data if endpoint not available yet
      setData({
        positions: [],
        total_value: 0,
        by_symbol: {}
      })
      setError("Positions endpoint not available")
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
        <CardContent>
          <Skeleton className="h-48 w-full" />
        </CardContent>
      </Card>
    )
  }

  const chartData = Object.entries(data?.by_symbol || {}).map(([symbol, value], index) => ({
    name: symbol.replace('USDT', ''),
    value: value,
    fullName: symbol,
    color: COLORS[index % COLORS.length]
  }))

  const hasPositions = chartData.length > 0

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <PieChartIcon className="h-4 w-4 text-primary" />
              Open Positions
            </CardTitle>
            <CardDescription>Distribution by asset</CardDescription>
          </div>
          {hasPositions && (
            <div className="text-right">
              <div className="text-xs text-muted-foreground">Total Value</div>
              <div className="font-mono font-semibold text-lg">
                ${(data?.total_value || 0).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {hasPositions ? (
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload
                      return (
                        <div className="bg-popover border border-border rounded-lg p-2 shadow-lg">
                          <div className="font-medium">{data.fullName}</div>
                          <div className="text-sm text-muted-foreground">
                            ${data.value.toLocaleString()}
                          </div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  content={({ payload }) => (
                    <div className="flex flex-wrap justify-center gap-3 mt-2">
                      {payload?.map((entry: any, index: number) => (
                        <div key={index} className="flex items-center gap-1.5 text-xs">
                          <div 
                            className="h-2.5 w-2.5 rounded-full" 
                            style={{ backgroundColor: entry.color }}
                          />
                          <span className="text-muted-foreground">{entry.value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-48 flex flex-col items-center justify-center text-muted-foreground">
            <TrendingUp className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm">No open positions</p>
            <p className="text-xs mt-1">Start trading to see positions here</p>
          </div>
        )}

        {/* Position list */}
        {hasPositions && data?.positions && data.positions.length > 0 && (
          <div className="mt-4 space-y-2 max-h-32 overflow-y-auto">
            {data.positions.slice(0, 5).map((pos, index) => (
              <div 
                key={`${pos.portfolio_id}-${pos.symbol}-${index}`}
                className="flex items-center justify-between text-xs p-2 rounded-lg bg-secondary/30"
              >
                <div className="flex items-center gap-2">
                  <div 
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="font-medium">{pos.symbol}</span>
                  <span className="text-muted-foreground">@ ${(pos.entry_price || 0).toFixed(2)}</span>
                </div>
                <div className="font-mono">
                  ${(pos.current_value || 0).toLocaleString()}
                </div>
              </div>
            ))}
            {data.positions.length > 5 && (
              <div className="text-center text-xs text-muted-foreground">
                +{data.positions.length - 5} more positions
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="text-xs text-center text-muted-foreground mt-2">
            {error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

