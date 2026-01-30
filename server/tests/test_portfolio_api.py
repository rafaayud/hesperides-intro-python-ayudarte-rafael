"""
Test script using FastAPI TestClient to test portfolio API endpoints.
This simulates HTTP requests without needing a running server.
"""
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.config import get_settings
from apps.api.dependencies import setup_registry
from apps.api.service_factory import ServiceFactory
from apps.api.trading_state import TradingStateManager
from apps.api.registry import AdapterRegistry
import json
import warnings

# Suppress noisy DeprecationWarnings from third-party libs (Binance / websockets / aiohttp)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="binance.ws.websocket_api",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="websockets.legacy",
)
from apps.api.registry import AdapterRegistry


@pytest.fixture
def client():
    """Create a test client for the FastAPI app with initialized state"""
    # Initialize app state (simulating lifespan startup)    
    settings = get_settings()
    setup_registry(settings)
    
    app.state.settings = settings
    app.state.services = ServiceFactory(AdapterRegistry, settings)
    app.state.trading_state = TradingStateManager()
    
    # Create TestClient
    test_client = TestClient(app)
    
    yield test_client
    
    # Cleanup (simulating lifespan shutdown)
    # Note: TestClient doesn't support async cleanup, so we skip shutdown


def test_list_portfolios(client: TestClient):
    """Test GET /api/portfolio/list"""
    print("\n" + "=" * 60)
    print("1. GET /api/portfolio/list")
    print("=" * 60)
    
    response = client.get("/api/portfolio/list")
    print(f"Status: {response.status_code}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    portfolios = data.get("portfolios", [])
    print(f"Found {len(portfolios)} portfolios")
    
    if portfolios:
        for p in portfolios:
            print(f"  - {p.get('name', 'N/A')} (ID: {p.get('id')}, Capital: ${p.get('initial_capital', 0)})")
    else:
        print("No portfolios found!")


def test_get_portfolio(client: TestClient):
    """Test GET /api/portfolio/{portfolio_id}"""
    print("\n" + "=" * 60)
    print("2. GET /api/portfolio/{portfolio_id}")
    print("=" * 60)
    
    # First get list to find a portfolio
    response = client.get("/api/portfolio/list")
    if response.status_code != 200:
        print("Cannot test: No portfolios available")
        return
    
    portfolios = response.json().get("portfolios", [])
    if not portfolios:
        print("Cannot test: No portfolios available")
        return
    
    portfolio_id = portfolios[0]["id"]
    print(f"Testing with portfolio ID: {portfolio_id}")
    
    response = client.get(f"/api/portfolio/{portfolio_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        portfolio_info = response.json()
        print(f"Portfolio: {json.dumps(portfolio_info, indent=2)}")
    else:
        print(f"Error: {response.text}")
        pytest.fail(f"Expected 200, got {response.status_code}")


def test_get_trading_status(client: TestClient):
    """Test GET /api/trading/status/{portfolio_id}"""
    print("\n" + "=" * 60)
    print("3. GET /api/trading/status/{portfolio_id}")
    print("=" * 60)
    
    # Get a portfolio ID
    response = client.get("/api/portfolio/list")
    if response.status_code != 200:
        print("Cannot test: No portfolios available")
        return
    
    portfolios = response.json().get("portfolios", [])
    if not portfolios:
        print("Cannot test: No portfolios available")
        return
    
    portfolio_id = portfolios[0]["id"]
    print(f"Testing with portfolio ID: {portfolio_id}")
    
    response = client.get(f"/api/trading/status/{portfolio_id}")
    print(f"Status: {response.status_code}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    status = response.json()
    print(f"Trading Status: {json.dumps(status, indent=2)}")


def test_get_active_portfolio(client: TestClient):
    """Test GET /api/portfolio/active/{portfolio_id} (only if running)"""
    print("\n" + "=" * 60)
    print("4. GET /api/portfolio/active/{portfolio_id}")
    print("=" * 60)
    
    # Get a portfolio ID
    response = client.get("/api/portfolio/list")
    if response.status_code != 200:
        print("Cannot test: No portfolios available")
        return
    
    portfolios = response.json().get("portfolios", [])
    if not portfolios:
        print("Cannot test: No portfolios available")
        return
    
    portfolio_id = portfolios[0]["id"]
    
    # Check if it's running
    status_response = client.get(f"/api/trading/status/{portfolio_id}")
    if status_response.status_code != 200:
        print("Cannot test: Cannot get trading status")
        return
    
    is_running = status_response.json().get("is_running", False)
    
    if not is_running:
        print(f"Portfolio {portfolio_id} is not running, skipping active portfolio test")
        return
    
    print(f"Testing with running portfolio ID: {portfolio_id}")
    
    response = client.get(f"/api/portfolio/active/{portfolio_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        active_info = response.json()
        print(f"Active Portfolio: {json.dumps(active_info, indent=2)}")
    elif response.status_code == 404:
        print("Portfolio not found or not running")
    else:
        print(f"Error: {response.text}")


def test_get_trades(client: TestClient):
    """Test GET /api/portfolio/trades/{portfolio_id}"""
    print("\n" + "=" * 60)
    print("5. GET /api/portfolio/trades/{portfolio_id}")
    print("=" * 60)
    
    # Get a portfolio ID
    response = client.get("/api/portfolio/list")
    if response.status_code != 200:
        print("Cannot test: No portfolios available")
        return
    
    portfolios = response.json().get("portfolios", [])
    if not portfolios:
        print("Cannot test: No portfolios available")
        return
    
    portfolio_id = portfolios[0]["id"]
    print(f"Testing with portfolio ID: {portfolio_id}")
    
    response = client.get(f"/api/portfolio/trades/{portfolio_id}?limit=5")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        trades_data = response.json()
        trades = trades_data.get("trades", [])
        print(f"Found {len(trades)} trades")
        
        if trades:
            print("\nFirst trade:")
            trade = trades[0]
            print(f"  Keys: {list(trade.keys())}")
            for key, value in trade.items():
                value_type = type(value).__name__
                # Truncate long values for display
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                print(f"  {key}: {value_str} (type: {value_type})")
    else:
        print(f"Error: {response.text}")


def test_start_trading(client: TestClient, auto_stop: bool = True):
    """
    Test POST /api/trading/start/{portfolio_id}
    
    Args:
        auto_stop: If True, automatically stop trading after the test (default: True)
    """
    import time
    
    print("\n" + "=" * 60)
    print("6. POST /api/trading/start/{portfolio_id}")
    print("=" * 60)
    
    # Get a portfolio ID
    response = client.get("/api/portfolio/list")
    assert response.status_code == 200, f"Cannot test: Failed to list portfolios - {response.text}"
    
    portfolios = response.json().get("portfolios", [])
    assert len(portfolios) > 0, "Cannot test: No portfolios available"
    
    portfolio_id = portfolios[0]["id"]
    print(f"Testing start trading for portfolio ID: {portfolio_id}")
    
    # Check current status BEFORE
    print("\n--- Status BEFORE starting ---")
    status_response = client.get(f"/api/trading/status/{portfolio_id}")
    assert status_response.status_code == 200, f"Failed to get status: {status_response.text}"
    
    current_status = status_response.json()
    is_running_before = current_status.get("is_running", False)
    print(f"  Is running: {is_running_before}")
    print(f"  Status details: {json.dumps(current_status, indent=2)}")
    
    if is_running_before:
        print(f"\n⚠️  Portfolio {portfolio_id} is already running!")
        print("  Stopping it first...")
        stop_response = client.post(f"/api/trading/stop/{portfolio_id}")
        if stop_response.status_code == 200:
            print("  ✓ Successfully stopped")
            time.sleep(1)  # Wait a bit for cleanup
        else:
            print(f"  ✗ Failed to stop: {stop_response.text}")
            pytest.skip(f"Portfolio {portfolio_id} is already running and could not be stopped")
    
    # Start trading
    print("\n--- Starting trading ---")
    response = client.post(f"/api/trading/start/{portfolio_id}")
    print(f"  Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"  ✗ Error: {response.text}")
        pytest.fail(f"Failed to start trading: {response.status_code} - {response.text}")
    
    result = response.json()
    print(f"  ✓ Result: {json.dumps(result, indent=2)}")
    
    # Wait a moment for trading to initialize
    print("\n--- Waiting 2 seconds for trading to initialize... ---")
    time.sleep(2)
    
    # Check status AFTER starting
    print("\n--- Status AFTER starting ---")
    status_response = client.get(f"/api/trading/status/{portfolio_id}")
    assert status_response.status_code == 200, f"Failed to get status after start: {status_response.text}"
    
    status_after = status_response.json()
    is_running_after = status_after.get("is_running", False)
    print(f"  Is running: {is_running_after}")
    print(f"  Status details: {json.dumps(status_after, indent=2)}")
    
    if is_running_after:
        # Get active strategies
        print("\n--- Active Strategies ---")
        strategies_response = client.get(f"/api/trading/strategies/{portfolio_id}")
        if strategies_response.status_code == 200:
            strategies_data = strategies_response.json()
            strategies = strategies_data.get("strategies", [])
            print(f"  Found {len(strategies)} active strategies:")
            for strat in strategies:
                print(f"    - {strat.get('trader_id', 'N/A')}: {strat.get('symbol', 'N/A')} "
                      f"({strat.get('interval', 'N/A')}) - Status: {strat.get('status', 'N/A')}")
        else:
            print(f"  Could not get strategies: {strategies_response.text}")
        
        # Get recent trades
        print("\n--- Recent Trades ---")
        trades_response = client.get(f"/api/trading/trades/{portfolio_id}?limit=5")
        if trades_response.status_code == 200:
            trades_data = trades_response.json()
            trades = trades_data.get("trades", [])
            print(f"  Found {len(trades)} recent trades")
            if trades:
                print("  Latest trade:")
                latest = trades[0]
                for key, value in latest.items():
                    print(f"    {key}: {value}")
        else:
            print(f"  Could not get trades: {trades_response.text}")
    
    # Stop trading if requested
    if auto_stop and is_running_after:
        print("\n--- Stopping trading (auto_stop=True) ---")
        stop_response = client.post(f"/api/trading/stop/{portfolio_id}")
        if stop_response.status_code == 200:
            print("  ✓ Successfully stopped trading")
            time.sleep(1)  # Wait for cleanup
            
            # Verify it's stopped
            final_status = client.get(f"/api/trading/status/{portfolio_id}")
            if final_status.status_code == 200:
                final_data = final_status.json()
                print(f"  Final status - Is running: {final_data.get('is_running', False)}")
        else:
            print(f"  ✗ Failed to stop: {stop_response.text}")
            print(f"  ⚠️  WARNING: Portfolio {portfolio_id} is still running!")
    elif is_running_after:
        print(f"\n⚠️  Portfolio {portfolio_id} is still running (auto_stop=False)")
        print("  You can stop it manually with: POST /api/trading/stop/{portfolio_id}")


def test_monitor_trading_status(client: TestClient):
    """Monitor trading status to catch potential errors"""
    print("\n" + "=" * 60)
    print("7. Monitoring trading status (to catch errors)")
    print("=" * 60)
    
    # Get a portfolio ID
    response = client.get("/api/portfolio/list")
    if response.status_code != 200:
        print("Cannot test: No portfolios available")
        return
    
    portfolios = response.json().get("portfolios", [])
    if not portfolios:
        print("Cannot test: No portfolios available")
        return
    
    portfolio_id = portfolios[0]["id"]
    
    # Check if running
    status_response = client.get(f"/api/trading/status/{portfolio_id}")
    if status_response.status_code != 200:
        print("Cannot test: Cannot get trading status")
        return
    
    is_running = status_response.json().get("is_running", False)
    
    if not is_running:
        print(f"Portfolio {portfolio_id} is not running, skipping monitoring")
        return
    
    print(f"Monitoring portfolio {portfolio_id} (checking status 5 times)...")
    
    for i in range(5):
        response = client.get(f"/api/trading/status/{portfolio_id}")
        if response.status_code == 200:
            status = response.json()
            print(f"  [{i+1}/5] Status: {'Running' if status.get('is_running') else 'Stopped'}")
        else:
            print(f"  [{i+1}/5] Error: {response.status_code} - {response.text}")


if __name__ == "__main__":
    print("=" * 60)
    print("Portfolio API Test - FastAPI TestClient")
    print("=" * 60)
    print("Running tests...")
    print("=" * 60)
    
    # Initialize app state (simulating lifespan startup)
    settings = get_settings()
    setup_registry(settings)
    app.state.settings = settings
    app.state.services = ServiceFactory(AdapterRegistry, settings)
    app.state.trading_state = TradingStateManager()
    
    # Create client
    test_client = TestClient(app)
    
    # Run tests in order (we just call them sequentially)
    try:
        test_list_portfolios(test_client)
        test_get_portfolio(test_client)
        test_get_trading_status(test_client)
        test_get_active_portfolio(test_client)
        test_get_trades(test_client)
        # Test starting trading (will auto-stop by default)
        # To keep trading running, pass auto_stop=False: test_start_trading(test_client, auto_stop=False)
        test_start_trading(test_client, auto_stop=True)
        test_monitor_trading_status(test_client)
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        print("\nIf you saw the 'float' error in the server logs,")
        print("check the server console output for the full traceback.")
    except Exception as e:
        print(f"\nERROR during tests: {e}")
        import traceback
        traceback.print_exc()
