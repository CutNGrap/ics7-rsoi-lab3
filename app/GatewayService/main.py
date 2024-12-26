from fastapi import *
from fastapi.responses import *
from fastapi.exceptions import RequestValidationError
from sqlmodel import *
from database import *
from typing import Annotated
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
import uvicorn
import requests.adapters as reqad
from multiprocessing import Process
import os
from http import HTTPStatus
import requests
from datetime import datetime
import uuid
from CircuitBreaker import CircuitBreaker
from RequestQueue import RequestQueueManager


requestManager = RequestQueueManager()
circuitBreaker = CircuitBreaker(2, 1)

reqSession = requests.Session()
reqSession.mount("http://", reqad.HTTPAdapter(max_retries=1))


# carsHost = "localhost:8070"
# rentalsHost = "localhost:8060"
# paymentHost = "localhost:8050"
carsHost = "cars:8070"
rentalsHost = "rentals:8060"
paymentsHost = "payments:8050"
carsApi = f"{carsHost}/api/v1"
rentalsApi = f"{rentalsHost}/api/v1"
paymentsApi = f"{paymentsHost}/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # reqSession.post(f"http://{carsHost}/manage/init")
    try:
        reqSession.post(f"http://{carsHost}/manage/init")
    except:
        requestManager.append(lambda: reqSession.post(f"http://{carsHost}/manage/init"))
        print(f"http://{carsHost} is not available")
    yield
    circuitBreaker.terminate()
    requestManager.terminate()

app = FastAPI(lifespan=lifespan)


@app.get('/manage/health', status_code=200)
def health_check():
    return


# Base URLs for services


@app.get("/api/v1/cars", response_model=PaginationResponse)
def get_cars(
    page: int = Query(1, ge=0),
    size: int = Query(10, ge=1, le=100),
    showAll: bool = Query(False)
) -> PaginationResponse:
    if circuitBreaker.isBlocked(carsHost):
        try:
            response = reqSession.get(f"http://{carsApi}/cars", params={"page": page, "size": size})
            circuitBreaker.appendOK(carsHost)
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(carsHost)
            return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
    else:
        return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
    
    if response.status_code == HTTPStatus.OK:
        return PaginationResponse(**response.json())
    else:
        return PaginationResponse(page=page, pageSize=0, totalElements=0, items=[])
    

