import random
import string
import requests
from bs4 import BeautifulSoup
from app.database import db

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

    # Return the information
    return {
        "original_url": original_url,
        "short_code": short_code,
        "short_url": f"{base_url}{short_code}",
        "title": title,
        "clicks": 0
    }

# Get information about a short URL
def get_url_info(short_code, base_url):
    # Look up in database
    result = db.find_by_code(short_code)

    # If not found, return None
    if not result:
        return None

    # Extract information
    original_url, clicks, title = result

    # Return the information
    return {
        "original_url": original_url,
        "short_code": short_code,
        "short_url": f"{base_url}{short_code}",
        "title": title,
        "clicks": clicks
    }


# Process a redirect and update click count
def handle_redirect(short_code):
    # Look up in database
    result = db.find_by_code(short_code)

    # If not found, return None
    if not result:
        return None

    # Get the original URL
    original_url = result[0]
    # Increase click counter
    db.increment_clicks(short_code)

    # Return the original URL
    return original_url

# Extract title from a webpage
def extract_title(url):
    try:
        # Request the webpage
        response = requests.get(url, timeout=5)
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