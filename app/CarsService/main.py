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
# database_url = 'postgresql://program:test@localhost/cars'
# database_url = 'postgresql://program:test@autorack.proxy.rlwy.net:52848/cars'
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
 
@app.post('/manage/init')
def init(session: SessionDep):
    query = text("""select * from cars where id=1""")
    if not session.exec(query).first():
        query = text("""insert into cars values
    (1, '109b42f3-198d-4c89-9276-a7520a7120ab', 'Mercedes Benz', 'GLA 250', 'ЛО777Х799', '249', '3500', 'SEDAN', 'true')
    """)
        session.exec(query)
        session.commit()

@app.get("/api/v1/cars", response_model=CarsResponse)
def get_all_cars(
    session: SessionDep, 
    page: int = Query(1, alias="page", ge=1), 
    size: int = Query(10, alias="size", ge=1), 
    showAll: bool = Query(False, alias="showAll")
) -> CarsResponse:
    query = select(Car)
    if not showAll:
        query = query.where(Car.availability == True)

    cars = session.exec(query.offset((page - 1) * size).limit(size)).all()
    # if not cars:
    #     raise HTTPException(status_code=404, detail="No cars available")

    response_data = CarsResponse(
        items=[
            CarDataJson(
                carUid=str(car.car_uid),
                brand=car.brand,
                model=car.model,
                registrationNumber=car.registration_number,
                power=car.power,
                price=car.price,
                type=car.type,
                available=car.availability
            ) for car in cars
        ],
        totalElements=len(cars)  # Optionally include the total count of cars
    )

    return response_data

@app.get("/api/v1/cars/{car_uid}", response_model=CarDataJson)
def get_car(session: SessionDep, car_uid: str):
    """
    Возвращает информацию об автомобиле по его car_uid.
    """
    query = select(Car).where(Car.car_uid==car_uid)
    car = session.exec(query).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return CarDataJson(
                carUid=str(car.car_uid),
                brand=car.brand,
                model=car.model,
                registrationNumber=car.registration_number,
                power=car.power,
                price=car.price,
                type=car.type,
                available=car.availability
            )


@app.put("/api/v1/cars/{car_uid}/reserve", status_code=200, response_model=CarReserveResponse)
def reserve_car(car_uid: uuid.UUID, session: SessionDep) -> CarReserveResponse:
    """
    Endpoint for reserving a car by setting its availability to False.
    """
    # Fetch the car by UUID
    car = session.exec(select(Car).where(Car.car_uid == car_uid)).first()

    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    # if not car.availability:
    #     raise HTTPException(status_code=400, detail="Car is already reserved")

    # Update the availability
    car.availability = False
    session.add(car)
    session.commit()
    session.refresh(car)

    return CarReserveResponse(
        message="Car reserved successfully",
        carUid=str(car.car_uid),
        available=car.availability
    )


@app.put("/api/v1/cars/{car_uid}/release", status_code=200, response_model=CarReserveResponse)
def release_car(car_uid: uuid.UUID, session: SessionDep) -> CarReserveResponse:
    """
    Endpoint for releasing a car by setting its availability to True.
    """
    car = session.exec(select(Car).where(Car.car_uid == car_uid)).first()

    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    # if car.availability:
    #     raise HTTPException(status_code=400, detail="Car is already available")

    car.availability = True
    session.add(car)
    session.commit()
    session.refresh(car)

    return CarReserveResponse(
        message="Car released successfully",
        carUid=str(car.car_uid),
        available=car.availability
    )




@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request : Request, exc):
    return JSONResponse({"message": "what", "errors": exc.errors()[0]}, status_code=400)