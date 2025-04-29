"""
Business logic for barcode generation
"""
import random
import string
import os
import requests
import json
from bs4 import BeautifulSoup
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw
from app.database import db
from app.cache.redis_client import redis_client, CACHE_TTL

# Create a folder for storing barcode images
os.makedirs("static/barcodes", exist_ok=True)

# Generate a random code (like bar123)
def generate_random_code(length=6):
    # Use letters and numbers
    chars = string.ascii_letters + string.digits
    # Create a random string of 6 characters
    return 'bar_' + ''.join(random.choice(chars) for _ in range(length))

# Create a code that isn't already used
def create_unique_code():
    # Try up to 10 times
    for _ in range(10):
        barcode_id = generate_random_code()
        # If code isn't in the database, use it
        if not db.barcode_exists(barcode_id):
            return barcode_id

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

# Create a barcode image and save it
def generate_barcode_image(url, barcode_id):
    # Use Code128 barcode type for URLs (can encode full ASCII)
    code128 = barcode.get_barcode_class('code128')(barcode_id, writer=ImageWriter())

    # Generate the barcode as PNG
    img_path = f"static/barcodes/{barcode_id}"

    # Save with options
    code128.save(img_path, options={
        'module_height': 15.0,
        'module_width': 0.8,
        'quiet_zone': 6.0,
        'write_text': False  # Don't write text to avoid Pillow errors
    })

    # Rename the file to ensure .png extension
    if os.path.exists(f"{img_path}.png"):
        return f"{img_path}.png"
    elif os.path.exists(f"{img_path}.svg"):
        # If it created an SVG, convert it to PNG
        from cairosvg import svg2png
        with open(f"{img_path}.svg", 'rb') as svg_file:
            svg_content = svg_file.read()

        # Convert SVG to PNG
        png_path = f"{img_path}.png"
        svg2png(bytestring=svg_content, write_to=png_path)

        # Remove the SVG file
        os.remove(f"{img_path}.svg")
        return png_path

    return f"{img_path}.png"

# Increment the scan counter
def increment_counter(barcode_id):
    # Increment in Redis
    redis_client.incr(f"barscans:{barcode_id}")
    # Every 10 increments, update the database
    if int(redis_client.get(f"barscans:{barcode_id}") or "0") % 10 == 0:
        # Get current count
        count = int(redis_client.get(f"barscans:{barcode_id}") or "0")
        # Update database with absolute count
        db.update_barcode_scan_count(barcode_id, count)

# Create a new barcode
def create_barcode(target_url, base_url):
    # Convert URL to string
    original_url = str(target_url)
    # Generate a unique code
    barcode_id = create_unique_code()

    # Try to extract title
    title = extract_title(original_url)

    # Generate the barcode image
    generate_barcode_image(original_url, barcode_id)

    # Save to database
    db.save_barcode(original_url, barcode_id, title)

    # Prepare response
    result = {
        "original_url": original_url,
        "barcode_id": barcode_id,
        "barcode_url": f"{base_url}barcode/{barcode_id}",
        "barcode_image_url": f"{base_url}barcode/{barcode_id}/image",
        "scans": 0,
        "title": title
    }

    # Cache the original URL for redirects
    redis_client.setex(f"barcode:{barcode_id}", CACHE_TTL, original_url)

    # Cache the full info response
    redis_client.setex(f"barinfo:{barcode_id}", CACHE_TTL, json.dumps(result))

    return result

# Get information about a barcode
def get_barcode_info(barcode_id, base_url):
    # Try to get from cache first
    cached_info = redis_client.get(f"barinfo:{barcode_id}")
    if cached_info:
        return json.loads(cached_info)

    # Not in cache, get from database
    result = db.find_barcode_by_id(barcode_id)

    # If not found, return None
    if not result:
        return None

    # Extract information
    original_url, scans, title = result

    # Prepare response
    response = {
        "original_url": original_url,
        "barcode_id": barcode_id,
        "barcode_url": f"{base_url}barcode/{barcode_id}",
        "barcode_image_url": f"{base_url}barcode/{barcode_id}/image",
        "scans": scans,
        "title": title
    }

    # Cache the result
    redis_client.setex(f"barinfo:{barcode_id}", CACHE_TTL, json.dumps(response))

    return response

# Process a redirect when barcode is scanned
def handle_barcode_redirect(barcode_id):
    # Try to get from cache first
    cached_url = redis_client.get(f"barcode:{barcode_id}")
    if cached_url:
        # Still update scan counter
        increment_counter(barcode_id)
        return cached_url

    # Not in cache, get from database
    result = db.find_barcode_by_id(barcode_id)

    # If not found, return None
    if not result:
        return None

    # Get the original URL
    original_url = result[0]

    # Update cache
    redis_client.setex(f"barcode:{barcode_id}", CACHE_TTL, original_url)

    # Increment counter
    increment_counter(barcode_id)

    # Return the original URL
    return original_url