from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, FileResponse
from app.models.schemas import URLRequest, URLResponse, QRCodeRequest, QRCodeResponse, BarcodeRequest, BarcodeResponse
from app.services import url_service, qr_service, barcode_service
from app.cache.redis_client import redis_client
import os
import json
from slowapi import Limiter
from slowapi.util import get_remote_address

# Create a router for our API endpoints
router = APIRouter()

# Get limiter from app state
limiter = Limiter(key_func=get_remote_address)

# Endpoint to create a short URL
@router.post("/shorten/", response_model=URLResponse, status_code=201)
@limiter.limit("10/minute")
def create_short_url(url_request: URLRequest, request: Request):
    # Get the base URL of our application
    base_url = str(request.base_url)
    # Create a short URL
    result = url_service.create_short_url(url_request.target_url, base_url)
    # Return the result
    return result


# Endpoint to redirect to the original URL
@router.get("/{short_code}")
def redirect_to_url(short_code: str):
    # Get the original URL
    original_url = url_service.handle_redirect(short_code)

    # If not found, return 404 error
    if not original_url:
        raise HTTPException(status_code=404, detail="URL not found")

    # Redirect to the original URL
    return RedirectResponse(url=original_url)


# Endpoint to get information about a short URL
@router.get("/info/{short_code}", response_model=URLResponse)
@limiter.limit("60/minute")
def get_url_info(short_code: str, request: Request):
    # Get the base URL of our application
    base_url = str(request.base_url)
    # Get info about the URL
    result = url_service.get_url_info(short_code, base_url)

    # If not found, return 404 error
    if not result:
        raise HTTPException(status_code=404, detail="URL not found")

    # Return the result
    return result


# QR Code Endpoints

# Endpoint to create a QR code
@router.post("/qrcode/", response_model=QRCodeResponse, status_code=201)
@limiter.limit("10/minute")
def create_qr_code(qr_request: QRCodeRequest, request: Request):
    # Get the base URL of our application
    base_url = str(request.base_url)
    # Create a QR code
    result = qr_service.create_qr_code(qr_request.target_url, base_url)
    # Return the result
    return result


# Endpoint to get QR code image
@router.get("/qrcode/{qr_code_id}/image")
def get_qr_code_image(qr_code_id: str):
    # Check if QR code exists
    result = qr_service.get_qr_code_info(qr_code_id, "")

    # If not found, return 404 error
    if not result:
        raise HTTPException(status_code=404, detail="QR code not found")

    # Path to the QR code image
    image_path = f"static/qrcodes/{qr_code_id}.png"

    # Check if file exists
    if not os.path.isfile(image_path):
        raise HTTPException(status_code=404, detail="QR code image not found")

    # Return the image file
    return FileResponse(image_path)


# Endpoint to redirect from QR code to original URL
@router.get("/qrcode/{qr_code_id}")
def redirect_from_qr_code(qr_code_id: str):
    # Get the original URL
    original_url = qr_service.handle_qr_redirect(qr_code_id)

    # If not found, return 404 error
    if not original_url:
        raise HTTPException(status_code=404, detail="QR code not found")

    # Redirect to the original URL
    return RedirectResponse(url=original_url)


# Endpoint to get information about a QR code
@router.get("/qrcode/info/{qr_code_id}", response_model=QRCodeResponse)
@limiter.limit("60/minute")
def get_qr_code_info(qr_code_id: str, request: Request):
    # Get the base URL of our application
    base_url = str(request.base_url)
    # Get information about the QR code
    result = qr_service.get_qr_code_info(qr_code_id, base_url)

    # If not found, return 404 error
    if not result:
        raise HTTPException(status_code=404, detail="QR code not found")

    # Return the result
    return result


# Barcode Endpoints

# Endpoint to create a barcode
@router.post("/barcode/", response_model=BarcodeResponse, status_code=201)
@limiter.limit("10/minute")
def create_barcode(barcode_request: BarcodeRequest, request: Request):
    # Get the base URL of our application
    base_url = str(request.base_url)
    # Create a barcode
    result = barcode_service.create_barcode(barcode_request.target_url, base_url)
    # Return the result
    return result


# Endpoint to get barcode image
@router.get("/barcode/{barcode_id}/image")
def get_barcode_image(barcode_id: str):
    # Check if barcode exists
    result = barcode_service.get_barcode_info(barcode_id, "")

    # If not found, return 404 error
    if not result:
        raise HTTPException(status_code=404, detail="Barcode not found")

    # Path to the barcode image
    image_path = f"static/barcodes/{barcode_id}.png"

    # Check if file exists
    if not os.path.isfile(image_path):
        raise HTTPException(status_code=404, detail="Barcode image not found")

    # Return the image file
    return FileResponse(image_path)


# Endpoint to redirect from barcode to original URL
@router.get("/barcode/{barcode_id}")
def redirect_from_barcode(barcode_id: str):
    # Get the original URL
    original_url = barcode_service.handle_barcode_redirect(barcode_id)

    # If not found, return 404 error
    if not original_url:
        raise HTTPException(status_code=404, detail="Barcode not found")

    # Redirect to the original URL
    return RedirectResponse(url=original_url)


# Endpoint to get information about a barcode
@router.get("/barcode/info/{barcode_id}", response_model=BarcodeResponse)
@limiter.limit("60/minute")
def get_barcode_info(barcode_id: str, request: Request):
    # Get the base URL of our application
    base_url = str(request.base_url)
    # Get information about the barcode
    result = barcode_service.get_barcode_info(barcode_id, base_url)

    # If not found, return 404 error
    if not result:
        raise HTTPException(status_code=404, detail="Barcode not found")

    # Return the result
    return result