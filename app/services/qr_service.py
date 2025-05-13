"""
QR code generation and management service.

This module provides functionality for creating, managing, and retrieving
QR codes. It leverages the BaseCodeService for common code operations
while implementing QR-specific logic.
"""

import qrcode
import io
import logging
from app.database import url_db as db
from app.utils.web_utils import extract_title
from app.services.base_code_service import BaseCodeService

# Setup logging
logger = logging.getLogger(__name__)

# Create QR service instance
qr_service = BaseCodeService("qr")


# Create a new QR code
def create_qr_code(target_url, base_url, user_id=None):
    """Create a new QR code for a URL.

    Generates a QR code image for the given URL, saves it to S3,
    and records the information in the database.

    Args:
        target_url: The URL that the QR code will redirect to
        base_url: The base URL of the application (used to construct the QR code)
        user_id: Optional user ID to associate with the QR code

    Returns:
        dict: A dictionary containing QR code information including IDs and URLs

    Raises:
        Exception: If there's an error in QR code creation
    """
    try:
        # Convert URL to string to handle Pydantic HttpUrl objects
        target_url = str(target_url)

        logger.debug(f"Creating QR code for URL: {target_url}")

        # Generate a random QR code ID
        qr_code_id = qr_service.generate_random_id()

        # Try to extract the title from the URL
        title = extract_title(target_url)

        # Create a QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"{base_url}qrcode/{qr_code_id}")
        qr.make(fit=True)

        # Create the QR code image
        img = qr.make_image(fill_color="black", back_color="white")

        # Save the image to a BytesIO object
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        # Save to S3 using base service
        qr_service.save_to_s3(img_byte_arr, qr_code_id, user_id)

        # Save QR code in the database with optional user_id
        db.save_qr_code(target_url, qr_code_id, title, user_id)

        # Get the creation timestamp
        created_at = db.get_qr_code_created_at(qr_code_id)
        created_at_str = created_at.isoformat() if created_at else None

        # Create the response object
        response = {
            "original_url": target_url,
            "qr_code_id": qr_code_id,
            "qr_code_url": f"{base_url}qrcode/{qr_code_id}",
            "qr_image_url": f"{base_url}qrcode/{qr_code_id}/image",
            "scans": 0,
            "title": title,
            "user_id": user_id,
            "created_at": created_at_str
        }

        # Cache the QR code info using base service
        qr_service.update_cache(qr_code_id, target_url, response)

        logger.info(f"Created QR code with ID: {qr_code_id}")
        return response
    except Exception as e:
        logger.error(f"Error creating QR code: {e}", exc_info=True)
        raise


# Use the base service's generate_random_id method


# Handle redirection from QR code to original URL
def handle_qr_redirect(qr_code_id):
    """Handle redirection from QR code to original URL.

    Args:
        qr_code_id: The unique identifier for the QR code

    Returns:
        str or None: The original URL if found, None otherwise

    Note:
        This function delegates to the base service implementation
        while maintaining a QR code-specific interface.
    """
    return qr_service.handle_redirect(qr_code_id)


# Get information about a QR code
def get_qr_code_info(qr_code_id, base_url):
    """Get information about a QR code.

    Retrieves detailed QR code information including original URL,
    scan count, and associated metadata.

    Args:
        qr_code_id: The unique identifier for the QR code
        base_url: The base URL to use for constructing QR code URLs

    Returns:
        dict or None: A dictionary containing QR code information if found,
                     None otherwise
    """
    return qr_service.get_code_info(qr_code_id, base_url)


# Get QR code image URL (used by url_routes.py)
def get_qr_code_image_url(qr_code_id):
    """Get the S3 URL for a QR code image.

    Args:
        qr_code_id: The unique identifier for the QR code

    Returns:
        str or None: The S3 URL for the QR code image if found, None otherwise
    """
    return qr_service.get_image_url(qr_code_id)