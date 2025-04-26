from pydantic import BaseModel, HttpUrl

class URLRequest(BaseModel):
    """What users send when creating a short URL"""
    target_url: HttpUrl  # This ensures we only accept valid URLs

class URLResponse(BaseModel):
    """What we send back to users"""
    original_url: str    # The original long URL
    short_code: str      # The random code (like abc123)
    short_url: str       # The complete short URL
    title: str = None  # The title of the webpage (optional)
    clicks: int          # How many times it's been used

# QR Code Models
class QRCodeRequest(BaseModel):
    """What users send when creating a QR code"""
    target_url: HttpUrl  # This ensures we only accept valid URLs

class QRCodeResponse(BaseModel):
    """What we send back to users"""
    original_url: str  # The original URL
    qr_code_id: str  # The unique ID for this QR code
    qr_code_url: str  # The URL to view the QR code
    qr_image_url: str  # The URL to get the QR code image
    scans: int  # How many times it's been scanned
    title: str = None  # Title of the website (if available)

# Barcode Models
class BarcodeRequest(BaseModel):
    """What users send when creating a barcode"""
    target_url: HttpUrl  # This ensures we only accept valid URLs

class BarcodeResponse(BaseModel):
    """What we send back to users"""
    original_url: str    # The original URL
    barcode_id: str      # The unique ID for this barcode
    barcode_url: str     # The URL to view the barcode
    barcode_image_url: str # The URL to get the barcode image
    scans: int           # How many times it's been scanned
    title: str = None    # Title of the website (if available)