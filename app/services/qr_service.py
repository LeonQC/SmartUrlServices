"""
Business logic for QR code generation
"""
import qrcode
import random
import string
import io
from app.database import url_db as db
from app.cache.redis_client import redis_client
import json
from app.services.s3_service import upload_file_to_s3, file_exists_in_s3, get_s3_file_url
import requests
from bs4 import BeautifulSoup
import os


# Create a new QR code
def create_qr_code(target_url, base_url):
    # Generate a random QR code ID
    qr_code_id = generate_random_id()

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

    # Upload to S3
    file_path = f"qrcodes/{qr_code_id}.png"
    s3_url = upload_file_to_s3(img_byte_arr.getvalue(), file_path, 'image/png')

    # Save QR code in the database
    db.save_qr_code(target_url, qr_code_id, title)

    # Create the response object
    response = {
        "original_url": target_url,
        "qr_code_id": qr_code_id,
        "qr_code_url": f"{base_url}qrcode/{qr_code_id}",
        "qr_image_url": f"{base_url}qrcode/{qr_code_id}/image",
        "scans": 0,
        "title": title
    }

    # Cache the QR code info
    redis_client.set(f"qrcode:{qr_code_id}", target_url)
    redis_client.set(f"qrinfo:{qr_code_id}", json.dumps(response))
    redis_client.set(f"qrscans:{qr_code_id}", 0)

    return response


# Generate a random ID for QR codes
def generate_random_id(length=8):
    # Generate a random ID of the given length
    characters = string.ascii_letters + string.digits
    random_id = ''.join(random.choice(characters) for _ in range(length))

    # Check if the ID already exists in the database
    while db.qr_code_exists(random_id):
        random_id = ''.join(random.choice(characters) for _ in range(length))

    return random_id


# Extract title from a URL
def extract_title(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')

        if title_tag:
            return title_tag.text.strip()
        else:
            return None
    except Exception as e:
        print(f"Error extracting title: {e}")
        return None


# Handle redirection from QR code to original URL
def handle_qr_redirect(qr_code_id):
    # Try to get the URL from Redis cache
    original_url = redis_client.get(f"qrcode:{qr_code_id}")

    if original_url:
        # Increment the scan counter in Redis
        redis_client.incr(f"qrscans:{qr_code_id}")

        # If the counter is a multiple of 10, update the database
        scans = int(redis_client.get(f"qrscans:{qr_code_id}") or 0)
        if scans % 10 == 0:
            db.update_qr_scan_count(qr_code_id, scans)

        return original_url

    # If not in cache, get from database
    result = db.find_qr_code_by_id(qr_code_id)

    if result:
        original_url, scans, title = result

        # Increment the scan counter
        scans += 1
        db.increment_qr_scans(qr_code_id)

        # Update the cache
        redis_client.set(f"qrcode:{qr_code_id}", original_url)
        redis_client.set(f"qrscans:{qr_code_id}", scans)

        return original_url

    return None


# Get information about a QR code
def get_qr_code_info(qr_code_id, base_url):
    # Try to get from Redis cache
    qr_info = redis_client.get(f"qrinfo:{qr_code_id}")

    if qr_info:
        info = json.loads(qr_info)

        # Update the scan count in the cached info
        scans = int(redis_client.get(f"qrscans:{qr_code_id}") or 0)
        info["scans"] = scans

        return info

    # If not in cache, get from database
    result = db.find_qr_code_by_id(qr_code_id)

    if result:
        original_url, scans, title = result

        # Create response object
        response = {
            "original_url": original_url,
            "qr_code_id": qr_code_id,
            "qr_code_url": f"{base_url}qrcode/{qr_code_id}",
            "qr_image_url": f"{base_url}qrcode/{qr_code_id}/image",
            "scans": scans,
            "title": title
        }

        # Update the cache
        redis_client.set(f"qrinfo:{qr_code_id}", json.dumps(response))
        redis_client.set(f"qrcode:{qr_code_id}", original_url)
        redis_client.set(f"qrscans:{qr_code_id}", scans)

        return response

    return None


# Get QR code image URL (used by url_routes.py)
def get_qr_code_image_url(qr_code_id):
    # Check if QR code exists in database
    if not db.qr_code_exists(qr_code_id):
        return None

    # Generate the file path
    file_path = f"qrcodes/{qr_code_id}.png"

    # Check if the file exists in S3
    if not file_exists_in_s3(file_path):
        return None

    # Return the S3 URL for the image
    return get_s3_file_url(file_path)