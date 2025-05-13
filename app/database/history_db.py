import json
import logging
from app.database.url_db import get_db
from app.cache.redis_client import redis_client

# Setup logging
logger = logging.getLogger(__name__)

# Cache TTL for history data (60 seconds, as they change often)
HISTORY_CACHE_TTL = 60


def _get_history_data(entity_type, user_id, page=1, limit=20, sort_field='created_at',
                     sort_order='desc', base_url=None):
    """Helper function to retrieve history data with common functionality.

    This function provides a common implementation for retrieving history data
    for different entity types (URLs, QR codes, barcodes). It handles caching,
    pagination, sorting, and database fallback.

    Args:
        entity_type: The type of entity ('url', 'qrcode', or 'barcode')
        user_id: The user ID to get history for
        page: Page number for pagination (default: 1)
        limit: Number of items per page (default: 20)
        sort_field: Field to sort by (default: 'created_at')
        sort_order: Order to sort by ('asc' or 'desc', default: 'desc')
        base_url: Base URL for constructing full URLs (default: None)

    Returns:
        dict: Dictionary containing paginated history data with the structure:
            {
                "page": <current_page>,
                "limit": <items_per_page>,
                "total": <total_items>,
                "<entity_type>s": [<items>]
            }

    Note:
        This function attempts to retrieve data from Redis cache first
        before falling back to database queries. Results are cached for
        HISTORY_CACHE_TTL seconds.
    """
    # Map entity types to their database table names and valid sort fields
    entity_config = {
        'url': {
            'table': 'urls',
            'id_field': 'short_code',
            'url_prefix': '',
            'result_key': 'urls',
            'sort_fields': ['created_at', 'clicks'],
            'count_field': 'clicks'
        },
        'qrcode': {
            'table': 'qrcodes',
            'id_field': 'qr_code_id',
            'url_prefix': 'qrcode/',
            'result_key': 'qrcodes',
            'sort_fields': ['created_at', 'scans'],
            'count_field': 'scans'
        },
        'barcode': {
            'table': 'barcodes',
            'id_field': 'barcode_id',
            'url_prefix': 'barcode/',
            'result_key': 'barcodes',
            'sort_fields': ['created_at', 'scans'],
            'count_field': 'scans'
        }
    }

    # Get config for this entity type
    config = entity_config[entity_type]

    try:
        # Create a cache key based on all parameters
        cache_key = f"history:{entity_type}:{user_id}:{page}:{limit}:{sort_field}:{sort_order}"

        # Try to get from cache
        cached_history = redis_client.get(cache_key)
        if cached_history:
            logger.debug(f"Cache hit for {entity_type} history: {cache_key}")
            return json.loads(cached_history)

        # Not in cache, calculate from database
        conn = get_db()
        cursor = conn.cursor()

        # Validate sort field to prevent SQL injection
        if sort_field not in config['sort_fields']:
            sort_field = 'created_at'

        # Validate sort order to prevent SQL injection
        valid_sort_orders = ['asc', 'desc']
        if sort_order.lower() not in valid_sort_orders:
            sort_order = 'desc'

        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Get total count for pagination
        cursor.execute(f"SELECT COUNT(*) FROM {config['table']} WHERE user_id = %s", (user_id,))
        total = cursor.fetchone()[0]

        # Get paginated items with sorting
        id_field = config['id_field']
        count_field = config['count_field']

        query = f"""
            SELECT original_url, {id_field}, title, {count_field}, created_at
            FROM {config['table']}
            WHERE user_id = %s
            ORDER BY {sort_field} {sort_order}
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, (user_id, limit, offset))
        items = cursor.fetchall()

        cursor.close()
        conn.close()

        # Use provided base_url or default
        if not base_url:
            base_url = "http://localhost:8000/"

        # Format the response
        item_list = []
        for item in items:
            original_url, item_id, title, count, created_at = item
            item_list.append({
                "original_url": original_url,
                f"{entity_type}_id" if entity_type != 'url' else "short_code": item_id,
                f"{entity_type}_url" if entity_type != 'url' else "short_url": f"{base_url}{config['url_prefix']}{item_id}",
                "title": title,
                count_field: count,
                "created_at": created_at.isoformat()
            })

        result = {
            "page": page,
            "limit": limit,
            "total": total,
            config['result_key']: item_list
        }

        # Cache the result (shorter TTL as history changes frequently)
        redis_client.setex(cache_key, HISTORY_CACHE_TTL, json.dumps(result))
        logger.debug(f"Cached {entity_type} history: {cache_key}")

        return result
    except Exception as e:
        logger.error(f"Error getting {entity_type} history: {e}")

        # Fall back to database query without caching
        conn = get_db()
        cursor = conn.cursor()

        # Validate sort field to prevent SQL injection
        if sort_field not in config['sort_fields']:
            sort_field = 'created_at'

        # Validate sort order to prevent SQL injection
        valid_sort_orders = ['asc', 'desc']
        if sort_order.lower() not in valid_sort_orders:
            sort_order = 'desc'

        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Get total count for pagination
        cursor.execute(f"SELECT COUNT(*) FROM {config['table']} WHERE user_id = %s", (user_id,))
        total = cursor.fetchone()[0]

        # Get paginated items with sorting
        id_field = config['id_field']
        count_field = config['count_field']

        query = f"""
            SELECT original_url, {id_field}, title, {count_field}, created_at
            FROM {config['table']}
            WHERE user_id = %s
            ORDER BY {sort_field} {sort_order}
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, (user_id, limit, offset))
        items = cursor.fetchall()

        cursor.close()
        conn.close()

        # Use provided base_url or default
        if not base_url:
            base_url = "http://localhost:8000/"

        # Format the response
        item_list = []
        for item in items:
            original_url, item_id, title, count, created_at = item
            item_list.append({
                "original_url": original_url,
                f"{entity_type}_id" if entity_type != 'url' else "short_code": item_id,
                f"{entity_type}_url" if entity_type != 'url' else "short_url": f"{base_url}{config['url_prefix']}{item_id}",
                "title": title,
                count_field: count,
                "created_at": created_at.isoformat()
            })

        return {
            "page": page,
            "limit": limit,
            "total": total,
            config['result_key']: item_list
        }


