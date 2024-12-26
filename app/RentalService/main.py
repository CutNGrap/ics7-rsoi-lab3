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


database_url = os.environ["DATABASE_URL"]
# database_url = 'postgresql://program:test@localhost/rentals'
# database_url = 'postgresql://program:test@autorack.proxy.rlwy.net:52848/rentals'
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


@app.get('/manage/health', status_code=200) 
def health():
    return 

@app.get("/api/v1/rentals", response_model=list[RentalDataJson])
def get_user_rentals(session: SessionDep, username: str = Header(..., alias="X-User-Name")):
    rentals = session.exec(select(Rental).where(Rental.username == username)).all()
    if not rentals:
        raise HTTPException(status_code=404, detail="No rentals found for user")

    return [
        RentalDataJson(
            rentalUid=str(rental.rental_uid),
            username=rental.username,
            paymentUid=str(rental.payment_uid),
            carUid=str(rental.car_uid),
            dateFrom=rental.date_from,
            dateTo=rental.date_to,
            status=rental.status
        ) for rental in rentals
    ]

@app.get("/api/v1/rentals/{rentalUid}", response_model=RentalDataJson)
def get_rental_details(
    rentalUid: str, 
    session: SessionDep, 
    username: str = Header(..., alias="X-User-Name")
):
    if (rentalUid[0]==':'): rentalUid=rentalUid[1:]
    rental = session.exec(select(Rental).where(Rental.rental_uid == rentalUid)).first()
    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")

    if rental.username != username:
        raise HTTPException(status_code=403, detail="Unauthorized to view this rental")

    return RentalDataJson(
        rentalUid=str(rental.rental_uid),
        username=rental.username,
        paymentUid=str(rental.payment_uid),
        carUid=str(rental.car_uid),
        dateFrom=rental.date_from,
        dateTo=rental.date_to,
        status=rental.status
    )

@app.post("/api/v1/rentals", status_code=201, response_model=RentalDataJson)
def create_rental(rental: RentalData, session: SessionDep):
    """
    Endpoint for creating a new rental record.
    """
    dbRental = Rental(
        rental_uid=rental.rentalUid,
        username=rental.username,
        payment_uid=rental.paymentUid,
        car_uid=rental.carUid,
        date_from=rental.date_from,
        date_to=rental.date_to,
        status=rental.status
    )
    session.add(dbRental)
    session.commit()
    session.refresh(dbRental)
    return RentalDataJson(
        rentalUid=str(dbRental.rental_uid),
        username=dbRental.username,
        paymentUid=str(dbRental.payment_uid),
        carUid=str(dbRental.car_uid),
        dateFrom=dbRental.date_from.date(),
        dateTo=dbRental.date_to.date(),
        status=dbRental.status
    )



@app.put("/api/v1/rentals/{rental_uid}/cancel", status_code=200, response_model=RentalDataJson)
def cancel_rental(rental_uid: str, session: SessionDep, username: Annotated[str, Header(alias="X-User-Name")]):
    """
    Endpoint for canceling a rental.
    """
    if (rental_uid[0]==':'): rental_uid=rental_uid[1:]
    rental = session.exec(select(Rental).where(Rental.rental_uid == rental_uid)).first()

    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")

    # if rental.username != username:
    #     raise HTTPException(status_code=403, detail="Unauthorized: Username does not match")

    # if rental.status == "CANCELED":
    #     raise HTTPException(status_code=400, detail="Rental is already canceled")

    rental.status = "CANCELED"
    session.add(rental)
    session.commit()
    session.refresh(rental)

    return RentalDataJson(
        rentalUid=str(rental.rental_uid),
        username=rental.username,
        paymentUid=str(rental.payment_uid),
        carUid=str(rental.car_uid),
        dateFrom=rental.date_from.date(),
        dateTo=rental.date_to.date(),
        status=rental.status
    )


@app.put("/api/v1/rentals/{rental_uid}/finish", status_code=200, response_model=RentalDataJson)
def finish_rental(rental_uid: uuid.UUID, session: SessionDep):
    """
    Endpoint for finishing a rental.
    """
    rental = session.exec(select(Rental).where(Rental.rental_uid == rental_uid)).first()

    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")

    if rental.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Only rentals in progress can be finished")

    rental.status = "FINISHED"
    session.add(rental)
    session.commit()
    session.refresh(rental)

    return RentalDataJson(
        rentalUid=str(rental.rental_uid),
        username=rental.username,
        paymentUid=str(rental.payment_uid),
        carUid=str(rental.car_uid),
        dateFrom=rental.date_from.date(),
        dateTo=rental.date_to.date(),
        status=rental.status
    )




@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request : Request, exc):
    return JSONResponse({"message": "what", "errors": exc.errors()[0]}, status_code=400)