@app.get("/api/v1/rental", response_model=list[RentalResponse])
def get_user_rentals(
    username: Annotated[str, Header(alias="X-User-Name")]
):
    """
    Gateway метод для получения информации обо всех арендах пользователя.
    """
    # 
    # response = reqSession.get(f"http://{rentalsApi}/rentals", headers={"X-User-Name": username})
    if circuitBreaker.isBlocked(rentalsHost):
        try:
            response = reqSession.get(f"http://{rentalsApi}/rentals", headers={"X-User-Name": username})
            circuitBreaker.appendOK(rentalsHost)
        except requests.ConnectionError:
            circuitBreaker.append(rentalsHost)
            return JSONResponse(content={"message": "Rentals Service unavailable"}, status_code=503)
    else:
        return JSONResponse(content={"message": "Rentals Service unavailable"}, status_code=503)
    # 
    
    if response.status_code == HTTPStatus.OK:
        ans = []
        rentals = response.json()
        for rental in rentals:

            carUid = rental["carUid"]
            paymentUid = rental["paymentUid"]

            # 
            # carResponse = reqSession.get(f"http://{carsApi}/cars/{carUid}?showAll=true)
            if circuitBreaker.isBlocked(carsHost):
                try:
                    carResponse = reqSession.get(f"http://{carsApi}/cars/{carUid}?showAll=true")
                    circuitBreaker.appendOK(carsHost)
                    carResponseData = carResponse.json()
                except requests.ConnectionError:
                    circuitBreaker.append(carsHost)
                    carResponseData = None
                    # return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
            else:
                # return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
                carResponseData = None
            # 

            if carResponse.status_code == HTTPStatus.NOT_FOUND:
                raise HTTPException(status_code=404, detail="Couldnt finde car")
            # 
            # payResponse = reqSession.get(f"http://{paymentsApi}/payment/{paymentUid}")
            if circuitBreaker.isBlocked(paymentsHost):
                try:
                    paymentResponse = reqSession.get(f"http://{paymentsApi}/payment/{paymentUid}")
                    circuitBreaker.appendOK(paymentResponse)
                    paymentResponseData = paymentResponse.json()
                except requests.ConnectionError:
                    circuitBreaker.append(paymentsHost)
                    paymentResponseData = None
                    # return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
            else:
                # return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
                paymentResponseData = None
            # 

            if paymentResponse.status_code == HTTPStatus.NOT_FOUND:
                raise HTTPException(status_code=404, detail="Couldnt finde payment")

            if (carResponseData is None):
                carData = CarData(
                    carUid = carUid)
            else:
                carData = CarData(
                    carUid = carResponseData["carUid"],
                    brand = carResponseData["brand"],
                    model = carResponseData["model"],
                    registrationNumber = carResponseData["registrationNumber"]
                )

            if (paymentResponseData is None):
                paymentData = PaymentData(
                    paymentUid = paymentUid)
            else:
                paymentData = PaymentData(
                    paymentUid = paymentUid,
                    status = paymentResponseData["status"],
                    price = paymentResponseData["price"],
                )


            ans.append(RentalResponse(
                rentalUid=rental["rentalUid"],
                status = rental["status"],
                dateFrom = rental["dateFrom"],
                dateTo = rental["dateTo"],
                car = carData,
                payment=paymentData
            ))

        return ans
    elif response.status_code == HTTPStatus.NOT_FOUND:
        raise HTTPException(status_code=404, detail="No rentals found for user")
    else:
        response.raise_for_status()


@app.get("/api/v1/rental/{rentalUid}", response_model=RentalResponse)
def get_rental_details(
    rentalUid: str,
    username: Annotated[str, Header(alias="X-User-Name")]
):
    """
    Gateway метод для получения информации по конкретной аренде пользователя.
    """
    # 
    # response = reqSession.get(f"http://{rentalsApi}/rentals/{rentalUid}",headers={"X-User-Name": username})
    if circuitBreaker.isBlocked(rentalsHost):
        try:
            response = reqSession.get(f"http://{rentalsApi}/rentals/{rentalUid}", headers={"X-User-Name": username})
            circuitBreaker.appendOK(rentalsHost)
        except requests.ConnectionError:
            circuitBreaker.append(rentalsHost)
            return JSONResponse(content={"message": "Rentals Service unavailable"}, status_code=503)
    else:
        return JSONResponse(content={"message": "Rentals Service unavailable"}, status_code=503)
    # 
    
    if response.status_code == HTTPStatus.OK:
        rental = response.json()
        carUid = rental["carUid"]
        paymentUid = rental["paymentUid"]

        # 
        # carResponse = reqSession.get(f"http://{carsApi}/cars/{carUid}?showAll=true)
        if circuitBreaker.isBlocked(carsHost):
            try:
                carResponse = reqSession.get(f"http://{carsApi}/cars/{carUid}?showAll=true")
                circuitBreaker.appendOK(carsHost)
                carResponseData = carResponse.json()
            except requests.ConnectionError:
                circuitBreaker.append(carsHost)
                carResponseData = None
                # return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
        else:
            # return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
            carResponseData = None
        # 

        if carResponse.status_code == HTTPStatus.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Couldnt finde car")
        # 
        # payResponse = reqSession.get(f"http://{paymentsApi}/payment/{paymentUid}")
        if circuitBreaker.isBlocked(paymentsHost):
            try:
                paymentResponse = reqSession.get(f"http://{paymentsApi}/payment/{paymentUid}")
                circuitBreaker.appendOK(paymentResponse)
                paymentResponseData = paymentResponse.json()
            except requests.ConnectionError:
                circuitBreaker.append(paymentsHost)
                paymentResponseData = None
                # return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
        else:
            # return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
            paymentResponseData = None
        # 

        if paymentResponse.status_code == HTTPStatus.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Couldnt finde payment")

        if (carResponseData is None):
            carData = CarData(
                carUid = carUid)
        else:
            carData = CarData(
                carUid = carResponseData["carUid"],
                brand = carResponseData["brand"],
                model = carResponseData["model"],
                registrationNumber = carResponseData["registrationNumber"]
            )

        if (paymentResponseData is None):
            paymentData = PaymentData(
                paymentUid = paymentUid)
        else:
            paymentData = PaymentData(
                paymentUid = paymentUid,
                status = paymentResponseData["status"],
                price = paymentResponseData["price"],
            )

        return RentalResponse(
            rentalUid=rental["rentalUid"],
            status = rental["status"],
            dateFrom = rental["dateFrom"],
            dateTo = rental["dateTo"],
            car = carData,
            payment=paymentData
        )
    elif response.status_code == HTTPStatus.NOT_FOUND:
        raise HTTPException(status_code=404, detail="Rental not found")
    elif response.status_code == HTTPStatus.FORBIDDEN:
        raise HTTPException(status_code=403, detail="Unauthorized to access this rental")
    else:
        response.raise_for_status()
    

