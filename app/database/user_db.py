import psycopg2
import bcrypt
import jwt
import time
import json
import hashlib
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from app.database.url_db import get_db
from app.cache.redis_client import redis_client, CACHE_TTL

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-for-jwt")
JWT_ACCESS_EXPIRE = int(os.getenv("JWT_ACCESS_EXPIRE", 3600))  # 1 hour
JWT_REFRESH_EXPIRE = int(os.getenv("JWT_REFRESH_EXPIRE", 604800))  # 7 days
JWT_ALGORITHM = "HS256"

# Cache TTLs for different user data (in seconds)
USER_CACHE_TTL = 3600  # 1 hour
USER_STATS_CACHE_TTL = 300  # 5 minutes
USER_LIST_CACHE_TTL = 600  # 10 minutes
TOKEN_VERIFY_CACHE_TTL = 300  # 5 minutes

# Redis key prefixes
USER_KEY_PREFIX = "user:"
USERNAME_KEY_PREFIX = "username:"
EMAIL_KEY_PREFIX = "email:"
USER_STATS_KEY_PREFIX = "user_stats:"
TOKEN_KEY_PREFIX = "token:"


# Initialize user table when the app starts
def init_user_db():
    # Connect to database
    conn = get_db()
    cursor = conn.cursor()

    # Create user table if it doesn't exist
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS users
                   (
                       id
                       SERIAL
                       PRIMARY
                       KEY,
                       username
                       TEXT
                       UNIQUE
                       NOT
                       NULL,
                       email
                       TEXT
                       UNIQUE
                       NOT
                       NULL,
                       password_hash
                       TEXT,
                       auth_provider
                       TEXT,
                       auth_provider_id
                       TEXT,
                       created_at
                       TIMESTAMP
                       NOT
                       NULL
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       updated_at
                       TIMESTAMP
                       NOT
                       NULL
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   """)

    # Add indexes for faster lookups
    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_username ON users (username)
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_email ON users (email)
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS idx_auth_provider ON users (auth_provider, auth_provider_id)
                   """)

    # Save changes and close connection
    conn.commit()
    cursor.close()
    conn.close()


# Check if a username already exists
def username_exists(username):
    """Check if username exists with Redis caching"""
    try:
        # Try cache first
        cache_key = f"{USERNAME_KEY_PREFIX}{username}"
        cached_result = redis_client.get(cache_key)

        if cached_result is not None:
            return cached_result == "1"

        # Not in cache, check database
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        result = cursor.fetchone() is not None

        cursor.close()
        conn.close()

        # Cache the result
        redis_client.setex(cache_key, USER_CACHE_TTL, "1" if result else "0")

        return result
    except Exception as e:
        logger.error(f"Error checking if username exists: {e}")
        # Fallback to database
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        result = cursor.fetchone() is not None

        cursor.close()
        conn.close()
        return result


# Check if an email already exists
def email_exists(email):
    """Check if email exists with Redis caching"""
    try:
        # Try cache first
        cache_key = f"{EMAIL_KEY_PREFIX}{email}"
        cached_result = redis_client.get(cache_key)

        if cached_result is not None:
            return cached_result == "1"

        # Not in cache, check database
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        result = cursor.fetchone() is not None

        cursor.close()
        conn.close()

        # Cache the result
        redis_client.setex(cache_key, USER_CACHE_TTL, "1" if result else "0")

        return result
    except Exception as e:
        logger.error(f"Error checking if email exists: {e}")
        # Fallback to database
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        result = cursor.fetchone() is not None

        cursor.close()
        conn.close()
        return result


