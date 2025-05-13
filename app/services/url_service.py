"""
URL shortening service module.

This module provides core functionality for creating and managing
shortened URLs, including tracking click metrics and handling redirects.
It integrates with Redis for caching and the database for persistent storage.
"""

import random
import string
import json
from app.database import url_db as db
from app.cache.redis_client import redis_client, CACHE_TTL
from app.utils.web_utils import extract_title
import logging

# Set up logging
logger = logging.getLogger(__name__)


# Generate a random code (like abc123)
def generate_random_code(length=6):
    """Generate a random short code for URL shortening.

    Creates a random alphanumeric string with the specified length.

    Args:
        length: Length of the random code (default: 6)

    Returns:
        str: A random alphanumeric string
    """
    # Use letters and numbers
    chars = string.ascii_letters + string.digits
    # Create a random string of characters
    return ''.join(random.choice(chars) for _ in range(length))


# Create a code that isn't already used
def create_unique_code(length=6, max_attempts=10):
    """Create a unique code that isn't already in the database.

    Attempts to generate a random code and checks that it
    doesn't already exist in the database.

    Args:
        length: Length of the random code (default: 6)
        max_attempts: Maximum number of attempts before increasing length (default: 10)

    Returns:
        str: A unique random code not found in the database

    Note:
        If unable to generate a unique code after max_attempts,
        increases the length by 1 and tries again recursively.
    """
    for _ in range(max_attempts):
        short_code = generate_random_code(length)
        if not db.code_exists(short_code):
            return short_code

    # If we get here, try with a longer code
    return create_unique_code(length=length + 1, max_attempts=max_attempts)


# Create a new short URL
def create_short_url(target_url, base_url, user_id=None):
    """Create a new short URL for the given target URL.

    Generates a unique short code, saves the URL mapping in the database,
    and caches the information in Redis.

    Args:
        target_url: The original URL to shorten
        base_url: The base URL of the application (used to construct the short URL)
        user_id: Optional user ID to associate with the shortened URL

    Returns:
        dict: A dictionary containing information about the shortened URL

    Raises:
        Exception: If there's an error in short URL creation
    """
    try:
        # Convert URL to string
        original_url = str(target_url)
        # Generate a unique code
        short_code = create_unique_code()
        # Try to extract the title
        title = extract_title(original_url)

        # Save to database with optional user_id
        db.save_url(original_url, short_code, title, user_id)

        # Get the creation timestamp from database
        created_at = db.get_url_created_at(short_code)
        created_at_str = created_at.isoformat() if created_at else None

        # Prepare response
        result = {
            "original_url": original_url,
            "short_code": short_code,
            "short_url": f"{base_url}{short_code}",
            "title": title,
            "clicks": 0,
            "user_id": user_id,
            "created_at": created_at_str
        }

        # Cache the original URL for redirects
        redis_client.setex(f"url:{short_code}", CACHE_TTL, original_url)

        # Cache the full info response
        redis_client.setex(f"info:{short_code}", CACHE_TTL, json.dumps(result))

        return result
    except Exception as e:
        logger.error(f"Error creating short URL: {e}")
        raise


# Get information about a short URL
def get_url_info(short_code, base_url):
    """Get information about a shortened URL.

    Retrieves details about a short URL including original URL,
    click count, creation time, and associated metadata.

    Args:
        short_code: The short code for the URL
        base_url: The base URL of the application

    Returns:
        dict or None: A dictionary containing URL information if found,
                     None otherwise
    """
    try:
        # Try to get from cache first
        cached_info = redis_client.get(f"info:{short_code}")
        if cached_info:
            info = json.loads(cached_info)

            # Update the click count from the database for accuracy
            result = db.find_by_code(short_code)
            if result:
                info["clicks"] = result[1]  # clicks is the second item in the tuple

                # Refresh cache with updated click count
                redis_client.setex(f"info:{short_code}", CACHE_TTL, json.dumps(info))

            return info

        # Not in cache, get from database
        result = db.find_by_code(short_code)

        # If not found, return None
        if not result:
            return None

        # Extract information
        original_url, clicks, title, user_id, created_at = result

        # Prepare response
        response = {
            "original_url": original_url,
            "short_code": short_code,
            "short_url": f"{base_url}{short_code}",
            "title": title,
            "clicks": clicks,
            "user_id": user_id,
            "created_at": created_at.isoformat() if created_at else None
        }

        # Cache the result
        redis_client.setex(f"info:{short_code}", CACHE_TTL, json.dumps(response))

        return response
    except Exception as e:
        logger.error(f"Error getting URL info: {e}")
        return None


