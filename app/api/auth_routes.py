from fastapi import APIRouter, HTTPException, status, Depends, Response, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from app.models.user_schema import (
    UserCreate, UserResponse, TokenResponse, UserLogin,
    UserGoogle, RefreshTokenRequest, TokenRefreshResponse,
    UserProfileResponse, UserProfileUpdate, DeleteAccountRequest
)
from app.database import user_db
from typing import Optional
import logging
import os
import json
from dotenv import load_dotenv
from app.cache.redis_client import redis_client

# Load environment variables
load_dotenv()

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
TESTING_MODE = os.environ.get("TESTING_MODE", "false").lower() == "true"

# Setup logging
logger = logging.getLogger(__name__)

# Create a router for auth endpoints
router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 password bearer token for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Security scheme for admin endpoints
security = HTTPBearer()


# --- Helper Functions ---

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current user from the token"""
    payload = user_db.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    user = user_db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def verify_google_token(token: str):
    """Verify Google ID token and extract user info"""
    try:
        # For testing mode, use test credentials
        if TESTING_MODE and token == "test_token":
            logger.warning("Using test Google authentication - NOT FOR PRODUCTION")
            return {
                "google_id": os.environ.get("GOOGLE_TEST_ID", "google_test_123456789"),
                "email": os.environ.get("GOOGLE_TEST_EMAIL", "test@example.com"),
                "name": os.environ.get("GOOGLE_TEST_NAME", "testuser").replace(" ", "").lower()
            }

        if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID == "placeholder_will_be_replaced_later":
            # For development without a client ID set
            logger.warning("Using dummy Google authentication as no client ID is set")
            return {
                "google_id": "google123456789",
                "email": "user@example.com",
                "name": "userexample"
            }

        # Import Google libraries
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
        except ImportError:
            logger.error("Google auth libraries not installed. Run: pip install google-auth google-auth-oauthlib")
            raise ValueError("Google authentication libraries not installed")

        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid token issuer')

        # Get user info
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', '').replace(' ', '').lower()

        # Verify email is verified
        if not idinfo.get('email_verified', False):
            raise ValueError('Email not verified by Google')

        return {
            "google_id": google_id,
            "email": email,
            "name": name
        }

    except ImportError:
        logger.error("Google auth libraries not installed")
        # Fallback to dummy implementation for development
        return {
            "google_id": "dummy_google_id",
            "email": "dummy@example.com",
            "name": "dummyuser"
        }
    except ValueError as e:
        logger.error(f"Google token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in Google token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication error: {str(e)}"
        )


# --- Authentication Endpoints ---

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user with username and password"""
    try:
        # Check if username or email already exists
        if user_db.username_exists(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        if user_db.email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user
        user = user_db.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/google", response_model=TokenResponse)
async def google_auth(token_data: UserGoogle):
    """Authenticate or register a user with Google OAuth"""
    try:
        # Verify the Google token and get user information
        google_user = await verify_google_token(token_data.token)

        # Create or get user based on Google ID
        user = user_db.create_google_user(
            email=google_user["email"],
            google_id=google_user["google_id"],
            username=google_user["name"]
        )

        # Generate tokens
        tokens = user_db.generate_tokens(user["id"])

        # Combine user and tokens for response
        response = {
            **tokens,
            "user": user
        }

        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Log in a user with username and password"""
    # Authenticate user
    user = user_db.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Generate tokens
    tokens = user_db.generate_tokens(user["id"])

    # Cache the user data
    try:
        cache_key = f"user:{user['id']}"
        redis_client.setex(cache_key, 3600, json.dumps(user))  # Cache for 1 hour
    except Exception as e:
        logger.error(f"Error caching user data: {e}")

    # Combine user and tokens for response
    response = {
        **tokens,
        "user": user
    }

    return response


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """Refresh an access token using a refresh token"""
    # Verify the refresh token
    payload = user_db.verify_token(refresh_request.refresh_token, token_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Generate a new access token
    user_id = payload.get("sub")

    # Make sure user still exists
    user = user_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    new_tokens = user_db.generate_tokens(user_id)

    # Return only the access token information
    return {
        "access_token": new_tokens["access_token"],
        "token_type": new_tokens["token_type"],
        "expires_in": new_tokens["expires_in"]
    }


@router.post("/logout")
async def logout(response: Response):
    """Log out a user (client-side)"""
    # For JWT, logout is handled client-side by removing the tokens
    # Here we can help by instructing the client to remove any cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    return {"message": "Successfully logged out"}


# --- User Profile Endpoints ---

@router.get("/users/me", response_model=UserProfileResponse)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get the current user's profile"""
    # Get user statistics
    stats = user_db.get_user_stats(current_user["id"])

    # Combine user profile and stats
    return {
        **current_user,
        "stats": stats
    }


@router.patch("/users/me", response_model=UserResponse)
async def update_user_profile(
        profile_update: UserProfileUpdate,
        current_user: dict = Depends(get_current_user)
):
    """Update the current user's profile"""
    try:
        updated_user = user_db.update_user_profile(
            user_id=current_user["id"],
            username=profile_update.username,
            email=profile_update.email
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
        delete_request: DeleteAccountRequest = None,
        current_user: dict = Depends(get_current_user)
):
    """Delete the current user's account and all associated data"""
    try:
        # Check if the user authenticated via OAuth
        if current_user.get("auth_provider"):
            # OAuth users don't have passwords, so just delete them
            success = user_db.delete_oauth_user(current_user["id"])
        else:
            # Regular users need to confirm with password
            if not delete_request or not delete_request.password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password required to delete account"
                )

            success = user_db.delete_user(current_user["id"], delete_request.password)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password"
                )

        # If deletion was successful, return 204 No Content
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account deletion failed: {str(e)}"
        )


