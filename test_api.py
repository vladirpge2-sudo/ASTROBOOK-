from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["engine"] == "pyswisseph"

def test_chart_with_coordinates():
    payload = {
        "name": "Vladir Fernandes",
        "date": "1990-10-06",
        "time": "11:25",
        "latitude": -23.9608,
        "longitude": -46.3336,
        "timezone": "America/Sao_Paulo",
    }
    response = client.post("/natal-chart/coordinates", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Vladir Fernandes"
    assert len(data["planets"]) >= 10
    assert len(data["houses"]) == 12
    assert "ascendant" in data
    assert "midheaven" in data
