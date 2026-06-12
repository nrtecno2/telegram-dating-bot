import math
import logging
from database import get_db

logger = logging.getLogger(__name__)
db = get_db()


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula
    Returns distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return round(distance, 2)


def get_nearby_profiles(latitude, longitude, query_filter=None, max_distance_km=50):
    """
    Get profiles near a given location
    Returns cursor of profiles within max_distance_km
    """
    profiles_col = db.get_collection("profiles")
    
    if query_filter is None:
        query_filter = {}
    
    # Add condition for profiles that have location
    query_filter["latitude"] = {"$exists": True, "$ne": None}
    query_filter["longitude"] = {"$exists": True, "$ne": None}
    
    # Get all profiles with location
    profiles = list(profiles_col.find(query_filter))
    
    # Calculate distance for each profile and filter
    nearby_profiles = []
    
    for profile in profiles:
        if profile.get('latitude') and profile.get('longitude'):
            distance = calculate_distance(
                latitude, longitude,
                profile['latitude'], profile['longitude']
            )
            
            if distance <= max_distance_km:
                profile['distance'] = distance
                nearby_profiles.append(profile)
    
    # Sort by distance
    nearby_profiles.sort(key=lambda x: x.get('distance', float('inf')))
    
    return nearby_profiles


def get_location_based_matches(user_id, max_distance_km=50):
    """
    Get potential matches based on user's location
    Returns list of profiles sorted by distance
    """
    user_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    
    if not user_profile or not user_profile.get('latitude'):
        return []
    
    # Get user preference
    user = db.get_collection("users").find_one({"user_id": user_id})
    preference = user.get('preference', 'both') if user else 'both'
    
    # Build query filter
    query_filter = {
        "user_id": {"$ne": user_id},
        "is_active": True
    }
    
    if preference == 'male':
        query_filter["gender"] = "male"
    elif preference == 'female':
        query_filter["gender"] = "female"
    
    # Get already liked users
    liked_users = db.get_collection("likes").distinct("to_user", {"from_user": user_id})
    query_filter["user_id"] = {"$nin": liked_users}
    
    return get_nearby_profiles(
        user_profile['latitude'],
        user_profile['longitude'],
        query_filter,
        max_distance_km
    )


def format_distance(distance_km):
    """Format distance for display"""
    if distance_km < 1:
        distance_m = int(distance_km * 1000)
        return f"{distance_m}m"
    elif distance_km < 10:
        return f"{distance_km:.1f}km"
    else:
        return f"{int(distance_km)}km"


def is_within_radius(lat1, lon1, lat2, lon2, radius_km):
    """Check if second point is within radius of first point"""
    distance = calculate_distance(lat1, lon1, lat2, lon2)
    return distance <= radius_km
