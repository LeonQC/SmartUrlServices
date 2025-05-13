from pydantic import BaseModel
from typing import List, Optional

class UrlHistoryItem(BaseModel):
    """URL history item model"""
    original_url: str
    short_code: str
    short_url: str
    title: Optional[str] = None
    clicks: int
    created_at: str

class QrCodeHistoryItem(BaseModel):
    """QR code history item model"""
    original_url: str
    qr_code_id: str
    qr_code_url: str
    title: Optional[str] = None
    scans: int
    created_at: str

class BarcodeHistoryItem(BaseModel):
    """Barcode history item model"""
    original_url: str
    barcode_id: str
    barcode_url: str
    title: Optional[str] = None
    scans: int
    created_at: str

class UrlHistoryResponse(BaseModel):
    """URL history response model"""
    page: int
    limit: int
    total: int
    urls: List[UrlHistoryItem]

class QrCodeHistoryResponse(BaseModel):
    """QR code history response model"""
    page: int
    limit: int
    total: int
    qrcodes: List[QrCodeHistoryItem]

class BarcodeHistoryResponse(BaseModel):
    """Barcode history response model"""
    page: int
    limit: int
    total: int
    barcodes: List[BarcodeHistoryItem]