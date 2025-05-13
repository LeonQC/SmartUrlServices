import os
import redis
from dotenv import load_dotenv
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Cache TTL (seconds)
CACHE_TTL = int(os.environ.get("REDIS_TTL", 3600))


try:
    # Get Redis configuration from environment variables
    REDIS_HOST = os.environ.get("REDIS_HOST")
    if REDIS_HOST is None:
        raise EnvironmentError("Missing required environment variable: REDIS_HOST")

    REDIS_PORT = os.environ.get("REDIS_PORT")
    if REDIS_PORT is None:
        raise EnvironmentError("Missing required environment variable: REDIS_PORT")
    REDIS_PORT = int(REDIS_PORT)

    REDIS_SSL = os.environ.get("REDIS_SSL", "false").lower() == "true"

    # Log configuration (without sensitive data)
    logger.info(f"Redis configured with Host: {REDIS_HOST}, Port: {REDIS_PORT}, SSL: {REDIS_SSL}")

    # Configure SSL parameters only if needed
    ssl_params = {}
    if REDIS_SSL:
        ssl_params = {
            "ssl_cert_reqs": "none",
            "ssl_check_hostname": False
        }

    # Create Redis client
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
        **ssl_params
    )

except Exception as e:
    # If Redis connection fails, log the error and create a dummy client
    logger.warning(f"Redis connection setup failed: {e}")


    class DummyRedis:
        """A dummy Redis client that silently performs no-ops for all Redis operations"""

        # Map of method names to their default return values
        DEFAULT_RETURNS = {
            'get': None,
            'exists': 0,
            'ttl': -2,  # Key does not exist
            'incr': 1,
            'setex': True,
            'set': True,
            'delete': True,
            'scan': ("0", []),  # Empty scan result
            'info': {"redis_version": "dummy", "used_memory_human": "0B"},
            'keys': [],
            'type': "none",
            'ping': True,
            'flushdb': True
        }

        def __init__(self):
            self.logger = logging.getLogger(__name__ + ".DummyRedis")
            self.logger.warning("Using DummyRedis client - no actual Redis operations will be performed")

        def __getattr__(self, name):
            def dummy_method(*args, **kwargs):
                self.logger.debug(f"DummyRedis: {name}({args}, {kwargs})")
                # Return appropriate default value or None
                return self.DEFAULT_RETURNS.get(name)


    redis_client = DummyRedis()
    logger.warning("Using DummyRedis client as fallback - caching disabled")


def check_redis():
    """Check if Redis is available and working"""
    try:
        result = redis_client.ping()
        logger.info(f"Redis connection check: {'Successful' if result else 'Failed'}")
        return result
    except Exception as e:
        logger.error(f"Redis connection check failed: {e}")
        return False


def clear_prefix(prefix):
    """Clear all keys with a given prefix"""
    try:
        keys = redis_client.keys(f"{prefix}*")
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} keys with prefix '{prefix}'")
            return len(keys)
        return 0
    except Exception as e:
        logger.error(f"Error clearing keys with prefix '{prefix}': {e}")
        return 0


def get_cache_stats():
    """Get basic statistics about Redis usage"""
    try:
        info = redis_client.info()
        stats = {
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            "total_keys": len(redis_client.keys("*"))
        }

        # Calculate hit rate if available
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total_ops = hits + misses

        if total_ops > 0:
            stats["hit_rate"] = hits / total_ops
        else:
            stats["hit_rate"] = 0

        return stats
    except Exception as e:
        logger.error(f"Error getting Redis stats: {e}")
        return {"error": str(e)}
