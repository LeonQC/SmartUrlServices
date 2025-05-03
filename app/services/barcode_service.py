"""
Business logic for barcode generation
"""
import random
import string
import io
from app.database import url_db as db
from app.cache.redis_client import redis_client
import json
import requests
from bs4 import BeautifulSoup
import barcode
from barcode.writer import ImageWriter
from app.services.s3_service import upload_file_to_s3, file_exists_in_s3, get_s3_file_url


# Create a new barcode
def create_barcode(target_url, base_url):
    # Generate a random barcode ID
    barcode_id = generate_random_id()

    # Try to extract the title from the URL
    title = extract_title(target_url)

    # Create a barcode (Code128 is a versatile barcode format)
    code128 = barcode.get('code128', f"{base_url}barcode/{barcode_id}", writer=ImageWriter())

    # Save the barcode to a BytesIO object
    img_byte_arr = io.BytesIO()
    code128.write(img_byte_arr, options={'write_text': False})
    img_byte_arr.seek(0)

    # Upload to S3
    file_path = f"barcodes/{barcode_id}.png"
    s3_url = upload_file_to_s3(img_byte_arr.getvalue(), file_path, 'image/png')

    # Save barcode in the database
    db.save_barcode(target_url, barcode_id, title)

    # Create the response object
    response = {
        "original_url": target_url,
        "barcode_id": barcode_id,
        "barcode_url": f"{base_url}barcode/{barcode_id}",
        "barcode_image_url": f"{base_url}barcode/{barcode_id}/image",
        "scans": 0,
        "title": title
    }

    # Cache the barcode info
    redis_client.set(f"barcode:{barcode_id}", target_url)
    redis_client.set(f"barinfo:{barcode_id}", json.dumps(response))
    redis_client.set(f"barscans:{barcode_id}", 0)

    return response


# Generate a random ID for barcodes
def generate_random_id(length=8):
    # Generate a random ID of the given length
    characters = string.ascii_letters + string.digits
    random_id = ''.join(random.choice(characters) for _ in range(length))

    # Check if the ID already exists in the database
    while db.barcode_exists(random_id):
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


# Handle redirection from barcode to original URL
def handle_barcode_redirect(barcode_id):
    # Try to get the URL from Redis cache
    original_url = redis_client.get(f"barcode:{barcode_id}")

    if original_url:
        # Increment the scan counter in Redis
        redis_client.incr(f"barscans:{barcode_id}")

        # If the counter is a multiple of 10, update the database
        scans = int(redis_client.get(f"barscans:{barcode_id}") or 0)
        if scans % 10 == 0:
            db.update_barcode_scan_count(barcode_id, scans)

        return original_url

    # If not in cache, get from database
    result = db.find_barcode_by_id(barcode_id)

    if result:
        original_url, scans, title = result

        # Increment the scan counter
        scans += 1
        db.increment_barcode_scans(barcode_id)

        # Update the cache
        redis_client.set(f"barcode:{barcode_id}", original_url)
        redis_client.set(f"barscans:{barcode_id}", scans)

        return original_url

    return None


# Get information about a barcode
def get_barcode_info(barcode_id, base_url):
    # Try to get from Redis cache
    barcode_info = redis_client.get(f"barinfo:{barcode_id}")

    if barcode_info:
        info = json.loads(barcode_info)

        # Update the scan count in the cached info
        scans = int(redis_client.get(f"barscans:{barcode_id}") or 0)
        info["scans"] = scans

        return info

    # If not in cache, get from database
    result = db.find_barcode_by_id(barcode_id)

    if result:
        original_url, scans, title = result

        # Create response object
        response = {
            "original_url": original_url,
            "barcode_id": barcode_id,
            "barcode_url": f"{base_url}barcode/{barcode_id}",
            "barcode_image_url": f"{base_url}barcode/{barcode_id}/image",
            "scans": scans,
            "title": title
        }

        # Update the cache
        redis_client.set(f"barinfo:{barcode_id}", json.dumps(response))
        redis_client.set(f"barcode:{barcode_id}", original_url)
        redis_client.set(f"barscans:{barcode_id}", scans)

        return response

    return None


# Get barcode image URL (used by url_routes.py)
def get_barcode_image_url(barcode_id):
    # Check if barcode exists in database
    if not db.barcode_exists(barcode_id):
        return None

    # Generate the file path
    file_path = f"barcodes/{barcode_id}.png"

    # Check if the file exists in S3
    if not file_exists_in_s3(file_path):
        # Could implement recovery logic here
        return None

    # Return the S3 URL for the image
    return get_s3_file_url(file_path)