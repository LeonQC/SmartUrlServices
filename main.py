from fastapi import FastAPI
from app.api.url_routes import router as url_router  # Changed from app.api.routes
from app.api.auth_routes import router as auth_router
from app.database.url_db import init_db  # Changed from app.database.db
from app.database.user_db import init_user_db
from dotenv import load_dotenv
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import boto3
from botocore.exceptions import ClientError
import uvicorn

# Load environment variables from .env file
load_dotenv()

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application
app = FastAPI(title="Smart URL")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add our API routes
app.include_router(url_router)  # Changed from 'router'
app.include_router(auth_router)


# Initialize database and check services when the app starts
@app.on_event("startup")
async def startup_event():
    # Initialize URL shortener database tables
    init_db()

    # Initialize user database tables
    init_user_db()

    # Check Redis connection
    from app.cache.redis_client import check_redis
    if not check_redis():
        print("Warning: Redis connection failed. Running without caching.")

    # Check S3 connection
    try:
        # Verify S3 credentials and bucket access
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION", "us-east-1")
        )

        # Check if the bucket exists
        bucket_name = os.environ.get("S3_BUCKET_NAME")
        s3_client.head_bucket(Bucket=bucket_name)

        print(f"Successfully connected to S3 bucket: {bucket_name}")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404':
            print(f"ERROR: S3 bucket {os.environ.get('S3_BUCKET_NAME')} does not exist!")
        elif error_code == '403':
            print("ERROR: No permission to access the S3 bucket. Check your credentials and bucket policies.")
        else:
            print(f"ERROR: S3 connection issue: {e}")
    except Exception as e:
        print(f"ERROR: Failed to connect to S3: {e}")
        print("Check your AWS credentials and S3 bucket configuration.")


# Run the application
if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)