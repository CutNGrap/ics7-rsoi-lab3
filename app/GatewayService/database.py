from pydantic import BaseModel, Field, UUID4
from typing import List, Optional, Literal
from datetime import date
import datetime as dt
import uuid


class PaginationResponse(BaseModel):
    page: int
    pageSize: int
    totalElements: int
    items: List['CarDataJson']


class CarDataJson(BaseModel):
    carUid: str
    brand: str
    model: str
    registrationNumber: str
    power: int
    price: int
    type: str
    available: bool

class CarData(BaseModel):
    carUid: str
    brand: Optional[str] = None
    model: Optional[str] = None
    registrationNumber: Optional[str] = None

class PaymentData(BaseModel):
    paymentUid: str
    status: Optional[str] = None
    price: Optional[int] = None

class RentalResponse(BaseModel):
    rentalUid: str
    status: str
    dateFrom: str
    dateTo: str
    car: CarData
    payment: PaymentData


class CreateRentalRequest(BaseModel):
    carUid: UUID4
    dateFrom: date
    dateTo: date


class CreateRentalResponse(BaseModel):
    rentalUid: str
    status: Literal['IN_PROGRESS', 'FINISHED', 'CANCELED']
    carUid: str
    dateFrom: date
    dateTo: date
    payment: 'PaymentInfo'


class CarInfo(BaseModel):
    carUid: UUID4
    brand: str
    model: str
    registrationNumber: str


class PaymentInfo(BaseModel):
    paymentUid: UUID4
    status: Literal['PAID', 'REVERSED']
    price: int


class ErrorDescription(BaseModel):
    field: Optional[str]
    error: str


class ErrorResponse(BaseModel):
    message: str


class ValidationErrorResponse(BaseModel):
    message: str
    errors: List[ErrorDescription]


class PaymentRequest(BaseModel):
    paymentUid: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False)
    status: str = Field(nullable=False)
    price: int = Field(nullable=False)
