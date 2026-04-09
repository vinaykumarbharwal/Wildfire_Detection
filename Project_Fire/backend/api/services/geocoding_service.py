import aiohttp
import math
import json
import logging
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from api.services.redis_service import cache

load_dotenv()

logger = logging.getLogger(__name__)
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# Cache constants
CACHE_EXPIRY_SECONDS = 60 * 60 * 24 * 7 # 7 Days (geocoding doesn't change often)

async def get_location_details(lat: float, lon: float) -> Dict:
    """Get address details from coordinates using Google Geocoding API with caching."""
    # Round to 4 decimals for cache key (~11m precision - good for hits)
    lat_key, lon_key = round(lat, 4), round(lon, 4)
    cache_key = f"geocode:{lat_key}:{lon_key}"
    
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        if not GOOGLE_MAPS_API_KEY:
            return {'address': f"{lat}, {lon}"}
        
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f"{lat},{lon}",
            'key': GOOGLE_MAPS_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                
                if data['status'] == 'OK' and data['results']:
                    result = data['results'][0]
                    address_components = result['address_components']
                    
                    location = {
                        'address': result['formatted_address'],
                        'city': '',
                        'state': '',
                        'country': '',
                        'postal_code': ''
                    }
                    
                    for component in address_components:
                        types = component['types']
                        if 'locality' in types:
                            location['city'] = component['long_name']
                        elif 'administrative_area_level_1' in types:
                            location['state'] = component['long_name']
                        elif 'country' in types:
                            location['country'] = component['long_name']
                        elif 'postal_code' in types:
                            location['postal_code'] = component['long_name']
                    
                    cache.set(cache_key, location, CACHE_EXPIRY_SECONDS)
                    return location
                    
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
    
    return {'address': f"{lat}, {lon}"}

async def find_nearby_stations(lat: float, lon: float, radius: int = 50000) -> List[Dict]:
    """Find nearby fire stations using Google Places API with caching."""
    lat_key, lon_key = round(lat, 3), round(lon, 3) # Slightly less precision for stations is fine
    cache_key = f"stations:{lat_key}:{lon_key}:{radius}"
    
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        if not GOOGLE_MAPS_API_KEY:
            return []
        
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': f"{lat},{lon}",
            'radius': radius,
            'keyword': 'fire station',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                
                stations = []
                for place in data.get('results', [])[:10]:
                    station = {
                        'name': place.get('name'),
                        'address': place.get('vicinity'),
                        'latitude': place['geometry']['location']['lat'],
                        'longitude': place['geometry']['location']['lng'],
                        'distance': calculate_distance(
                            lat, lon,
                            place['geometry']['location']['lat'],
                            place['geometry']['location']['lng']
                        ),
                        'place_id': place.get('place_id')
                    }
                    
                    # Try to get additional details
                    if place.get('place_id'):
                        station.update(
                            await get_place_details(place['place_id'])
                        )
                    
                    stations.append(station)
                
                # Sort by distance
                stations.sort(key=lambda x: x['distance'])
                cache.set(cache_key, stations, CACHE_EXPIRY_SECONDS)
                return stations
                    
    except Exception as e:
        logger.error(f"Places API error: {e}")
        return []

async def get_place_details(place_id: str) -> Dict:
    """Get detailed information about a place with caching."""
    cache_key = f"place_detail:{place_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'place_id': place_id,
            'fields': 'formatted_phone_number,international_phone_number,website,opening_hours',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                
                if data['status'] == 'OK':
                    result = data['result']
                    details = {
                        'phone': result.get('formatted_phone_number') or result.get('international_phone_number'),
                        'website': result.get('website'),
                        'hours': result.get('opening_hours', {}).get('weekday_text')
                    }
                    cache.set(cache_key, details, CACHE_EXPIRY_SECONDS)
                    return details
                    
    except Exception as e:
        logger.error(f"Place details error: {e}")
    
    return {}

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return round(R * c, 2)  # Distance in kilometers