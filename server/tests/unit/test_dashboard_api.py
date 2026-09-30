from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from apps.api.dependencies import get_service_factory
from apps.api.main import app


def test_strategy_forms_receive_labels_and_select_options():
    with TestClient(app) as client:
        for strategy in ('mock_strategy', 'mean_cross', 'momentum'):
            response = client.get(f'/api/portfolio/strategies/{strategy}/params')
            assert response.status_code == 200
            params = response.json()['parameters']['all']
            assert all(param['label'] for param in params)
            for param in params:
                if param['name'] == 'execution_mode' and strategy == 'mock_strategy':
                    assert param['type'] == 'select'
                    assert param['default'] in [option['value'] for option in param['options']]


def test_dashboard_open_positions_route_accepts_empty_portfolio_list():
    manager = AsyncMock()
    manager.__aenter__.return_value = manager
    manager._storage.list_portfolios.return_value = []
    app.dependency_overrides[get_service_factory] = lambda: SimpleNamespace(create_portfolio_manager=lambda: manager)
    try:
        with TestClient(app) as client:
            assert client.get('/health').json() == {'status': 'ok'}
            response = client.get('/api/portfolio/positions/open')
            assert response.status_code == 200
            assert response.json() == {'status': 'success', 'positions': []}
    finally:
        app.dependency_overrides.clear()
