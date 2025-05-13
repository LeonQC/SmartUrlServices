"""
Barcode generation and management service.

This module provides functionality for creating, managing, and retrieving
barcodes (specifically Code128 barcodes). It leverages the BaseCodeService
for common code operations while implementing barcode-specific logic.
"""

import io
import logging
from app.database import url_db as db
import barcode
from barcode.writer import ImageWriter
from app.utils.web_utils import extract_title
from app.services.base_code_service import BaseCodeService

# Setup logging
logger = logging.getLogger(__name__)

# Create barcode service instance
barcode_service_base = BaseCodeService("barcode")


# Create a new barcode
def create_barcode(target_url, base_url, user_id=None):
    """Create a new barcode for a URL.

    Generates a Code128 barcode image for the given URL, saves it to S3,
    and records the information in the database.

    Args:
        target_url: The URL that the barcode will redirect to
        base_url: The base URL of the application (used to construct the barcode)
        user_id: Optional user ID to associate with the barcode

    Returns:
        dict: A dictionary containing barcode information including IDs and URLs

    Raises:
        Exception: If there's an error in barcode creation
    """
    try:
        # Convert URL to string to handle Pydantic HttpUrl objects
        target_url = str(target_url)

        logger.debug(f"Creating barcode for URL: {target_url}")

        # Generate a random barcode ID
        barcode_id = barcode_service_base.generate_random_id()

        # Try to extract the title from the URL
        title = extract_title(target_url)

        # Create a barcode (Code128 is a versatile barcode format)
        code128 = barcode.get('code128', f"{base_url}barcode/{barcode_id}", writer=ImageWriter())

        # Save the barcode to a BytesIO object
        img_byte_arr = io.BytesIO()
        code128.write(img_byte_arr, options={'write_text': False})
        img_byte_arr.seek(0)

        # Save to S3 using base service
        barcode_service_base.save_to_s3(img_byte_arr, barcode_id, user_id)

        # Save barcode in the database with optional user_id
        db.save_barcode(target_url, barcode_id, title, user_id)

        # Get the creation timestamp
        created_at = db.get_barcode_created_at(barcode_id)
        created_at_str = created_at.isoformat() if created_at else None

        # Create the response object
        response = {
            "original_url": target_url,
            "barcode_id": barcode_id,
            "barcode_url": f"{base_url}barcode/{barcode_id}",
            "barcode_image_url": f"{base_url}barcode/{barcode_id}/image",
            "scans": 0,
            "title": title,
            "user_id": user_id,
            "created_at": created_at_str
        }

        # Cache the barcode info using base service
        barcode_service_base.update_cache(barcode_id, target_url, response)

        logger.info(f"Created barcode with ID: {barcode_id}")
        return response
    except Exception as e:
        logger.error(f"Error creating barcode: {e}", exc_info=True)
        raise


# Use the base service's generate_random_id method


# Handle redirection from barcode to original URL
def handle_barcode_redirect(barcode_id):
    """Handle redirection from barcode to original URL.

    Args:
        barcode_id: The unique identifier for the barcode

    Returns:
        str or None: The original URL if found, None otherwise

    Note:
        This function delegates to the base service implementation
        while maintaining a barcode-specific interface.
    """
    return barcode_service_base.handle_redirect(barcode_id)


# Get information about a barcode
def get_barcode_info(barcode_id, base_url):
    """Get information about a barcode.

    Retrieves detailed barcode information including original URL,
    scan count, and associated metadata.

    Args:
        barcode_id: The unique identifier for the barcode
        base_url: The base URL to use for constructing barcode URLs

    Returns:
        dict or None: A dictionary containing barcode information if found,
                     None otherwise
    """
    return barcode_service_base.get_code_info(barcode_id, base_url)


# Get barcode image URL (used by url_routes.py)
def get_barcode_image_url(barcode_id):
    """Get the S3 URL for a barcode image.

    Args:
        barcode_id: The unique identifier for the barcode

    Returns:
        str or None: The S3 URL for the barcode image if found, None otherwise
    """
    return barcode_service_base.get_image_url(barcode_id)