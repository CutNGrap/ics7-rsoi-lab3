import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from fastapi import HTTPException
from main import app, Session, create_db_and_tables, engine, get_session, Payment, PaymentDataJson
from sqlmodel import SQLModel, create_engine, Session as SQLSession
from unittest.mock import MagicMock


@pytest.fixture(scope="module")
def client():
    """
    Create a FastAPI TestClient for testing the endpoints.
    """
    # Create tables in the test database
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

@pytest.fixture
def payment_data():
    """
    Fixture to provide payment data for testing.
    """
    return {
        "payment_uid": str(uuid4()),
        "status": "PAID",
        "price": 100.0
    }


def test_create_payment(client, payment_data):
    """
    Тест для создания нового платежа через /api/v1/payments
    """
    response = client.post("/api/v1/payments", json=payment_data)
    assert response.status_code == 201
    payment = response.json()

    assert "payment_uid" in payment
    assert payment["status"] == "PAID"
    assert payment["price"] == 100.0

