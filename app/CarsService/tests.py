import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from fastapi import HTTPException
from main import app, Session, create_db_and_tables, engine, get_session, Car, CarDataJson, CarReserveResponse
from sqlmodel import SQLModel, create_engine, Session as SQLSession

# Mock the session to avoid using a real database
from unittest.mock import MagicMock

carId = "109b42f3-198d-4c89-9276-a7520a7120ab"

@pytest.fixture(scope="module")
def client():
    """
    Create a FastAPI TestClient for testing the endpoints.
    """
    # Mock database connection
    create_db_and_tables()  # This would create tables in an in-memory DB if configured
    with TestClient(app) as client:
        yield client

@pytest.fixture
def mock_session():
    """
    Fixture to mock the session dependency for the endpoints.
    """
    mock_session = MagicMock(spec=SQLSession)
    return mock_session


def test_get_all_cars(client):
    # Тест для получения всех машин через /api/v1/cars
    response = client.get("/api/v1/cars")
    assert response.status_code == 200
    cars = response.json()["items"]
    assert len(cars) > 0  # Проверим, что хотя бы одна машина есть
    assert cars[0]["carUid"] == carId


def test_reserve_car(client):
    # Тест для бронирования машины через /api/v1/cars/{carUid}/reserve
    response = client.put(f"/api/v1/cars/{carId}/reserve")
    assert response.status_code == 200
    assert response.json()["message"] == "Car reserved successfully"
    assert response.json()["availability"] is False


def test_release_car(client):
    
    # Сначала забронируем машину
    client.put(f"/api/v1/cars/{carId}/reserve")
    
    # Теперь попробуем освободить машину
    response = client.put(f"/api/v1/cars/{carId}/release")
    assert response.status_code == 200
    assert response.json()["message"] == "Car released successfully"
    assert response.json()["availability"] is True
