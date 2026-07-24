"""Authentication Tests"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


def test_register(client):
    """Test user registration"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


def test_login(client):
    """Test user login"""
    # First register
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Then login
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401


def test_register_duplicate_email(client):
    """Test registration with duplicate email"""
    # Register first user
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Try to register again with same email
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "anotherpassword"
        }
    )
    assert response.status_code == 400
