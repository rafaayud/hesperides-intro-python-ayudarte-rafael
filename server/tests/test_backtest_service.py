from modules.trading.application.services.backtest_service import BacktestService
from modules.trading.domain.value_objects import Symbol, Interval, Candle_static, Signal, Side, Quantity, TradeStatus
from modules.trading.domain.entities import Candle, Position, Trade
from modules.trading.domain.aggregates.backtest_result import BacktestResult
from modules.trading.domain.strategies import MeanCross, Momentum
from modules.trading.infrastructure import PostgreAdapter
import asyncio
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from time import perf_counter
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_backtest_service() -> None:
    try:
        async with BacktestService(PostgreAdapter("postgresql://postgres:1234@localhost:5432/postgres")) as backtest_service:
            # get_candles only takes 2 parameters (symbol, interval), limit is calculated from interval.max_candles
            candles = await backtest_service.get_candles(Symbol("BTCUSDT"), Interval.H1)

            

   
            # Extract prices and timestamps for plotting

            
            prices = [float(candle.close.value) for candle in candles]
            timestamps = [candle.timestamp.timestamp for candle in candles]

            strategy = MeanCross(50, 10)

            result = backtest_service.test_strategy(strategy, candles, 100000)

            print(result)
            
            # Debug: Verify trade order
            logging.info(f"📋 Total trades: {len(result.trades)}")
            for i, trade in enumerate(result.trades):
                logging.info(f"  Trade {i+1}: Entry={trade.entry_time.timestamp} | Exit={trade.exit_time.timestamp} | "
                           f"Side={trade.side} | PnL=${float(trade.pnl.value):,.2f}")

            # Calculate moving averages for plotting
            fast_period = 10
            slow_period = 50
            fast_ma_values = []
            slow_ma_values = []
            fast_ma_timestamps = []
            slow_ma_timestamps = []
            
            # Calculate fast MA (starts after fast_period candles)
            for i in range(fast_period - 1, len(prices)):
                fast_ma = sum(prices[i - fast_period + 1:i + 1]) / fast_period
                fast_ma_values.append(fast_ma)
                fast_ma_timestamps.append(timestamps[i])
            
            # Calculate slow MA (starts after slow_period candles)
            for i in range(slow_period - 1, len(prices)):
                slow_ma = sum(prices[i - slow_period + 1:i + 1]) / slow_period
                slow_ma_values.append(slow_ma)
                slow_ma_timestamps.append(timestamps[i])

            # Create interactive plot with Plotly
            fig = go.Figure()
            
            # Plot price line
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=prices,
                mode='lines',
                name='Precio',
                line=dict(color='#1f77b4', width=2),
                hovertemplate='<b>Fecha:</b> %{x}<br>' +
                            '<b>Precio:</b> $%{y:,.2f}<br>' +
                            '<extra></extra>'
            ))
            
            # Plot fast moving average
            fig.add_trace(go.Scatter(
                x=fast_ma_timestamps,
                y=fast_ma_values,
                mode='lines',
                name=f'MA Rápida ({fast_period})',
                line=dict(color='orange', width=2, dash='dash'),
                hovertemplate='<b>MA Rápida</b><br>' +
                            '<b>Fecha:</b> %{x}<br>' +
                            '<b>Valor:</b> $%{y:,.2f}<br>' +
                            '<extra></extra>'
            ))
            
            # Plot slow moving average
            fig.add_trace(go.Scatter(
                x=slow_ma_timestamps,
                y=slow_ma_values,
                mode='lines',
                name=f'MA Lenta ({slow_period})',
                line=dict(color='purple', width=2, dash='dash'),
                hovertemplate='<b>MA Lenta</b><br>' +
                            '<b>Fecha:</b> %{x}<br>' +
                            '<b>Valor:</b> $%{y:,.2f}<br>' +
                            '<extra></extra>'
            ))
            
            # Mark each trade individually to ensure correct chronological order
            entry_times_all = []
            entry_prices_all = []
            exit_times_all = []
            exit_prices_all = []
            
            for i, trade in enumerate(result.trades):
                entry_time = trade.entry_time.timestamp
                entry_price = float(trade.entry_price.value)
                exit_time = trade.exit_time.timestamp
                exit_price = float(trade.exit_price.value)
                pnl = float(trade.pnl.value)
                pnl_color = 'green' if pnl >= 0 else 'red'
                
                # Verify entry comes before exit
                if entry_time > exit_time:
                    logging.warning(f"⚠️ Trade {i+1}: Entry time ({entry_time}) is after exit time ({exit_time})!")
                
                # Collect for separate markers
                entry_times_all.append(entry_time)
                entry_prices_all.append(entry_price)
                exit_times_all.append(exit_time)
                exit_prices_all.append(exit_price)
                
                # Draw line connecting entry to exit for each trade
                fig.add_trace(go.Scatter(
                    x=[entry_time, exit_time],
                    y=[entry_price, exit_price],
                    mode='lines',
                    name=f'Trade {i+1}',
                    line=dict(color=pnl_color, width=2, dash='dash'),
                    opacity=0.5,
                    showlegend=False,
                    hovertemplate=f'<b>Trade {i+1}</b><br>' +
                                f'Entrada: {entry_time}<br>' +
                                f'Salida: {exit_time}<br>' +
                                f'PnL: ${pnl:,.2f}<br>' +
                                '<extra></extra>'
                ))
            
            # Mark all entry points (BUY) - green triangles (in chronological order)
            if entry_times_all:
                fig.add_trace(go.Scatter(
                    x=entry_times_all,
                    y=entry_prices_all,
                    mode='markers',
                    name='Entrada (BUY)',
                    marker=dict(
                        symbol='triangle-up',
                        size=15,
                        color='green',
                        line=dict(width=2, color='darkgreen')
                    ),
                    hovertemplate='<b>ENTRADA (BUY)</b><br>' +
                                '<b>Fecha:</b> %{x}<br>' +
                                '<b>Precio:</b> $%{y:,.2f}<br>' +
                                '<extra></extra>'
                ))
            
            # Mark all exit points (SELL) - red triangles (in chronological order)
            if exit_times_all:
                fig.add_trace(go.Scatter(
                    x=exit_times_all,
                    y=exit_prices_all,
                    mode='markers',
                    name='Salida (SELL)',
                    marker=dict(
                        symbol='triangle-down',
                        size=15,
                        color='red',
                        line=dict(width=2, color='darkred')
                    ),
                    hovertemplate='<b>SALIDA (SELL)</b><br>' +
                                '<b>Fecha:</b> %{x}<br>' +
                                '<b>Precio:</b> $%{y:,.2f}<br>' +
                                '<extra></extra>'
                ))
            
            # Update layout
            fig.update_layout(
                title=dict(
                    text=f'Backtest: {result.strategy_name} - {result.symbol.symbol}<br>' +
                         f'<sub>Capital inicial: ${result.initial_capital:,.2f} | ' +
                         f'Capital final: ${result.final_capital:,.2f} | ' +
                         f'Trades: {len(result.trades)} | ' +
                         f'PnL Total: ${float(result.total_pnl.value):,.2f}</sub>',
                    x=0.5,
                    xanchor='center'
                ),
                xaxis=dict(
                    title='Fecha/Hora',
                    type='date',
                    showgrid=True,
                    gridcolor='lightgray'
                ),
                yaxis=dict(
                    title='Precio (USDT)',
                    showgrid=True,
                    gridcolor='lightgray'
                ),
                hovermode='x unified',
                template='plotly_white',
                height=700,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )
            
            # Add zoom and pan controls
            fig.update_xaxes(rangeslider_visible=False)  # Can enable for range selector
            
            logging.info("📊 Displaying interactive graph... (close the browser tab to continue)")
            logging.info("💡 Features: Zoom (mouse wheel), Pan (click & drag), Hover (info), Reset (double-click)")
            fig.show()  # Opens in browser - interactive with zoom, pan, hover!
            
            # Optional: Save as HTML file
            # fig.write_html('backtest_result.html')
            # logging.info("Graph saved to backtest_result.html")
            
            logging.info("✅ Graph closed, continuing...")
    except Exception as e:
        logging.error(f"Error in backtest: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    start_time = perf_counter()
    logging.info("🚀 Starting backtest...")
    asyncio.run(test_backtest_service())
    end_time = perf_counter()
    logging.info(f"⏱️  Time taken: {end_time - start_time:.2f} seconds")