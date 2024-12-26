from sqlmodel import SQLModel, Field, Column, CheckConstraint
import uuid
import datetime as dt

class Rental(SQLModel, table=True):
    __tablename__ = "rental"

    id: int = Field(primary_key=True, index=True)
    rental_uid: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False, unique=True)
    username: str = Field(nullable=False, max_length=80)
    payment_uid: uuid.UUID = Field(nullable=False)
    car_uid: uuid.UUID = Field(nullable=False)
    date_from: dt.datetime = Field(nullable=False)
    date_to: dt.datetime = Field(nullable=False)
    status: str = Field(nullable=False)

    # Добавляем ограничение через __table_args__
    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'FINISHED', 'CANCELED')", 
            name="status_check"
        ),
    )
    
class RentalDataJson(SQLModel):
    rentalUid: str
    username: str
    paymentUid: str
    carUid: str
    dateFrom: dt.date
    dateTo: dt.date
    status: str

class RentalData(SQLModel):
    rentalUid: str
    username: str
    paymentUid: str
    carUid: str
    date_from: dt.date
    date_to: dt.date
    status: str