@app.post("/api/v1/rental", status_code=200)
def book_car(
    rental_request: CreateRentalRequest, 
    username: Annotated[str, Header(alias="X-User-Name")]
) -> CreateRentalResponse:
    
    carUid = rental_request.carUid

    # 
    # response = reqSession.get(f"http://{carsApi}/cars/{carUid}")
    if circuitBreaker.isBlocked(carsHost):
        try:
            response = reqSession.get(f"http://{carsApi}/cars/{carUid}")
            circuitBreaker.appendOK(carsHost)
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(carsHost)
            return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
    else:
        return JSONResponse(content={"message": "Cars Service unavailable"}, status_code=503)
    # 
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise HTTPException(status_code=404, detail="Car not found")

    car = response.json()

    reserve_response = reqSession.put(f"http://{carsApi}/cars/{carUid}/reserve")
    if reserve_response.status_code != HTTPStatus.OK:
        raise HTTPException(status_code=500, detail="Failed to reserve car")

    date_from = datetime.strptime(str(rental_request.dateFrom), "%Y-%m-%d")
    date_to = datetime.strptime(str(rental_request.dateTo), "%Y-%m-%d")
    rental_days = (date_to - date_from).days

    if rental_days <= 0:
        raise HTTPException(status_code=400, detail="Invalid rental period")
    total_price = rental_days * car["price"]
    payment_request = {
        "status": "PAID",
        "price": total_price
    }

    # 
    # payment_response = reqSession.post(f"http://{paymentsApi}/payment", json=payment_request)
    if circuitBreaker.isBlocked(paymentsHost):
        try:
            payment_response = reqSession.post(f"http://{paymentsApi}/payment", json=payment_request)
            circuitBreaker.appendOK(paymentsHost)
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(paymentsHost)
            reqSession.put(f"http://{carsApi}/cars{carUid}/release")
            return JSONResponse(content={"message": "Payment Service unavailable"}, status_code=503)
    else:
        reqSession.put(f"http://{carsApi}/cars{carUid}/release")
        return JSONResponse(content={"message": "Payment Service unavailable"}, status_code=503)
    # 


    payment_data = payment_response.json()
    paymentUid = str(payment_data["paymentUid"])

    rental_data = {
        "rentalUid": str(uuid.uuid4()),
        "username": username,
        "paymentUid": str(payment_data["paymentUid"]),
        "carUid": str(carUid),
        "date_from": str(rental_request.dateFrom),
        "date_to": str(rental_request.dateTo),
        "status": "IN_PROGRESS"
    }

    # 
    # rental_response = reqSession.post(f"http://{rentalsApi}/rentals", json=rental_data)
    if circuitBreaker.isBlocked(rentalsHost):
        try:
            rental_response = reqSession.post(f"http://{rentalsApi}/rentals", json=rental_data)
            circuitBreaker.appendOK(rentalsHost)
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(rentalsHost)
            reqSession.put(f"http://{carsApi}/cars/{carUid}/release")
            reqSession.put(f"http://{paymentsApi}/payments/{paymentUid}/cancel")
            return JSONResponse(content={"message": "Rental Service unavailable"}, status_code=503)
    else:
        reqSession.put(f"http://{carsApi}/cars/{carUid}/release")
        reqSession.put(f"http://{paymentsApi}/payments/{paymentUid}/cancel")
        return JSONResponse(content={"message": "Rental Service unavailable"}, status_code=503)
    # 

    if rental_response.status_code != HTTPStatus.CREATED:
        raise HTTPException(status_code=500, detail="Failed to create rental record")
    
    rental_response_data =  rental_response.json()
    
    p = PaymentInfo(
            paymentUid=str(payment_data['paymentUid']),
            status=payment_data["status"],
            price=payment_data["price"]
        )
    
    uid = str(rental_response_data["rentalUid"])

    return  CreateRentalResponse(
        rentalUid=uid,
        status=rental_response_data["status"],
        carUid=str(carUid),
        dateFrom=date_from,
        dateTo=date_to,
        payment=p
    )

    
