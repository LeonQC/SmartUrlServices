from fastapi import APIRouter, Depends, Query, HTTPException, Request
from app.api.auth_routes import get_current_user
from app.database import history_db
from app.models.history_schema import (
    UrlHistoryResponse, QrCodeHistoryResponse, BarcodeHistoryResponse
)
from typing import Optional

# Create router for history endpoints
router = APIRouter(tags=["History"])


@router.get("/urls/history", response_model=UrlHistoryResponse)
async def get_url_history(
        request: Request,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        sort: str = Query("created_at", description="Sort field (created_at or clicks)"),
        order: str = Query("desc", description="Sort order (asc or desc)"),
        current_user: dict = Depends(get_current_user)
):
    """Get the history of URLs created by the current user"""
    # Validate sort field
    if sort not in ["created_at", "clicks"]:
        raise HTTPException(status_code=400, detail="Invalid sort field. Must be 'created_at' or 'clicks'")

    # Validate sort order
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort order. Must be 'asc' or 'desc'")

    # Get base URL for constructing complete URLs
    base_url = str(request.base_url)

    # Get URL history
    history_data = history_db.get_url_history(
        user_id=current_user["id"],
        page=page,
        limit=limit,
        sort_field=sort,
        sort_order=order,
        base_url=base_url
    )

    return history_data


@router.get("/qrcodes/history", response_model=QrCodeHistoryResponse)
async def get_qrcode_history(
        request: Request,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        sort: str = Query("created_at", description="Sort field (created_at or scans)"),
        order: str = Query("desc", description="Sort order (asc or desc)"),
        current_user: dict = Depends(get_current_user)
):
    """Get the history of QR codes created by the current user"""
    # Validate sort field
    if sort not in ["created_at", "scans"]:
        raise HTTPException(status_code=400, detail="Invalid sort field. Must be 'created_at' or 'scans'")

    # Validate sort order
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort order. Must be 'asc' or 'desc'")

    # Get base URL for constructing complete URLs
    base_url = str(request.base_url)

    # Get QR code history
    history_data = history_db.get_qrcode_history(
        user_id=current_user["id"],
        page=page,
        limit=limit,
        sort_field=sort,
        sort_order=order,
        base_url=base_url
    )

    return history_data


@router.get("/barcodes/history", response_model=BarcodeHistoryResponse)
async def get_barcode_history(
        request: Request,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        sort: str = Query("created_at", description="Sort field (created_at or scans)"),
        order: str = Query("desc", description="Sort order (asc or desc)"),
        current_user: dict = Depends(get_current_user)
):
    """Get the history of barcodes created by the current user"""
    # Validate sort field
    if sort not in ["created_at", "scans"]:
        raise HTTPException(status_code=400, detail="Invalid sort field. Must be 'created_at' or 'scans'")

    # Validate sort order
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort order. Must be 'asc' or 'desc'")

    # Get base URL for constructing complete URLs
    base_url = str(request.base_url)

    # Get barcode history
    history_data = history_db.get_barcode_history(
        user_id=current_user["id"],
        page=page,
        limit=limit,
        sort_field=sort,
        sort_order=order,
        base_url=base_url
    )

    return history_data