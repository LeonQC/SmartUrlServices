import os
import random
import string
import redis
import requests
import json
from bs4 import BeautifulSoup
from app.database import url_db as db
from app.cache.redis_client import redis_client, CACHE_TTL

# Generate a random code (like abc123)
def generate_random_code(length=6):
    # Use letters and numbers
    chars = string.ascii_letters + string.digits
    # Create a random string of 6 characters
    return ''.join(random.choice(chars) for _ in range(length))

# Create a code that isn't already used
def create_unique_code(length=6, max_attempts=10):
    """Create a unique code that isn't already in the database"""
    for _ in range(max_attempts):
        short_code = generate_random_code(length)
        if not db.code_exists(short_code):
            return short_code

    # If we get here, try with a longer code
    return create_unique_code(length=length + 1, max_attempts=max_attempts)

# Create a new short URL
def create_short_url(target_url, base_url):
    # Convert URL to string
    original_url = str(target_url)
    # Generate a unique code
    short_code = create_unique_code()
    # Try to extract the title
    title = extract_title(original_url)

    # Save to database
    db.save_url(original_url, short_code, title)

    # Prepare response
    result = {
        "original_url": original_url,
        "short_code": short_code,
        "short_url": f"{base_url}{short_code}",
        "title": title,
        "clicks": 0
    }

    # Cache the original URL for redirects
    redis_client.setex(f"url:{short_code}", CACHE_TTL, original_url)

    # Cache the full info response
    redis_client.setex(f"info:{short_code}", CACHE_TTL, json.dumps(result))

    return result


# Get information about a short URL
def get_url_info(short_code, base_url):
    # Try to get from cache first
    cached_info = redis_client.get(f"info:{short_code}")
    if cached_info:
        return json.loads(cached_info)

    # Not in cache, get from database
    result = db.find_by_code(short_code)

    # If not found, return None
    if not result:
        return None

    # Extract information
    original_url, clicks, title = result

    # Prepare response
    response = {
        "original_url": original_url,
        "short_code": short_code,
        "short_url": f"{base_url}{short_code}",
        "title": title,
        "clicks": clicks
    }

    # Cache the result
    redis_client.setex(f"info:{short_code}", CACHE_TTL, json.dumps(response))

    return response


def increment_counter(short_code):
    # Increment in Redis
    redis_client.incr(f"clicks:{short_code}")
    # Every 10 increments, update the database
    if int(redis_client.get(f"clicks:{short_code}") or "0") % 10 == 0:
        # Get current count
        count = int(redis_client.get(f"clicks:{short_code}") or "0")
        # Update database with absolute count
        db.update_click_count(short_code, count)


# Process a redirect and update click count
def handle_redirect(short_code):
    # Try to get from cache first
    cached_url = redis_client.get(f"url:{short_code}")
    if cached_url:
        # Still update click counter
        increment_counter(short_code)
        return cached_url

    # Not in cache, get from database
    result = db.find_by_code(short_code)

    # If not found, return None
    if not result:
        return None

    # Get the original URL
    original_url = result[0]

    # Update cache
    redis_client.setex(f"url:{short_code}", CACHE_TTL, original_url)

    # Increment counter
    increment_counter(short_code)

    # Return the original URL
    return original_url

# Extract title from a webpage
def extract_title(url):
    try:
        # Request the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        # Check if request was successful
        if response.status_code == 200:
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            # Find the title tag
            title_tag = soup.find('title')
            # Return the title text if found, otherwise None
            return title_tag.text if title_tag else None
    except Exception:
        # If any error occurs, just return None
        pass
    return None