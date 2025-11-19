
"""Utility functions for the travel activity system"""

import time
import logging
from functools import wraps
from typing import Callable, Any
from math import radians, cos, sin, asin, sqrt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def rate_limit(calls_per_second: int = 10):
    """
    Rate-limiting decorator.

    Ensures that a function is not called faster than the specified frequency.

    Args:
        calls_per_second: Maximum allowed calls per second.

    Returns:
        A wrapped function that respects the rate limit.
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]  # use list to allow mutation inside closure
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            elapsed = time.time() - last_called[0]
            wait_time = min_interval - elapsed
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
                time.sleep(wait_time)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Retry-on-failure decorator.

    Automatically retries executing a function if an exception occurs.

    Args:
        max_retries: Maximum number of retries before failing.
        delay: Initial retry delay (seconds). Delay increases linearly.

    Returns:
        A wrapped function that retries on failure.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying..."
                    )
                    time.sleep(delay * (attempt + 1))  # Exponential-ish backoff
        return wrapper
    return decorator


def calculate_haversine_distance(loc1: dict, loc2: dict) -> float:
    """
    Calculate the great-circle distance between two points using the Haversine formula.

    Args:
        loc1: {"lat": float, "lng": float}
        loc2: {"lat": float, "lng": float}

    Returns:
        Distance in meters.
    """
    lat1, lon1 = radians(loc1['lat']), radians(loc1['lng'])
    lat2, lon2 = radians(loc2['lat']), radians(loc2['lng'])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    return 6371000 * c  # Earth radius in meters


def format_distance(distance_meters: float) -> str:
    """
    Format a distance value into a readable string.

    Args:
        distance_meters: Distance in meters.

    Returns:
        A formatted string such as "850m" or "4.21km".
    """
    if distance_meters < 1000:
        return f"{distance_meters:.0f}m"
    else:
        return f"{distance_meters / 1000:.2f}km"


def validate_location(location: dict) -> bool:
    """
    Validate a location dictionary.

    Ensures the dictionary contains valid latitude and longitude values.

    Args:
        location: {"lat": ..., "lng": ...}

    Returns:
        True if valid, False otherwise.
    """
    if not isinstance(location, dict):
        return False
    
    if 'lat' not in location or 'lng' not in location:
        return False
    
    try:
        lat = float(location['lat'])
        lng = float(location['lng'])
        
        # Latitude range: -90 to 90
        if not (-90 <= lat <= 90):
            return False
        
        # Longitude range: -180 to 180
        if not (-180 <= lng <= 180):
            return False
        
        return True

    except (ValueError, TypeError):
        return False
