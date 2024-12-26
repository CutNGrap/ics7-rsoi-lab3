from fastapi import *
from fastapi.responses import *
from fastapi.exceptions import RequestValidationError
from sqlmodel import *
from database import *
from typing import Annotated
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
import uvicorn
from multiprocessing import Process
import os
import datetime as dt
import uuid

app = FastAPI()

# database_url = database_url = 'postgresql://program:test@localhost/payments'
# database_url = 'postgresql://program:test@autorack.proxy.rlwy.net:52848/payments'
database_url = os.environ["DATABASE_URL"]
print(database_url)
engine = create_engine(database_url)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app = FastAPI()

# Create a Pydantic model to respond with


# Assuming a Session Dependency is already set up in the app for database interaction
def get_db():
    # This is a placeholder for actual database session handling
    pass


@app.get('/manage/health', status_code=200) 
def health():
    return 

@app.get("/api/v1/payment/{paymentUid}", status_code=200, response_model=PaymentDataJson)
def create_payment(paymentUid: str,  session: SessionDep):
    """
    Endpoint for getting a payment record.
    """
    payment = session.exec(select(Payment).where(Payment.payment_uid == paymentUid)).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return PaymentDataJson(
        paymentUid=str(payment.payment_uid),
        status=payment.status,
        price=payment.price
    )


@app.post("/api/v1/payment", status_code=201, response_model=PaymentDataJson)
def create_payment(payment: PaymentJson, session: SessionDep):
    """
    Endpoint for creating a new payment record.
    """
    dbPayment = Payment(
        payment_uid=uuid.uuid4(),
        status=payment.status,
        price=payment.price
    )
    session.add(dbPayment)
    session.commit()
    session.refresh(dbPayment)
    return PaymentDataJson(
        paymentUid=str(dbPayment.payment_uid),
        status=dbPayment.status,
        price=dbPayment.price
    )


@app.put("/api/v1/payments/{payment_uid}/cancel", status_code=200, response_model=PaymentDataJson)
def cancel_payment(payment_uid: str, session: SessionDep):
    """
    Endpoint for canceling a payment.
    """
    payment = session.exec(select(Payment).where(Payment.payment_uid == payment_uid)).first()

    if not payment:
        raise HTTPException(status_code=404, detail="payment not found")

    # if payment.status == "CANCELED":
    #     raise HTTPException(status_code=400, detail="payment is already canceled")

    payment.status = "CANCELED"
    session.add(payment)
    session.commit()
    session.refresh(payment)

    return PaymentDataJson(
        paymentUid=str(payment.payment_uid),
        status=payment.status,
        price=payment.price
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request : Request, exc):
    return JSONResponse({"message": "what", "errors": exc.errors()[0]}, status_code=400)


