import pytest
from httpx import ASGITransport, AsyncClient

from app import main as main_module


@pytest.fixture(autouse=True)
def mock_db_pool(monkeypatch):
    async def fake_get_pool():
        return None

    async def fake_close_pool():
        return None

    monkeypatch.setattr(main_module, "get_pool", fake_get_pool)
    monkeypatch.setattr(main_module, "close_pool", fake_close_pool)


async def test_health_endpoint_reports_ok():
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
