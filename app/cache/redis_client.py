import os
import redis
import json

# Configure Redis connection
redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

# Cache TTL in seconds (default: 1 hour)
CACHE_TTL = int(os.environ.get("REDIS_TTL", 3600))

# Test Redis connection
def check_redis():
    try:
        redis_client.ping()
        return True
    except redis.exceptions.ConnectionError:
        return False