@app.post("/api/v1/rental/{rentalUid}/finish", status_code=204)
def finish_rental(
    rentalUid: str,
    username: Annotated[str, Header(alias="X-User-Name")]
):
    # 
    # rental_response = requests.get(f"http://{rentalsApi}/rentals/{rentalUid}",headers={"X-User-Name": username})
    if circuitBreaker.isBlocked(rentalsHost):
        try:
            rental_response = requests.get(f"http://{rentalsApi}/rentals/{rentalUid}",headers={"X-User-Name": username})
            circuitBreaker.appendOK(rentalsHost)
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(rentalsHost)
            return JSONResponse(content={"message": "rentals Service unavailable"}, status_code=503)
    else:
        return JSONResponse(content={"message": "rentals Service unavailable"}, status_code=503)
    # 
    
        
    if rental_response.status_code == HTTPStatus.NOT_FOUND:
        raise HTTPException(status_code=404, detail="Rental not found")
    
    rental_data = rental_response.json()
    
    
    finish_rental_data = {
        "status": "FINISHED"
    }


    # 
    # finish_response = reqSession.put(f"http://{rentalsApi}/rentals/{rentalUid}/finish", json=finish_rental_data)
    if circuitBreaker.isBlocked(rentalsHost):
        try:
            finish_response = reqSession.put(f"http://{rentalsApi}/rentals/{rentalUid}/finish", json=finish_rental_data)
            circuitBreaker.appendOK(rentalsHost)
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(rentalsHost)
            requestManager.append(lambda: reqSession.put(f"http://{rentalsApi}/rentals/{rentalUid}/finish", json=finish_rental_data))
    else:
        requestManager.append(lambda: reqSession.put(f"http://{rentalsApi}/rentals/{rentalUid}/finish", json=finish_rental_data))
    # 

    if finish_response.status_code != HTTPStatus.OK:
        raise HTTPException(status_code=500, detail="Failed to update rental status")
    
    # Remove reservation on the car in Car Service
    carUid = rental_data["carUid"]
    unreserve_response = reqSession.put(
        f"http://{carsApi}/cars/{carUid}/release"
    )
    if unreserve_response.status_code != HTTPStatus.OK:
        raise HTTPException(status_code=500, detail="Failed to unreserve car")
    
    return 
    

