from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from app.models.url_schemas import URLRequest, URLResponse, QRCodeRequest, QRCodeResponse, BarcodeRequest, \
    BarcodeResponse
from app.services import url_service, qr_service, barcode_service
from app.cache.redis_client import redis_client
from app.api.auth_routes import get_current_user, oauth2_scheme
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

# Setup logging
logger = logging.getLogger(__name__)

# Create a router for our API endpoints
router = APIRouter()

# Get limiter from app state
limiter = Limiter(key_func=get_remote_address)


# --- URL Endpoints ---

@router.post("/shorten/", response_model=URLResponse, status_code=201)
@limiter.limit("10/minute")
async def create_short_url(
        url_request: URLRequest,
        request: Request,
        token: Optional[str] = Depends(oauth2_scheme)
):
    """Create a short URL from a long URL. If authenticated, associate with user."""
    try:
        # Get the base URL of our application
        base_url = str(request.base_url)

        # Initialize user_id as None (for unauthenticated users)
        user_id = None

        # If token is provided, get user_id from token
        if token:
            try:
                current_user = await get_current_user(token)
                user_id = current_user["id"]
            except:
                # If authentication fails, continue as unauthenticated
                pass

        # Create a short URL with optional user_id
        result = url_service.create_short_url(url_request.target_url, base_url, user_id)

        # Return the result
        return result
    except Exception as e:
        logger.error(f"Error creating short URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to create short URL")


