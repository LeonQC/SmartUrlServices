"""
Base service for code generation and management.

This module provides a common foundation for QR code and barcode services,
implementing shared functionality like ID generation, redirection handling,
and S3 image storage.
"""

import random
import string
import io
import json
import logging
from app.database import url_db as db
from app.cache.redis_client import redis_client, CACHE_TTL
from app.services.s3_service import upload_file_to_s3, file_exists_in_s3, get_s3_file_url

# Setup logging
logger = logging.getLogger(__name__)


class BaseCodeService:
    """Base service class for code generation operations.

    This class provides common functionality for different types of codes
    (QR codes, barcodes) including random ID generation, database operations,
    caching, and S3 storage management.
    """

    def __init__(self, code_type):
        """Initialize base service with code type.

        Args:
            code_type: Type of code ('qr' or 'barcode')

        Note:
            This will configure appropriate cache key prefixes and database
            functions based on the code type.
        """
        self.code_type = code_type
        self.cache_key_prefix = f"{code_type}code" if code_type == "qr" else "barcode"
        self.info_key_prefix = f"{code_type}info" if code_type == "qr" else "barinfo"
        self.scans_key_prefix = f"{code_type}scans" if code_type == "qr" else "barscans"
        self.storage_dir = f"{code_type}codes" if code_type == "qr" else "barcodes"
        
        # Map functions based on code type
        if code_type == 'qr':
            self.id_field = 'qr_code_id'
            self.code_exists_func = db.qr_code_exists
            self.find_by_id_func = db.find_qr_code_by_id
            self.update_scan_count_func = db.update_qr_scan_count
            self.increment_scans_func = db.increment_qr_scans
            self.url_prefix = 'qrcode'
        else:
            self.id_field = 'barcode_id'
            self.code_exists_func = db.barcode_exists
            self.find_by_id_func = db.find_barcode_by_id
            self.update_scan_count_func = db.update_barcode_scan_count
            self.increment_scans_func = db.increment_barcode_scans
            self.url_prefix = 'barcode'

    def generate_random_id(self, length=8):
        """Generate a random ID and check against database.

        Args:
            length: Length of the random ID to generate (default: 8)

        Returns:
            str: A unique random ID that doesn't exist in the database

        Note:
            This method ensures the generated ID is unique by checking
            against existing IDs in the database.
        """
        characters = string.ascii_letters + string.digits
        random_id = ''.join(random.choice(characters) for _ in range(length))
        
        # Check if the ID already exists in the database
        while self.code_exists_func(random_id):
            random_id = ''.join(random.choice(characters) for _ in range(length))
        
        return random_id

    def handle_redirect(self, code_id):
        """Handle redirection from code to original URL.

        This method retrieves the original URL for a given code ID,
        increments the scan counter, and updates relevant caches.

        Args:
            code_id: The unique identifier for the code

        Returns:
            str or None: The original URL if found, None otherwise

        Note:
            This method handles both Redis cache and database lookups,
            with fallback if the cache is unavailable.
        """
        try:
            logger.debug(f"Handling {self.code_type} code redirect for ID: {code_id}")
            
            # Try to get the URL from Redis cache
            cache_key = f"{self.cache_key_prefix}:{code_id}"
            original_url = redis_client.get(cache_key)
            
            if original_url:
                # Increment the scan counter in Redis
                scans_key = f"{self.scans_key_prefix}:{code_id}"
                redis_client.incr(scans_key)
                
                # If the counter is a multiple of 10, update the database
                scans = int(redis_client.get(scans_key) or "0")
                if scans % 10 == 0:
                    self.update_scan_count_func(code_id, scans)
                    logger.debug(f"Updated scan count in database for {self.code_type} code {code_id}: {scans}")
                
                return original_url
            
            # If not in cache, get from database
            logger.debug(f"{self.code_type.upper()} code ID {code_id} not found in cache, checking database")
            result = self.find_by_id_func(code_id)
            
            if result:
                original_url, scans, title = result[0:3]
                
                # Increment the scan counter
                scans += 1
                self.increment_scans_func(code_id)
                
                # Update the cache
                redis_client.setex(cache_key, CACHE_TTL, original_url)
                redis_client.setex(f"{self.scans_key_prefix}:{code_id}", CACHE_TTL, str(scans))
                
                logger.debug(f"{self.code_type.upper()} code ID {code_id} found in database, redirecting to {original_url}")
                return original_url
            
            logger.warning(f"{self.code_type.upper()} code ID {code_id} not found in database")
            return None
        except Exception as e:
            logger.error(f"Error handling {self.code_type} code redirect: {e}")
            # If there's an error but we already retrieved the original URL, return it
            if 'original_url' in locals():
                return original_url
            return None

    def get_code_info(self, code_id, base_url):
        """Get information about a code.

        Retrieves detailed information about a code, including its
        original URL, scan count, creation time, and associated metadata.

        Args:
            code_id: The unique identifier for the code
            base_url: The base URL to use for constructing full URLs

        Returns:
            dict or None: A dictionary containing code information if found,
                         None otherwise

        Note:
            This method checks Redis cache first before falling back to the database.
            The returned information includes URLs for both the code itself and its image.
        """
        try:
            logger.debug(f"Getting information for {self.code_type} code ID: {code_id}")
            
            # Try to get from Redis cache
            info_key = f"{self.info_key_prefix}:{code_id}"
            code_info = redis_client.get(info_key)
            
            if code_info:
                info = json.loads(code_info)
                
                # Update the scan count in the cached info
                scans_key = f"{self.scans_key_prefix}:{code_id}"
                scans_str = redis_client.get(scans_key)
                if scans_str:
                    try:
                        scans = int(scans_str)
                        info["scans"] = scans
                    except (ValueError, TypeError):
                        pass  # If conversion fails, keep the original value
                
                return info
            
            # If not in cache, get from database
            logger.debug(f"{self.code_type.upper()} code ID {code_id} not found in cache, checking database")
            result = self.find_by_id_func(code_id)
            
            if result:
                original_url, scans, title, user_id, created_at = result
                
                # Create response object
                if self.code_type == "qr":
                    response = {
                        "original_url": original_url,
                        "qr_code_id": code_id,
                        "qr_code_url": f"{base_url}qrcode/{code_id}",
                        "qr_image_url": f"{base_url}qrcode/{code_id}/image",
                        "scans": scans,
                        "title": title,
                        "user_id": user_id,
                        "created_at": created_at.isoformat() if created_at else None
                    }
                else:
                    response = {
                        "original_url": original_url,
                        "barcode_id": code_id,
                        "barcode_url": f"{base_url}barcode/{code_id}",
                        "barcode_image_url": f"{base_url}barcode/{code_id}/image",
                        "scans": scans,
                        "title": title,
                        "user_id": user_id,
                        "created_at": created_at.isoformat() if created_at else None
                    }
                
                # Update the cache
                redis_client.setex(info_key, CACHE_TTL, json.dumps(response))
                redis_client.setex(f"{self.cache_key_prefix}:{code_id}", CACHE_TTL, original_url)
                redis_client.setex(f"{self.scans_key_prefix}:{code_id}", CACHE_TTL, str(scans))
                
                logger.debug(f"{self.code_type.upper()} code ID {code_id} found in database and cached")
                return response
            
            logger.warning(f"{self.code_type.upper()} code ID {code_id} not found in database")
            return None
        except Exception as e:
            logger.error(f"Error getting {self.code_type} code info: {e}")
            return None

    def get_image_url(self, code_id):
        """Get code image URL from S3.

        Retrieves the S3 URL for the image associated with a code.

        Args:
            code_id: The unique identifier for the code

        Returns:
            str or None: The S3 URL for the image if found, None otherwise

        Note:
            This method first checks if the code exists in the database,
            then verifies that the image file exists in S3 before returning the URL.
        """
        try:
            logger.debug(f"Getting {self.code_type} code image URL for ID: {code_id}")
            
            # Check if code exists in database
            if not self.code_exists_func(code_id):
                logger.warning(f"{self.code_type.upper()} code ID {code_id} does not exist")
                return None
            
            # Generate the file path
            file_path = f"{self.storage_dir}/{code_id}.png"
            
            # Check if the file exists in S3
            if not file_exists_in_s3(file_path):
                logger.warning(f"{self.code_type.upper()} code image not found in S3: {file_path}")
                return None
            
            # Return the S3 URL for the image
            image_url = get_s3_file_url(file_path)
            logger.debug(f"{self.code_type.upper()} code image URL for ID {code_id}: {image_url}")
            return image_url
        except Exception as e:
            logger.error(f"Error getting {self.code_type} code image URL: {e}")
            return None

    def save_to_s3(self, img_byte_arr, code_id, user_id=None):
        """Save code image to S3.

        Uploads the code image to S3, with optional user-specific copy.

        Args:
            img_byte_arr: BytesIO object containing the image data
            code_id: The unique identifier for the code
            user_id: Optional user ID to create a user-specific copy of the image

        Note:
            If user_id is provided, the image is saved to both a user-specific path
            and a general path. This facilitates easier cleanup when a user is deleted.
        """
        # Upload to S3 - add user ID to path if available
        file_path = f"{self.storage_dir}/{code_id}.png"
        if user_id:
            # Keep a copy in the user's directory for easy cleanup
            user_file_path = f"{self.storage_dir}/user_{user_id}/{code_id}.png"
            # Upload both copies
            upload_file_to_s3(img_byte_arr.getvalue(), user_file_path, 'image/png')
            img_byte_arr.seek(0)  # Reset position after read
        
        # Always upload the main file that will be served
        upload_file_to_s3(img_byte_arr.getvalue(), file_path, 'image/png')

    def update_cache(self, code_id, target_url, response):
        """Update Redis cache with code information.

        Stores various code-related data in Redis for quick access.

        Args:
            code_id: The unique identifier for the code
            target_url: The original URL that the code redirects to
            response: The full response object containing code metadata

        Note:
            This method sets separate cache entries for the target URL,
            the full response object, and the initial scan count.
            All entries use the configured CACHE_TTL.
        """
        redis_client.setex(f"{self.cache_key_prefix}:{code_id}", CACHE_TTL, target_url)
        redis_client.setex(f"{self.info_key_prefix}:{code_id}", CACHE_TTL, json.dumps(response))
        redis_client.setex(f"{self.scans_key_prefix}:{code_id}", CACHE_TTL, "0")