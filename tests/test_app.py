from app.app import app


def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"Hello from Flask!" in response.data