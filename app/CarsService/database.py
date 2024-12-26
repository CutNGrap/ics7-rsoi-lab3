from sqlmodel import SQLModel, Field, Column, CheckConstraint
import uuid
from pydantic import BaseModel

from sqlalchemy import CheckConstraint
from sqlmodel import SQLModel, Field
import uuid

class Car(SQLModel, table=True):
    __tablename__ = "cars"

    id: int = Field(primary_key=True, index=True)
    car_uid: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False, unique=True)
    brand: str = Field(nullable=False, max_length=80)
    model: str = Field(nullable=False, max_length=80)
    registration_number: str = Field(nullable=False, max_length=20)
    power: int = Field(default=None)
    price: int = Field(nullable=False)
    type: str = Field(nullable=True, max_length=20)  # Removed the check here.
    availability: bool = Field(nullable=False)

    # Adding the CheckConstraint to validate the 'type' column
    __table_args__ = (
        CheckConstraint("type IN ('SEDAN', 'SUV', 'MINIVAN', 'ROADSTER')", name="check_type"),
    )


class CarDataJson(BaseModel):
    carUid: str
    brand: str
    model: str
    registrationNumber: str
    power: int
    price: int
    type: str
    available: bool

class CarReserveResponse(BaseModel):
    message: str
    carUid: str
    available: bool


class CarsResponse(BaseModel):
    page: int = 1
    pageSize: int = 10
    totalElements: int
    items: list[CarDataJson]