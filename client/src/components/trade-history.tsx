import type { Trade } from "@/lib/trading-data"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ArrowUpCircle, ArrowDownCircle } from "lucide-react"

interface TradeHistoryProps {
  trades: Trade[]
}

export function TradeHistory({ trades }: TradeHistoryProps) {
  if (trades.length === 0) {
    return (
      <Card className="bg-card border-border h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Trade History</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-32 text-muted-foreground text-sm">
          No trades yet
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-card border-border h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">Trade History</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[200px]">
          <div className="space-y-1 p-4 pt-0">
            {trades
              .slice()
              .reverse()
              .map((trade) => (
                <div
                  key={trade.id}
                  className="flex items-center justify-between py-2 border-b border-border last:border-0"
                >
                  <div className="flex items-center gap-2">
                    {trade.type === "buy" ? (
                      <ArrowUpCircle className="h-4 w-4 text-profit" />
                    ) : (
                      <ArrowDownCircle className="h-4 w-4 text-loss" />
                    )}
                    <div>
                      <div className="text-sm font-medium capitalize">{trade.type}</div>
                      <div className="text-xs text-muted-foreground">{new Date(trade.time).toLocaleTimeString()}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-mono">${trade.price.toFixed(2)}</div>
                    {trade.pnl !== undefined && (
                      <div className={`text-xs font-mono ${trade.pnl >= 0 ? "text-profit" : "text-loss"}`}>
                        {trade.pnl >= 0 ? "+" : ""}
                        {trade.pnl.toFixed(2)}%
                      </div>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
