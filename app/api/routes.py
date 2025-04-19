from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.models.schemas import URLRequest, URLResponse
from app.services import url_service

# Create a router for our API endpoints
router = APIRouter()

# Endpoint to create a short URL
@router.post("/shorten/", response_model=URLResponse, status_code=201)
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
def get_url_info(short_code: str, request: Request):
    # Get the base URL of our application
    base_url = str(request.base_url)
    # Get information about the short URL
    result = url_service.get_url_info(short_code, base_url)

    # If not found, return 404 error
    if not result:
        raise HTTPException(status_code=404, detail="URL not found")

    # Return the result
    return result