# Create a new user in the database with local authentication
def create_user(username, email, password):
    conn = get_db()
    cursor = conn.cursor()

    # Hash the password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, auth_provider, auth_provider_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id, created_at
            """,
            (username, email, password_hash, None, None)
        )

        user_id, created_at = cursor.fetchone()
        conn.commit()

        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "auth_provider": None,
            "created_at": created_at.isoformat()
        }

        # Cache the new user
        try:
            redis_client.setex(f"{USER_KEY_PREFIX}{user_id}", USER_CACHE_TTL, json.dumps(user_data))
            redis_client.setex(f"{USERNAME_KEY_PREFIX}{username}", USER_CACHE_TTL, "1")
            redis_client.setex(f"{EMAIL_KEY_PREFIX}{email}", USER_CACHE_TTL, "1")
            logger.info(f"Cached new user data for user ID: {user_id}")
        except Exception as e:
            logger.error(f"Error caching new user: {e}")
            # Continue even if caching fails

        return user_data
    except psycopg2.Error as e:
        conn.rollback()
        if e.pgcode == '23505':  # Unique violation
            if 'users_username_key' in str(e):
                raise ValueError("Username already exists")
            elif 'users_email_key' in str(e):
                raise ValueError("Email already exists")
        raise e
    finally:
        cursor.close()
        conn.close()


# Create or update a user with Google authentication
def create_google_user(email, google_id, username=None):
    # If no username is provided, generate one from the email prefix
    if not username:
        username = email.split('@')[0]

    # Ensure username is unique
    base_username = username
    i = 1
    while username_exists(username):
        username = f"{base_username}_{i}"
        i += 1

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Check if user with this Google ID already exists
        cursor.execute(
            "SELECT id, username, email, created_at FROM users WHERE auth_provider = %s AND auth_provider_id = %s",
            ("google", google_id)
        )
        existing_user = cursor.fetchone()

        if existing_user:
            # User exists, return the user data
            user_id, db_username, db_email, created_at = existing_user
            user_data = {
                "id": user_id,
                "username": db_username,
                "email": db_email,
                "auth_provider": "google",
                "created_at": created_at.isoformat()
            }

            # Cache the user data
            try:
                redis_client.setex(f"{USER_KEY_PREFIX}{user_id}", USER_CACHE_TTL, json.dumps(user_data))
                logger.info(f"Cached existing Google user data for user ID: {user_id}")
            except Exception as e:
                logger.error(f"Error caching existing Google user: {e}")

            return user_data

        # Check if email already exists with different auth provider
        cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            raise ValueError("Email already exists with different authentication provider")

        # Create new user
        cursor.execute(
            """
            INSERT INTO users (username, email, auth_provider, auth_provider_id)
            VALUES (%s, %s, %s, %s) RETURNING id, created_at
            """,
            (username, email, "google", google_id)
        )

        user_id, created_at = cursor.fetchone()
        conn.commit()

        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "auth_provider": "google",
            "created_at": created_at.isoformat()
        }

        # Cache the new user
        try:
            redis_client.setex(f"{USER_KEY_PREFIX}{user_id}", USER_CACHE_TTL, json.dumps(user_data))
            redis_client.setex(f"{USERNAME_KEY_PREFIX}{username}", USER_CACHE_TTL, "1")
            redis_client.setex(f"{EMAIL_KEY_PREFIX}{email}", USER_CACHE_TTL, "1")
            logger.info(f"Cached new Google user data for user ID: {user_id}")
        except Exception as e:
            logger.error(f"Error caching new Google user: {e}")

        return user_data
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


# Authenticate a user by username and password
def authenticate_user(username, password):
    conn = get_db()
    cursor = conn.cursor()

    # Try to find user by username
    cursor.execute(
        "SELECT id, password_hash, email, created_at, auth_provider FROM users WHERE username = %s",
        (username,)
    )
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    # User not found
    if not user:
        return None

    user_id, password_hash, email, created_at, auth_provider = user

    # OAuth user attempting local login
    if auth_provider:
        return None

    # Verify password
    if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "auth_provider": None,
            "created_at": created_at.isoformat()
        }

        # Cache the user data on successful login
        try:
            redis_client.setex(f"{USER_KEY_PREFIX}{user_id}", USER_CACHE_TTL, json.dumps(user_data))
            logger.info(f"Cached user data after login for user ID: {user_id}")
        except Exception as e:
            logger.error(f"Error caching user data after login: {e}")

        return user_data

    # Password incorrect
    return None


# Get a user by their ID
def get_user_by_id(user_id):
    """Get a user by their ID with Redis caching"""
    try:
        # Try to get from cache first
        cache_key = f"{USER_KEY_PREFIX}{user_id}"
        cached_user = redis_client.get(cache_key)

        if cached_user:
            logger.debug(f"Cache hit for user ID: {user_id}")
            return json.loads(cached_user)

        # Not in cache, get from database
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, email, created_at, auth_provider FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if not user:
            return None

        user_id, username, email, created_at, auth_provider = user
        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "auth_provider": auth_provider,
            "created_at": created_at.isoformat()
        }

        # Cache the result
        redis_client.setex(cache_key, USER_CACHE_TTL, json.dumps(user_data))
        logger.debug(f"Cached user data for user ID: {user_id}")

        return user_data
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        # If Redis fails, still try to get from database directly
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, email, created_at, auth_provider FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if not user:
            return None

        user_id, username, email, created_at, auth_provider = user
        return {
            "id": user_id,
            "username": username,
            "email": email,
            "auth_provider": auth_provider,
            "created_at": created_at.isoformat()
        }


# Get user statistics
def get_user_stats(user_id):
    """Get user statistics with Redis caching"""
    try:
        # Try cache first
        cache_key = f"{USER_STATS_KEY_PREFIX}{user_id}"
        cached_stats = redis_client.get(cache_key)

        if cached_stats:
            logger.debug(f"Cache hit for user stats ID: {user_id}")
            return json.loads(cached_stats)

        # Not in cache, get from database
        conn = get_db()
        cursor = conn.cursor()

        # Count URLs created by user
        cursor.execute("SELECT COUNT(*) FROM urls WHERE user_id = %s", (user_id,))
        urls_count = cursor.fetchone()[0]

        # Count QR codes created by user
        cursor.execute("SELECT COUNT(*) FROM qrcodes WHERE user_id = %s", (user_id,))
        qr_codes_count = cursor.fetchone()[0]

        # Count barcodes created by user
        cursor.execute("SELECT COUNT(*) FROM barcodes WHERE user_id = %s", (user_id,))
        barcodes_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        stats = {
            "urls_created": urls_count,
            "qr_codes_created": qr_codes_count,
            "barcodes_created": barcodes_count
        }

        # Cache the result (shorter TTL as stats change more frequently)
        redis_client.setex(cache_key, USER_STATS_CACHE_TTL, json.dumps(stats))
        logger.debug(f"Cached user stats for user ID: {user_id}")

        return stats
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        # Fallback to database
        conn = get_db()
        cursor = conn.cursor()

        # Count URLs created by user
        cursor.execute("SELECT COUNT(*) FROM urls WHERE user_id = %s", (user_id,))
        urls_count = cursor.fetchone()[0]

        # Count QR codes created by user
        cursor.execute("SELECT COUNT(*) FROM qrcodes WHERE user_id = %s", (user_id,))
        qr_codes_count = cursor.fetchone()[0]

        # Count barcodes created by user
        cursor.execute("SELECT COUNT(*) FROM barcodes WHERE user_id = %s", (user_id,))
        barcodes_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return {
            "urls_created": urls_count,
            "qr_codes_created": qr_codes_count,
            "barcodes_created": barcodes_count
        }


# Update user profile
def update_user_profile(user_id, username=None, email=None):
    conn = get_db()
    cursor = conn.cursor()

    # Start constructing the SQL query and parameters
    update_fields = []
    params = []

    if username is not None:
        update_fields.append("username = %s")
        params.append(username)

    if email is not None:
        update_fields.append("email = %s")
        params.append(email)

    # Only proceed if there are fields to update
    if not update_fields:
        cursor.close()
        conn.close()
        return get_user_by_id(user_id)

    # Add updated_at field
    update_fields.append("updated_at = CURRENT_TIMESTAMP")

    # Complete the query
    query = f"""
        UPDATE users 
        SET {", ".join(update_fields)}
        WHERE id = %s
        RETURNING id, username, email, created_at, auth_provider
    """
    params.append(user_id)

    try:
        cursor.execute(query, params)
        user = cursor.fetchone()
        conn.commit()

        if not user:
            return None

        user_id, username, email, created_at, auth_provider = user
        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "auth_provider": auth_provider,
            "created_at": created_at.isoformat()
        }

        # Invalidate caches
        try:
            # Invalidate user cache
            redis_client.delete(f"{USER_KEY_PREFIX}{user_id}")

            # If username was updated, invalidate username cache
            if "username = %s" in update_fields:
                redis_client.delete(f"{USERNAME_KEY_PREFIX}{username}")

            # If email was updated, invalidate email cache
            if "email = %s" in update_fields:
                redis_client.delete(f"{EMAIL_KEY_PREFIX}{email}")

            # Update user cache with new data
            redis_client.setex(f"{USER_KEY_PREFIX}{user_id}", USER_CACHE_TTL, json.dumps(user_data))
            logger.info(f"Updated cache for user {user_id} after profile update")
        except Exception as e:
            logger.error(f"Error updating user cache: {e}")

        return user_data
    except psycopg2.Error as e:
        conn.rollback()
        if e.pgcode == '23505':  # Unique violation
            if 'users_username_key' in str(e):
                raise ValueError("Username already exists")
            elif 'users_email_key' in str(e):
                raise ValueError("Email already exists")
        raise e
    finally:
        cursor.close()
        conn.close()


# Generate JWT tokens for a user
def generate_tokens(user_id):
    """Generate JWT tokens for a user"""
    current_time = int(time.time())

    # Create access token
    access_token_payload = {
        "sub": str(user_id),
        "iat": current_time,
        "exp": current_time + JWT_ACCESS_EXPIRE,
        "token_type": "access"  # Explicitly set token type
    }
    access_token = jwt.encode(access_token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    # Create refresh token
    refresh_token_payload = {
        "sub": str(user_id),
        "iat": current_time,
        "exp": current_time + JWT_REFRESH_EXPIRE,
        "token_type": "refresh"  # Explicitly set token type
    }
    refresh_token = jwt.encode(refresh_token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_EXPIRE
    }


def verify_token(token, token_type=None):
    """Verify and decode JWT token with Redis caching"""
    try:
        # Create a unique cache key that includes the token type
        token_hash = hashlib.md5(token.encode()).hexdigest()
        cache_key = f"{TOKEN_KEY_PREFIX}{token_hash}:{token_type or 'access'}"

        # Try to get the verified payload from cache
        cached_payload = redis_client.get(cache_key)

        if cached_payload:
            return json.loads(cached_payload)

        # Not in cache, verify the token
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            # Check if the token is of the expected type
            if token_type == "refresh" and payload.get("token_type") != "refresh":
                return None

            # Cache the verified payload
            redis_client.setex(cache_key, TOKEN_VERIFY_CACHE_TTL, json.dumps(payload))

            return payload
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Token is invalid
            return None
        except Exception as e:
            # Other errors
            logger.error(f"Unexpected error verifying token: {e}")
            return None

    except Exception as e:
        logger.error(f"Error using Redis for token verification: {e}")
        # Fall back to non-cached verification
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            # Check if the token is of the expected type
            if token_type == "refresh" and payload.get("token_type") != "refresh":
                return None

            return payload
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Token is invalid
            return None
        except Exception as e:
            # Other errors
            logger.error(f"Unexpected error verifying token: {e}")
            return None


# Delete a user and all their associated data
def delete_user(user_id, password=None):
    """
    Delete a user and all their associated data.

    Args:
        user_id: The ID of the user to delete
        password: If provided, verify password before deletion

    Returns:
        bool: True if user was successfully deleted, False otherwise
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Start a transaction
        conn.autocommit = False

        # If password is provided, verify it first
        if password:
            cursor.execute(
                "SELECT password_hash FROM users WHERE id = %s",
                (user_id,)
            )
            result = cursor.fetchone()

            if not result:
                return False  # User not found

            password_hash = result[0]

            # If user uses OAuth, they won't have a password
            if not password_hash:
                return False  # Cannot verify password for OAuth users

            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                return False  # Password incorrect

        # Delete user's files from S3
        from app.services.s3_service import delete_user_files
        delete_user_files(user_id)

        # Delete user's URLs
        cursor.execute("DELETE FROM urls WHERE user_id = %s", (user_id,))

        # Delete user's QR codes
        cursor.execute("DELETE FROM qrcodes WHERE user_id = %s", (user_id,))

        # Delete user's barcodes
        cursor.execute("DELETE FROM barcodes WHERE user_id = %s", (user_id,))

        # Get user data for cache invalidation
        cursor.execute(
            "SELECT username, email FROM users WHERE id = %s",
            (user_id,)
        )
        user_data = cursor.fetchone()

        # Finally, delete the user
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

        # Commit the transaction
        conn.commit()

        # Invalidate caches
        try:
            # Invalidate all user related caches
            redis_client.delete(f"{USER_KEY_PREFIX}{user_id}")
            redis_client.delete(f"{USER_STATS_KEY_PREFIX}{user_id}")

            if user_data:
                username, email = user_data
                redis_client.delete(f"{USERNAME_KEY_PREFIX}{username}")
                redis_client.delete(f"{EMAIL_KEY_PREFIX}{email}")

            logger.info(f"Invalidated cache for deleted user {user_id}")
        except Exception as e:
            logger.error(f"Error invalidating cache for deleted user: {e}")

        return True

    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        logger.error(f"Error deleting user: {e}")
        return False

    finally:
        # Reset autocommit and close connection
        conn.autocommit = True
        cursor.close()
        conn.close()


def delete_oauth_user(user_id):
    """
    Delete a user authenticated via OAuth (no password verification)

    Args:
        user_id: The ID of the user to delete

    Returns:
        bool: True if user was successfully deleted, False otherwise
    """
    return delete_user(user_id)