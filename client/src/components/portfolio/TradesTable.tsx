"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { TrendingUp, TrendingDown, History, Loader2 } from "lucide-react"
import type { Trade } from "@/lib/api"
import { formatUtcDateTime } from "@/lib/chart-time"

interface TradesTableProps {
  trades: Trade[]
  loading?: boolean
}

function formatPrice(price: number): string {
  if (price >= 1000) {
    return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return price.toFixed(4)
}

export function TradesTable({ trades, loading }: TradesTableProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        Loading trades...
      </div>
    )
  }
  
  if (trades.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <History className="h-12 w-12 mx-auto mb-3 opacity-30" />
        <p>No trades yet</p>
        <p className="text-sm mt-1">Trades will appear here when executed</p>
      </div>
    )
  }

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[120px]">Time (UTC)</TableHead>
            <TableHead className="w-[100px]">Symbol</TableHead>
            <TableHead className="text-right w-[100px]">Entry</TableHead>
            <TableHead className="text-right w-[100px]">Exit</TableHead>
            <TableHead className="text-right w-[90px]">Qty</TableHead>
            <TableHead className="text-right w-[100px]">PnL</TableHead>
            <TableHead className="text-right w-[80px]">%</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade, index) => {
            const pnl = trade.pnl || 0
            const pnlPct = trade.pnl_percentage || 0
            const isProfit = pnl >= 0
            
            return (
              <TableRow key={trade.id || index} className="group hover:bg-muted/30">
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {formatUtcDateTime(trade.exit_time || trade.entry_time)}
                </TableCell>
                <TableCell className="font-medium">
                  <span className="text-sm">{trade.symbol.replace('USDT', '')}</span>
                  <span className="text-muted-foreground text-xs">/USDT</span>
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  ${formatPrice(trade.entry_price)}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  ${formatPrice(trade.exit_price)}
                </TableCell>
                <TableCell className="text-right font-mono text-sm text-muted-foreground">
                  {trade.quantity?.toFixed(4) || '-'}
                </TableCell>
                <TableCell className="text-right">
                  <div className={`flex items-center justify-end gap-1 font-mono font-medium ${isProfit ? 'text-profit' : 'text-loss'}`}>
                    {isProfit ? (
                      <TrendingUp className="h-3.5 w-3.5" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5" />
                    )}
                    {isProfit ? '+' : ''}{pnl.toFixed(2)}
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <span className={`font-mono text-sm ${isProfit ? 'text-profit' : 'text-loss'}`}>
                    {isProfit ? '+' : ''}{pnlPct.toFixed(2)}%
                  </span>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

