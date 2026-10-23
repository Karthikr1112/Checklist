import math
from decimal import Decimal
from typing import Optional, Tuple


def calculate_distance_meters(
    lat1: float | Decimal, lon1: float | Decimal,
    lat2: float | Decimal, lon2: float | Decimal
) -> float:
    """
    Calculate the great-circle distance between two points in meters using the Haversine formula.
    """
    R = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def verify_user_at_store(
    *,
    store,
    user_latitude: Optional[float | Decimal | str],
    user_longitude: Optional[float | Decimal | str],
    is_admin_bypass: bool = False,
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Check if the user is within the store's geofence radius.
    Returns: (is_valid, error_message, distance_meters)
    """
    if is_admin_bypass:
        return True, None, 0

    if not store.latitude or not store.longitude:
        # Store doesn't have coordinates configured yet
        return True, None, None

    if not user_latitude or not user_longitude:
        return (
            False,
            "Location verification is required. Please turn on device GPS/Location and allow browser permissions to verify you are at the store.",
            None,
        )

    try:
        user_lat = float(user_latitude)
        user_lon = float(user_longitude)
    except (ValueError, TypeError):
        return False, "Invalid GPS coordinates received. Please try again with GPS enabled.", None

    dist = calculate_distance_meters(user_lat, user_lon, store.latitude, store.longitude)
    dist_int = int(round(dist))
    allowed_radius = getattr(store, "geofence_radius_meters", 250) or 250

    if dist > allowed_radius:
        return (
            False,
            (
                f"Location verification failed: You are outside {store.code} · {store.name}. "
                f"Company rule: You must be physically at the store (within {allowed_radius}m) to start or edit this visit."
            ),
            dist_int,
        )

    return True, None, dist_int
