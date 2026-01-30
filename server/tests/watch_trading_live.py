"""
Script para iniciar trading mediante la API y monitorear su operación.
Simula las llamadas que hace el frontend para detectar errores reales.

USO:
1. Asegúrate de que el servidor FastAPI esté corriendo en otra terminal:
   cd server
   uvicorn apps.api.main:app --reload

2. Ejecuta este script:
   python tests/watch_trading_live.py --portfolio-id <ID>
   
Los logs del trading engine aparecerán en la terminal del servidor.
Este script solo hace llamadas HTTP y muestra las respuestas.
"""
import sys
import os
import time
import requests
import json
from datetime import datetime
from typing import Optional

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

API_BASE_URL = "http://127.0.0.1:8000/api"


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def list_portfolios() -> list:
    """List all portfolios"""
    try:
        response = requests.get(f"{API_BASE_URL}/portfolio/list")
        response.raise_for_status()
        data = response.json()
        return data.get("portfolios", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing portfolios: {e}")
        return []


def get_trading_status(portfolio_id: str) -> Optional[dict]:
    """Get trading status for a portfolio"""
    try:
        response = requests.get(f"{API_BASE_URL}/trading/status/{portfolio_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting status: {e}")
        return None


def start_trading(portfolio_id: str) -> bool:
    """Start trading for a portfolio"""
    try:
        response = requests.post(f"{API_BASE_URL}/trading/start/{portfolio_id}")
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "already_running":
            print(f"⚠️  Trading is already running for portfolio {portfolio_id}")
            return True
        elif result.get("status") == "started":
            print(f"✅ Trading started successfully!")
            return True
        else:
            print(f"❌ Unexpected response: {result}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error starting trading: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False


def stop_trading(portfolio_id: str) -> bool:
    """Stop trading for a portfolio"""
    try:
        response = requests.post(f"{API_BASE_URL}/trading/stop/{portfolio_id}")
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "stopped":
            print(f"✅ Trading stopped successfully!")
            return True
        elif result.get("status") == "not_running":
            print(f"⚠️  Trading was not running")
            return True
        else:
            print(f"❌ Unexpected response: {result}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error stopping trading: {e}")
        return False


def get_active_portfolio(portfolio_id: str) -> Optional[dict]:
    """Get active portfolio info (includes traders/strategies)"""
    try:
        response = requests.get(f"{API_BASE_URL}/portfolio/active/{portfolio_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting active portfolio: {e}")
        return None


def get_trades(portfolio_id: str, limit: int = 10) -> Optional[dict]:
    """Get trades for a portfolio"""
    try:
        response = requests.get(f"{API_BASE_URL}/portfolio/trades/{portfolio_id}?limit={limit}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting trades: {e}")
        return None


def get_chart_data(portfolio_id: str, trader_id: str, limit: int = 50) -> Optional[dict]:
    """Get chart data for a trader"""
    try:
        response = requests.get(f"{API_BASE_URL}/portfolio/chart/{portfolio_id}/{trader_id}?limit={limit}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting chart data: {e}")
        return None


def monitor_trading(portfolio_id: str, duration_minutes: int = 5, check_interval: int = 10):
    """Monitor trading for a specified duration"""
    
    print_section("TRADING MONITOR - API Calls")
    print(f"Portfolio ID: {portfolio_id}")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Check interval: {check_interval} seconds")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n⚠️  IMPORTANT: Make sure the FastAPI server is running in another terminal!")
    print("   The trading engine logs will appear in the server terminal.")
    print("\nPress Ctrl+C to stop monitoring (trading will continue running)")
    print("=" * 80)
    
    # Check if server is reachable
    try:
        # Try to list portfolios as a connectivity test
        response = requests.get(f"{API_BASE_URL}/portfolio/list", timeout=5)
        response.raise_for_status()
        print("✅ Server is reachable")
    except requests.exceptions.RequestException as e:
        print("❌ ERROR: Cannot reach the FastAPI server!")
        print(f"   Error: {e}")
        print("   Make sure it's running: uvicorn apps.api.main:app --reload")
        return
    
    # Check current status
    print_subsection("Initial Status Check")
    status = get_trading_status(portfolio_id)
    if not status:
        print("❌ Cannot get trading status. Exiting.")
        return
    
    is_running = status.get("is_running", False)
    print(f"Current status: {'Running' if is_running else 'Stopped'}")
    
    # Start trading if not running
    if not is_running:
        print_subsection("Starting Trading")
        if not start_trading(portfolio_id):
            print("❌ Failed to start trading. Exiting.")
            return
        time.sleep(3)  # Wait for initialization
    else:
        print("✓ Trading is already running")
    
    # Monitoring loop
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    check_count = 0
    last_trade_count = 0
    error_count = 0
    
    try:
        while time.time() < end_time:
            check_count += 1
            elapsed = int(time.time() - start_time)
            remaining = int(end_time - time.time())
            
            print_subsection(f"Check #{check_count} | Elapsed: {elapsed}s | Remaining: {remaining}s")
            
            # 1. Check status
            status = get_trading_status(portfolio_id)
            if not status:
                error_count += 1
                print("⚠️  Failed to get status")
                time.sleep(check_interval)
                continue
            
            is_running = status.get("is_running", False)
            if not is_running:
                print("⚠️  WARNING: Trading stopped unexpectedly!")
                break
            
            print(f"✓ Status: Running")
            print(f"  Details: {json.dumps(status, indent=2)}")
            
            # 2. Get active portfolio info
            active_portfolio = get_active_portfolio(portfolio_id)
            if active_portfolio:
                print(f"✓ Active Portfolio Info:")
                print(f"  Name: {active_portfolio.get('portfolio_name', 'N/A')}")
                print(f"  Capital: ${active_portfolio.get('portfolio_capital', 0)}")
                print(f"  Traders: {active_portfolio.get('portfolio_traders', 0)}")
            else:
                error_count += 1
                print("⚠️  Failed to get active portfolio (may not be running)")
            
            # 3. Get trades
            trades_data = get_trades(portfolio_id, limit=10)
            if trades_data:
                trades = trades_data.get("trades", [])
                current_trade_count = len(trades)
                
                if current_trade_count > last_trade_count:
                    new_trades = current_trade_count - last_trade_count
                    print(f"✓ New Trades: +{new_trades} (Total: {current_trade_count})")
                    
                    # Show latest trades
                    for trade in trades[:new_trades]:
                        symbol = trade.get('symbol', 'N/A')
                        side = trade.get('side', 'N/A')
                        entry_price = trade.get('entry_price', 0)
                        exit_price = trade.get('exit_price', 0)
                        pnl = trade.get('pnl', 0)
                        pnl_pct = trade.get('pnl_percentage', 0)
                        winner = "✓" if trade.get('is_winner', False) else "✗"
                        
                        print(f"  {winner} {symbol} {side}: ${entry_price:.4f} → ${exit_price:.4f} | "
                              f"PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
                else:
                    print(f"✓ Trades: {current_trade_count} (no new trades)")
                
                last_trade_count = current_trade_count
            else:
                error_count += 1
                print("⚠️  Failed to get trades")
            
            # 4. Try to get chart data (this might fail if there are issues)
            # Get first trader from trades if available
            if trades_data and trades_data.get("trades"):
                first_trade = trades_data["trades"][0]
                trader_id = first_trade.get('trader_id')
                if trader_id:
                    chart_data = get_chart_data(portfolio_id, trader_id, limit=50)
                    if chart_data:
                        candles = chart_data.get('candles', [])
                        markers = chart_data.get('trade_markers', [])
                        print(f"✓ Chart Data: {len(candles)} candles, {len(markers)} trade markers")
                    else:
                        error_count += 1
                        print("⚠️  Failed to get chart data")
            elif active_portfolio and active_portfolio.get('portfolio_traders', 0) > 0:
                # If we have portfolio info but no trades, we could try to get traders
                # For now, skip chart data if no trades
                print("⏸️  Skipping chart data (no trades to determine trader)")
            
            # Wait for next check
            if time.time() < end_time:
                print(f"\n⏳ Waiting {check_interval} seconds until next check...")
                time.sleep(check_interval)
        
        print_section("MONITORING COMPLETE")
        print(f"Total checks: {check_count}")
        print(f"Errors encountered: {error_count}")
        print(f"Final trade count: {last_trade_count}")
        
        if error_count > 0:
            print(f"\n⚠️  WARNING: {error_count} errors were encountered!")
            print("   Check the API responses above for details.")
        else:
            print("\n✓ No errors detected in API calls!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring interrupted by user (Ctrl+C)")
    
    finally:
        print_section("Trading Status")
        status = get_trading_status(portfolio_id)
        if status:
            is_running = status.get("is_running", False)
            print(f"Trading is {'still running' if is_running else 'stopped'}")
            
            if is_running:
                print("\n⚠️  Trading is still running!")
                print("To stop it, use:")
                print(f"  POST {API_BASE_URL}/trading/stop/{portfolio_id}")
                print("\nOr run this script with --stop flag")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Monitor trading via API calls (simulates frontend behavior)"
    )
    parser.add_argument(
        "--portfolio-id",
        type=str,
        help="Portfolio ID to monitor (if not provided, will show list)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Duration in minutes (default: 5)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Check interval in seconds (default: 10)"
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop trading instead of monitoring"
    )
    
    args = parser.parse_args()
    
    # List portfolios if no ID provided
    if not args.portfolio_id:
        print_section("Available Portfolios")
        portfolios = list_portfolios()
        
        if not portfolios:
            print("❌ No portfolios found!")
            return
        
        for i, p in enumerate(portfolios, 1):
            print(f"  {i}. {p.get('name', 'N/A')} (ID: {p.get('id')}) - Capital: ${p.get('initial_capital', 0)}")
        
        print()
        choice = input(f"Select portfolio (1-{len(portfolios)}) or enter ID: ").strip()
        
        # Try as number first
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(portfolios):
                portfolio_id = portfolios[idx]["id"]
            else:
                print("❌ Invalid selection")
                return
        except ValueError:
            # Try as ID
            portfolio_id = None
            for p in portfolios:
                if p.get("id") == choice:
                    portfolio_id = choice
                    break
            
            if not portfolio_id:
                print("❌ Invalid selection")
                return
    else:
        portfolio_id = args.portfolio_id
    
    # Stop trading if requested
    if args.stop:
        print_section("Stopping Trading")
        stop_trading(portfolio_id)
        return
    
    # Monitor trading
    monitor_trading(portfolio_id, args.duration, args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