# Endpoint to redirect to the original URL
@router.get("/{short_code}")
def redirect_to_url(short_code: str):
    """Redirect from short code to original URL"""
    try:
        # Get the original URL
        original_url = url_service.handle_redirect(short_code)

        # If not found, return 404 error
        if not original_url:
            raise HTTPException(status_code=404, detail="URL not found")

        # Redirect to the original URL
        return RedirectResponse(url=original_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error redirecting: {e}")
        raise HTTPException(status_code=500, detail="Redirect failed")


# Endpoint to get information about a short URL
@router.get("/info/{short_code}", response_model=URLResponse)
@limiter.limit("60/minute")
def get_url_info(short_code: str, request: Request):
    """Get information about a short URL"""
    try:
        # Get the base URL of our application
        base_url = str(request.base_url)
        # Get info about the URL
        result = url_service.get_url_info(short_code, base_url)

        # If not found, return 404 error
        if not result:
            raise HTTPException(status_code=404, detail="URL not found")

        # Return the result
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting URL info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get URL information")


# --- QR Code Endpoints ---

@router.post("/qrcode/", response_model=QRCodeResponse, status_code=201)
@limiter.limit("10/minute")
async def create_qr_code(
        qr_request: QRCodeRequest,
        request: Request,
        token: Optional[str] = Depends(oauth2_scheme)
):
    """Create a QR code for a URL. If authenticated, associate with user."""
    try:
        # Get the base URL of our application
        base_url = str(request.base_url)

        # Initialize user_id as None (for unauthenticated users)
        user_id = None

        # If token is provided, get user_id from token
        if token:
            try:
                current_user = await get_current_user(token)
                user_id = current_user["id"]
            except:
                # If authentication fails, continue as unauthenticated
                pass

        # Create a QR code with optional user_id
        result = qr_service.create_qr_code(qr_request.target_url, base_url, user_id)

        # Return the result
        return result
    except Exception as e:
        logger.error(f"Error creating QR code: {e}")
        raise HTTPException(status_code=500, detail="Failed to create QR code")


# Endpoint to get QR code image
@router.get("/qrcode/{qr_code_id}/image")
def get_qr_code_image(qr_code_id: str):
    """Get QR code image and redirect to S3 storage"""
    try:
        # Check if QR code exists
        result = qr_service.get_qr_code_info(qr_code_id, "")

        # If not found, return 404 error
        if not result:
            raise HTTPException(status_code=404, detail="QR code not found")

        # Get the S3 URL for the QR code image
        image_url = qr_service.get_qr_code_image_url(qr_code_id)

        if not image_url:
            raise HTTPException(status_code=404, detail="QR code image not found")

        # Redirect to the S3 URL
        return RedirectResponse(url=image_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting QR code image: {e}")
        raise HTTPException(status_code=500, detail="Failed to get QR code image")


# Endpoint to redirect from QR code to original URL
@router.get("/qrcode/{qr_code_id}")
def redirect_from_qr_code(qr_code_id: str):
    """Redirect from QR code to original URL"""
    try:
        # Get the original URL
        original_url = qr_service.handle_qr_redirect(qr_code_id)

        # If not found, return 404 error
        if not original_url:
            raise HTTPException(status_code=404, detail="QR code not found")

        # Redirect to the original URL
        return RedirectResponse(url=original_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error redirecting from QR code: {e}")
        raise HTTPException(status_code=500, detail="Redirect failed")


# Endpoint to get information about a QR code
@router.get("/qrcode/info/{qr_code_id}", response_model=QRCodeResponse)
@limiter.limit("60/minute")
def get_qr_code_info(qr_code_id: str, request: Request):
    """Get information about a QR code"""
    try:
        # Get the base URL of our application
        base_url = str(request.base_url)
        # Get information about the QR code
        result = qr_service.get_qr_code_info(qr_code_id, base_url)

        # If not found, return 404 error
        if not result:
            raise HTTPException(status_code=404, detail="QR code not found")

        # Return the result
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting QR code info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get QR code information")


# --- Barcode Endpoints ---

@router.post("/barcode/", response_model=BarcodeResponse, status_code=201)
@limiter.limit("10/minute")
async def create_barcode(
        barcode_request: BarcodeRequest,
        request: Request,
        token: Optional[str] = Depends(oauth2_scheme)
):
    """Create a barcode for a URL. If authenticated, associate with user."""
    try:
        # Get the base URL of our application
        base_url = str(request.base_url)

        # Initialize user_id as None (for unauthenticated users)
        user_id = None

        # If token is provided, get user_id from token
        if token:
            try:
                current_user = await get_current_user(token)
                user_id = current_user["id"]
            except:
                # If authentication fails, continue as unauthenticated
                pass

        # Create a barcode with optional user_id
        result = barcode_service.create_barcode(barcode_request.target_url, base_url, user_id)

        # Return the result
        return result
    except Exception as e:
        logger.error(f"Error creating barcode: {e}")
        raise HTTPException(status_code=500, detail="Failed to create barcode")


# Endpoint to get barcode image
@router.get("/barcode/{barcode_id}/image")
def get_barcode_image(barcode_id: str):
    """Get barcode image and redirect to S3 storage"""
    try:
        # Check if barcode exists
        result = barcode_service.get_barcode_info(barcode_id, "")

        # If not found, return 404 error
        if not result:
            raise HTTPException(status_code=404, detail="Barcode not found")

        # Get the S3 URL for the barcode image
        image_url = barcode_service.get_barcode_image_url(barcode_id)

        if not image_url:
            raise HTTPException(status_code=404, detail="Barcode image not found")

        # Redirect to the S3 URL
        return RedirectResponse(url=image_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting barcode image: {e}")
        raise HTTPException(status_code=500, detail="Failed to get barcode image")


# Endpoint to redirect from barcode to original URL
@router.get("/barcode/{barcode_id}")
def redirect_from_barcode(barcode_id: str):
    """Redirect from barcode to original URL"""
    try:
        # Get the original URL
        original_url = barcode_service.handle_barcode_redirect(barcode_id)

        # If not found, return 404 error
        if not original_url:
            raise HTTPException(status_code=404, detail="Barcode not found")

        # Redirect to the original URL
        return RedirectResponse(url=original_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error redirecting from barcode: {e}")
        raise HTTPException(status_code=500, detail="Redirect failed")


# Endpoint to get information about a barcode
@router.get("/barcode/info/{barcode_id}", response_model=BarcodeResponse)
@limiter.limit("60/minute")
def get_barcode_info(barcode_id: str, request: Request):
    """Get information about a barcode"""
    try:
        # Get the base URL of our application
        base_url = str(request.base_url)
        # Get information about the barcode
        result = barcode_service.get_barcode_info(barcode_id, base_url)

        # If not found, return 404 error
        if not result:
            raise HTTPException(status_code=404, detail="Barcode not found")

        # Return the result
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting barcode info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get barcode information")
# Admin endpoint to sync click counts
@router.get("/admin/sync-clicks")
@limiter.limit("1/minute")
def sync_click_counts(request: Request):
    """Synchronize all click counts from Redis to database"""
    try:
        from app.services.url_service import sync_all_click_counts
        count = sync_all_click_counts()
        return {"status": "success", "message": f"Synchronized {count} URL click counts"}
    except Exception as e:
        logger.error(f"Error in sync endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error synchronizing click counts")
