"""API Integration Tests"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Fixture to get auth token"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    return response.json()["access_token"]


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_protected_endpoint_without_token(client):
    """Test protected endpoint without token"""
    response = client.get("/api/documents/list")
    assert response.status_code == 401


def test_protected_endpoint_with_token(client, auth_token):
    """Test protected endpoint with token"""
    response = client.get(
        "/api/documents/list",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200


def test_query_endpoint(client, auth_token):
    """Test query endpoint"""
    response = client.post(
        "/api/queries/",
        json={"question": "Test question"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    # May fail if no documents, but should not be 401
    assert response.status_code != 401