@app.delete("/api/v1/rental/{rentalUid}", status_code=204)
def cancel_rental(
    rentalUid: str,
    username: Annotated[str, Header(alias="X-User-Name")]
):
    # 
    # rental_response = reqSession.get(f"http://{rentalsApi}/rentals/{rentalUid}",headers={"X-User-Name": username})
    if circuitBreaker.isBlocked(rentalsHost):
        try:
            rental_response = reqSession.get(f"http://{rentalsApi}/rentals/{rentalUid}",headers={"X-User-Name": username})
            circuitBreaker.appendOK(rentalsHost)
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(rentalsHost)
            return JSONResponse(content={"message": "rentals Service unavailable"}, status_code=503)
    else:
        return JSONResponse(content={"message": "rentals Service unavailable"}, status_code=503)
    # 

    if rental_response.status_code == HTTPStatus.NOT_FOUND:
        raise HTTPException(status_code=404, detail="Rental not found")
    
    rental_data = rental_response.json()
    
    carUid = rental_data["carUid"]
    print('\n\n',carUid,'\n\n')

    # 
    # unreserve_response = reqSession.put(f"http://{carsApi}/cars/{carUid}/release")
    if circuitBreaker.isBlocked(carsHost):
        try:
            unreserve_response = reqSession.put(f"http://{carsApi}/cars/{carUid}/release")
            circuitBreaker.appendOK(carsHost)
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(carsHost)
            return JSONResponse(content={"message": "cars Service unavailable"}, status_code=503)
    else:
        return JSONResponse(content={"message": "cars Service unavailable"}, status_code=503)
    # 

    if unreserve_response.status_code != HTTPStatus.OK:
        raise HTTPException(status_code=500, detail="Failed to unreserve car")
    
    cancel_rental_data = {"status": "CANCELED"}
    # 
    # rental_finish_response = reqSession.put(f"http://{rentalsApi}/rentals/{rentalUid}/cancel",json=cancel_rental_data,headers={"X-User-Name": username})
    if circuitBreaker.isBlocked(rentalsHost):
        try:
            rental_finish_response = reqSession.get(f"http://{rentalsHost}/rentals/{rentalUid}/cancel",json=cancel_rental_data,headers={"X-User-Name": username})
            circuitBreaker.appendOK(rentalsHost)
            if rental_finish_response.status_code == HTTPStatus.NOT_FOUND:
                raise HTTPException(status_code=404, detail="Rental not found")
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(rentalsHost)
            requestManager.append(lambda: reqSession.get(f"http://{rentalsHost}/rentals/{rentalUid}/cancel",json=cancel_rental_data,headers={"X-User-Name": username}))
    else:
        requestManager.append(lambda: reqSession.get(f"http://{rentalsHost}/rentals/{rentalUid}/cancel",json=cancel_rental_data,headers={"X-User-Name": username}))
    # 


    if rental_finish_response.status_code != HTTPStatus.OK:
        raise HTTPException(status_code=500, detail="Failed to update rental status to CANCELED")
    
    paymentUid = rental_data['paymentUid'] 
    cancel_payment_data = {"status": "CANCELED"}


    # 
    # payment_response = reqSession.put(f"http://{paymentsApi}/payments/{paymentUid}/cancel",json=cancel_payment_data,headers={"X-User-Name": username} )
    if circuitBreaker.isBlocked(paymentsHost):
        try:
            payment_response = reqSession.put(f"http://{paymentsApi}/payments/{paymentUid}/cancel",json=cancel_payment_data,headers={"X-User-Name": username} )
            circuitBreaker.appendOK(rentalsHost)
            if payment_response.status_code == HTTPStatus.NOT_FOUND:
                raise HTTPException(status_code=404, detail="Payment not found")
        except requests.ConnectionError as ex:
            print(ex)
            circuitBreaker.append(rentalsHost)
            requestManager.append(lambda: reqSession.put(f"http://{paymentsApi}/payments/{paymentUid}/cancel",json=cancel_payment_data,headers={"X-User-Name": username} ))
    else:
        requestManager.append(lambda: reqSession.put(f"http://{paymentsApi}/payments/{paymentUid}/cancel",json=cancel_payment_data,headers={"X-User-Name": username} ))
    # 
    # 
    return 