def increment_counter(short_code):
    """Increment the click counter for a short URL.

    Updates both Redis cache and the database with the new click count.
    The database is updated every 10 clicks for efficiency.

    Args:
        short_code: The short code for the URL to increment

    Note:
        If Redis fails, falls back to direct database increment.
    """
    try:
        logger.info(f"Incrementing counter for short_code: {short_code}")

        # Increment in Redis
        redis_client.incr(f"clicks:{short_code}")

        # Get the current count
        clicks_str = redis_client.get(f"clicks:{short_code}")
        clicks = int(clicks_str) if clicks_str else 0
        logger.info(f"New click count in Redis for {short_code}: {clicks}")

        # Update the database every 10 clicks for efficiency
        if clicks % 10 == 0:
            db.update_click_count(short_code, clicks)
            logger.info(f"Updated clicks in database for {short_code}: {clicks}")
    except Exception as e:
        logger.error(f"Error incrementing counter: {e}")
        # If Redis fails, still try to update the database directly
        try:
            db.increment_clicks(short_code)
            logger.info(f"Fallback: directly incremented clicks in database for {short_code}")
        except Exception as db_err:
            logger.error(f"Fallback database update failed: {db_err}")


# Process a redirect and update click count
def handle_redirect(short_code):
    """Process a redirect and update click count.

    Looks up the original URL for a short code, increments the click counter,
    and returns the original URL for redirection.

    Args:
        short_code: The short code to look up

    Returns:
        str or None: The original URL if found, None otherwise

    Note:
        This function checks Redis cache first for performance,
        falling back to the database when needed.
    """
    try:
        logger.info(f"Handling redirect for short_code: {short_code}")

        # Try to get from cache first
        cached_url = redis_client.get(f"url:{short_code}")
        if cached_url:
            logger.info(f"Cache hit for {short_code}")
            # Still update click counter
            increment_counter(short_code)
            return cached_url

        # Not in cache, get from database
        logger.info(f"Cache miss for {short_code}, checking database")
        result = db.find_by_code(short_code)

        # If not found, return None
        if not result:
            logger.warning(f"Short code not found in database: {short_code}")
            return None

        # Get the original URL
        original_url = result[0]
        logger.info(f"Found original URL in database for {short_code}: {original_url[:30]}...")

        # Update cache
        redis_client.setex(f"url:{short_code}", CACHE_TTL, original_url)

        # Increment counter
        increment_counter(short_code)

        # Return the original URL
        return original_url
    except Exception as e:
        logger.error(f"Error handling redirect: {e}")
        # If there's an error, still try to return the URL if we have it
        if 'original_url' in locals():
            return original_url
        return None


# Synchronize click counts from Redis to database for all URLs
def sync_all_click_counts():
    """Synchronize all Redis click counts to the database.

    Retrieves all click counters from Redis and ensures the database
    has the most up-to-date counts. Used for scheduled maintenance
    and admin operations.

    Returns:
        int: The number of URL click counters synchronized

    Note:
        This operation should be run periodically to ensure database accuracy,
        especially if the application is running across multiple instances.
    """
    try:
        logger.info("Starting synchronization of all click counts")
        # Get all Redis keys for click counters
        click_keys = redis_client.keys("clicks:*")

        for key in click_keys:
            short_code = key.split(":")[-1]
            redis_count = redis_client.get(key)

            if redis_count:
                count = int(redis_count)
                logger.info(f"Syncing {short_code}: {count} clicks")

                # Update the database with absolute count
                db.update_click_count(short_code, count)

        logger.info(f"Synchronized {len(click_keys)} URL click counters")
        return len(click_keys)
    except Exception as e:
        logger.error(f"Error synchronizing click counts: {e}")
        return 0