# --- Admin Cache Management Endpoints ---

@router.get("/admin/cache/stats")
async def get_cache_stats(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get statistics about the cache usage"""
    # Verify admin token (you should implement proper admin authorization)
    try:
        token = credentials.credentials
        payload = user_db.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check if user is admin (implement proper admin check)
        user_id = payload.get("sub")
        user = user_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Get cache stats
        stats = CacheManager.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/admin/cache/clear/{entity_type}")
async def clear_cache(
        entity_type: str,
        entity_id: Optional[int] = None,
        credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Clear cache for a specific entity type"""
    # Verify admin token (implement proper admin authorization)
    try:
        token = credentials.credentials
        payload = user_db.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check if user is admin (implement proper admin check)
        user_id = payload.get("sub")
        user = user_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Clear specified cache
        if entity_type == "user" and entity_id:
            result = CacheManager.clear_user_cache(entity_id)
            return {"success": result, "message": f"Cleared cache for user {entity_id}"}
        elif entity_type == "users":
            count = CacheManager.clear_all_user_caches()
            return {"success": True, "message": f"Cleared {count} user cache entries"}
        elif entity_type == "all":
            # Clear all caches
            from app.cache.redis_client import redis_client
            redis_client.flushdb()
            return {"success": True, "message": "Cleared all caches"}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/admin/redis/info")
async def redis_info(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get Redis server information"""
    # Verify admin token (implement proper admin authorization)
    try:
        token = credentials.credentials
        payload = user_db.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check if user is admin (implement proper admin check)
        user_id = payload.get("sub")
        user = user_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Get Redis info
        from app.cache.redis_client import redis_client
        info = redis_client.info()

        # Filter out sensitive information
        hit_rate = 0
        if info.get("keyspace_hits") is not None and info.get("keyspace_misses") is not None:
            total = info.get("keyspace_hits") + info.get("keyspace_misses")
            hit_rate = info.get("keyspace_hits") / total if total > 0 else 0

        safe_info = {
            "redis_version": info.get("redis_version"),
            "uptime_in_seconds": info.get("uptime_in_seconds"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "total_connections_received": info.get("total_connections_received"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "hit_rate": hit_rate,
        }

        return safe_info
    except Exception as e:
        logger.error(f"Error getting Redis info: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")