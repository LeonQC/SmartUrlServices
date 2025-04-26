"""
Business logic for QR code generation
"""
import random
import string
import qrcode
import os
import requests
import json
from bs4 import BeautifulSoup
from app.database import db
from app.cache.redis_client import redis_client, CACHE_TTL

# Create a folder for storing QR code images
os.makedirs("static/qrcodes", exist_ok=True)


# Generate a random code (like qr123)
def generate_random_code(length=6):
    # Use letters and numbers
    chars = string.ascii_letters + string.digits
    # Create a random string of 6 characters
    return 'qr_' + ''.join(random.choice(chars) for _ in range(length))


# Create a code that isn't already used
def create_unique_code():
    # Try up to 10 times
    for _ in range(10):
        qr_code_id = generate_random_code()
        # If code isn't in the database, use it
        if not db.qr_code_exists(qr_code_id):
            return qr_code_id

    # If we get here, try with a longer code
    return create_unique_code(length=7)


# Try to extract title from webpage
def extract_title(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.text.strip()
    except Exception:
        pass
    return None


# Create a QR code image and save it
def generate_qr_code_image(url, qr_code_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save the image
    img_path = f"static/qrcodes/{qr_code_id}.png"
    img.save(img_path)

    return img_path


# Create a new QR code
def create_qr_code(target_url, base_url):
    # Convert URL to string
    original_url = str(target_url)
    # Generate a unique code
    qr_code_id = create_unique_code()

    # Try to extract title
    title = extract_title(original_url)

    # Generate the QR code image
    generate_qr_code_image(original_url, qr_code_id)

    # Save to database
    db.save_qr_code(original_url, qr_code_id, title)

    # Prepare response
    result = {
        "original_url": original_url,
        "qr_code_id": qr_code_id,
        "qr_code_url": f"{base_url}qrcode/{qr_code_id}",
        "qr_image_url": f"{base_url}qrcode/{qr_code_id}/image",
        "scans": 0,
        "title": title
    }

    # Cache the original URL for redirects
    redis_client.setex(f"qrcode:{qr_code_id}", CACHE_TTL, original_url)

    # Cache the full info response
    redis_client.setex(f"qrinfo:{qr_code_id}", CACHE_TTL, json.dumps(result))

    return result


# Increment the scan counter
def increment_counter(qr_code_id):
    # Increment in Redis
    redis_client.incr(f"qrscans:{qr_code_id}")
    # Every 10 increments, update the database
    if int(redis_client.get(f"qrscans:{qr_code_id}") or "0") % 10 == 0:
        # Get current count
        count = int(redis_client.get(f"qrscans:{qr_code_id}") or "0")
        # Update database with absolute count
        db.update_qr_scan_count(qr_code_id, count)


# Get information about a QR code
def get_qr_code_info(qr_code_id, base_url):
    # Try to get from cache first
    cached_info = redis_client.get(f"qrinfo:{qr_code_id}")
    if cached_info:
        return json.loads(cached_info)

    # Not in cache, get from database
    result = db.find_qr_code_by_id(qr_code_id)

    # If not found, return None
    if not result:
        return None

    # Extract information
    original_url, scans, title = result

    # Prepare response
    response = {
        "original_url": original_url,
        "qr_code_id": qr_code_id,
        "qr_code_url": f"{base_url}qrcode/{qr_code_id}",
        "qr_image_url": f"{base_url}qrcode/{qr_code_id}/image",
        "scans": scans,
        "title": title
    }

    # Cache the result
    redis_client.setex(f"qrinfo:{qr_code_id}", CACHE_TTL, json.dumps(response))

    return response


# Process a redirect when QR code is scanned
def handle_qr_redirect(qr_code_id):
    # Try to get from cache first
    cached_url = redis_client.get(f"qrcode:{qr_code_id}")
    if cached_url:
        # Still update scan counter
        increment_counter(qr_code_id)
        return cached_url

    # Not in cache, get from database
    result = db.find_qr_code_by_id(qr_code_id)

    # If not found, return None
    if not result:
        return None

    # Get the original URL
    original_url = result[0]

    # Update cache
    redis_client.setex(f"qrcode:{qr_code_id}", CACHE_TTL, original_url)

    # Increment counter
    increment_counter(qr_code_id)

    # Return the original URL
    return original_url