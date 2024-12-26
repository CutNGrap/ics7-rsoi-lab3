import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime
from main import app, Rental, RentalDataJson, Session, get_session
from sqlmodel import Session as SQLSession
from unittest.mock import MagicMock

# Тестовые данные
username = "test_user"
car_uid = uuid4()
payment_uid = uuid4()
rental_uid = uuid4()

@pytest.fixture(scope="module")
def client():
    """Создает TestClient для тестирования эндпоинтов."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_session():
    """Фикстура для мокирования сессии."""
    mock_session = MagicMock(spec=SQLSession)
    return mock_session


@pytest.fixture
def create_rental_in_db(mock_session):
    """Фикстура для создания аренды в базе данных."""
    rental = Rental(
        rental_uid=rental_uid,
        username=username,
        payment_uid=payment_uid,
        car_uid=car_uid,
        date_from=datetime.now(),
        date_to=datetime.now(),
        status="IN_PROGRESS"
    )
    mock_session.add(rental)
    mock_session.commit()
    mock_session.refresh(rental)
    return rental


# def test_get_rental_details_not_found(client):
#     """Тест для случая, когда аренда не найдена."""
#     non_existing_rental_uid = uuid4()
#     response = client.get(f"/api/v1/rental/{non_existing_rental_uid}", headers={"X-User-Name": username})
#     assert response.status_code == 404
#     assert response.json()["detail"] == "Rental not found"


# def test_create_rental(client):
#     """Тест для создания аренды."""
#     rental_data = {
#         "username": username,
#         "payment_uid": str(payment_uid),
#         "car_uid": str(car_uid),
#         "date_from": datetime.now().isoformat(),
#         "date_to": datetime.now().isoformat(),
#         "status": "IN_PROGRESS"
#     }
#     response = client.post("/api/v1/rentals", json=rental_data)
#     assert response.status_code == 201
#     rental = response.json()
#     assert rental["username"] == username
#     assert rental["status"] == "IN_PROGRESS"


def test_cancel_rental_not_found(client):
    """Тест для попытки отменить несуществующую аренду."""
    non_existing_rental_uid = uuid4()
    response = client.put(f"/api/v1/rentals/{non_existing_rental_uid}/cancel", headers={"X-User-Name": username})
    assert response.status_code == 404
    assert response.json()["detail"] == "Rental not found"

def test_finish_rental_not_found(client):
    """Тест для попытки завершить несуществующую аренду."""
    non_existing_rental_uid = uuid4()
    response = client.put(f"/api/v1/rentals/{non_existing_rental_uid}/finish")
    assert response.status_code == 404
    assert response.json()["detail"] == "Rental not found"
