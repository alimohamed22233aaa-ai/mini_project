from app.app import app


def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_returns_json_with_version():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "application/json" in response.content_type
    data = response.get_json()
    assert data["app"] == "web-app"
    assert "version" in data


def test_index_returns_html_for_browser():
    client = app.test_client()
    response = client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"<html" in response.data