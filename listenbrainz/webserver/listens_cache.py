from typing import Optional, Any
import json

from brainzutils import cache
from flask import current_app


def _get_listens_cache_key(
    user_id: int,
    min_ts: Optional[int] = None,
    max_ts: Optional[int] = None,
    count: Optional[int] = None
) -> str:
    """Generate a cache key for the get_listens endpoint.
    
    Args:
        user_id: The ListenBrainz user ID of the user
        min_ts: Optional minimum timestamp (UNIX timestamp)
        max_ts: Optional maximum timestamp (UNIX timestamp)
        count: Optional number of items to return
        
    Returns:
        A string to be used as a cache key
    """
    key_parts = ["listens", str(user_id)]
    if min_ts is not None:
        key_parts.append(f"min_{min_ts}")
    if max_ts is not None:
        key_parts.append(f"max_{max_ts}")
    if count is not None:
        key_parts.append(f"count_{count}")
    return ":".join(key_parts)


def get_listens_from_cache(
    user_id: int,
    min_ts: Optional[float] = None,
    max_ts: Optional[float] = None,
    count: Optional[int] = None
) -> Optional[dict[str, Any]]:
    """Get listens from cache if available.
    
    Args:
        user_id: The ListenBrainz user ID of the user
        min_ts: Optional minimum timestamp (UNIX timestamp)
        max_ts: Optional maximum timestamp (UNIX timestamp)
        count: Optional number of items to return
        
    Returns:
        Cached data if found, None otherwise
    """
    cache_key = _get_listens_cache_key(user_id, min_ts, max_ts, count)
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)
    return None


def set_listens_in_cache(
    data: dict[str, Any],
    user_id: int,
    min_ts: Optional[float] = None,
    max_ts: Optional[float] = None, 
    count: Optional[int] = None,
    expire_time: int = 3600
) -> None:
    """Store listens data in cache.
    
    Args:
        user_id: The ListenBrainz user ID of the user
        data: The data to cache (should be JSON serializable)
        min_ts: Optional minimum timestamp (UNIX timestamp)
        max_ts: Optional maximum timestamp (UNIX timestamp)
        count: Optional number of items
        expire_time: Time in seconds until the cache expires.
    """
    cache_key = _get_listens_cache_key(user_id, min_ts, max_ts, count)
    cache.sadd(f"user_listens_cache:{user_id}", cache_key, expire_time * 2)
    cache.set(cache_key, json.dumps(data), expire_time)

def invalidate_user_listen_caches(user_id: int) -> None:
    """Invalidate all cached listens for a user.
    
    This should be called whenever new listens are inserted or deleted for a user.
    
    Args:
        user_id: The ListenBrainz user ID of the user
    """
    user_cache_set = f"user_listens_cache:{user_id}"
    cache_keys = cache.smembers(user_cache_set)
    current_app.logger.error("smembers: %s", cache_keys)
    if cache_keys:
        cache.delete_many(cache_keys)
        cache.delete(user_cache_set)
