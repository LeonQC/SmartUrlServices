from fastapi import FastAPI
from app.api.routes import router
from app.database.db import init_db
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables from .env file
load_dotenv()

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application
app = FastAPI(title="Smart URL")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add our API routes
app.include_router(router)
# Mount static directory for serving QR code images
os.makedirs("static/qrcodes", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
os.makedirs("static/barcodes", exist_ok=True)

# Initialize database when the app starts
@app.on_event("startup")
async def startup_event():
    init_db()

    # Check Redis connection
    from app.cache.redis_client import check_redis
    if not check_redis():
        print("Warning: Redis connection failed. Running without caching.")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)