def get_url_history(user_id, page=1, limit=20, sort_field='created_at', sort_order='desc', base_url=None):
    """Get paginated list of URLs created by a user with Redis caching.

    Args:
        user_id: The user ID to retrieve history for
        page: Page number for pagination (default: 1)
        limit: Number of items per page (default: 20)
        sort_field: Field to sort by (default: 'created_at')
        sort_order: Order to sort by ('asc' or 'desc', default: 'desc')
        base_url: Base URL for constructing full URLs (default: None)

    Returns:
        dict: Dictionary containing paginated URL history data

    Note:
        This is a specialized wrapper around _get_history_data for URLs.
    """
    return _get_history_data('url', user_id, page, limit, sort_field, sort_order, base_url)


def get_qrcode_history(user_id, page=1, limit=20, sort_field='created_at', sort_order='desc', base_url=None):
    """Get paginated list of QR codes created by a user with Redis caching.

    Args:
        user_id: The user ID to retrieve history for
        page: Page number for pagination (default: 1)
        limit: Number of items per page (default: 20)
        sort_field: Field to sort by (default: 'created_at')
        sort_order: Order to sort by ('asc' or 'desc', default: 'desc')
        base_url: Base URL for constructing full URLs (default: None)

    Returns:
        dict: Dictionary containing paginated QR code history data

    Note:
        This is a specialized wrapper around _get_history_data for QR codes.
    """
    return _get_history_data('qrcode', user_id, page, limit, sort_field, sort_order, base_url)


def get_barcode_history(user_id, page=1, limit=20, sort_field='created_at', sort_order='desc', base_url=None):
    """Get paginated list of barcodes created by a user with Redis caching.

    Args:
        user_id: The user ID to retrieve history for
        page: Page number for pagination (default: 1)
        limit: Number of items per page (default: 20)
        sort_field: Field to sort by (default: 'created_at')
        sort_order: Order to sort by ('asc' or 'desc', default: 'desc')
        base_url: Base URL for constructing full URLs (default: None)

    Returns:
        dict: Dictionary containing paginated barcode history data

    Note:
        This is a specialized wrapper around _get_history_data for barcodes.
    """
    return _get_history_data('barcode', user_id, page, limit, sort_field, sort_order, base_url)


def invalidate_user_history_cache(user_id):
    """Invalidate all history cache entries for a user when their data changes.

    Cleans up all cached history data for a specific user to ensure
    fresh data will be retrieved on the next request.

    Args:
        user_id: The user ID whose cache entries should be invalidated

    Returns:
        int: The number of cache entries that were invalidated

    Note:
        This should be called whenever a user's URL, QR code, or barcode data changes,
        such as when creating new items or deleting existing ones.
    """
    try:
        # Use pattern matching to find and delete all history keys for this user
        patterns = [
            f"history:url:{user_id}:*",
            f"history:qrcode:{user_id}:*",
            f"history:barcode:{user_id}:*"
        ]

        total_deleted = 0
        for pattern in patterns:
            cursor = "0"
            while True:
                cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    result = redis_client.delete(*keys)
                    total_deleted += result or 0

                # Exit loop when scan is complete
                if cursor == "0":
                    break

        logger.info(f"Invalidated {total_deleted} history cache entries for user {user_id}")
        return total_deleted
    except Exception as e:
        logger.error(f"Error invalidating user history cache: {e}")
        return 0