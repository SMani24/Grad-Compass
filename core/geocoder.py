from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="grad_compass_desktop")

def geocode_institution(name: str, country: str, city: str = None):
    """Returns (lat, lng) tuple or (None, None) if unresolved."""
    queries = []
    if city:
        queries.append(f"{name}, {city}, {country}")
    queries.append(f"{name}, {country}")
    queries.append(name)

    for q in queries:
        try:
            location = geolocator.geocode(q, timeout=6)
            if location:
                return round(location.latitude, 6), round(location.longitude, 6)
        except Exception as e:
            print(f"[Geocoder warning] Query '{q}' failed: {e}")
            continue

    return None, None