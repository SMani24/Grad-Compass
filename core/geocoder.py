import json
import urllib.request
import urllib.parse
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

def fetch_university_photo(name: str) -> str:
    """
    Fetches a high-quality university image from Wikipedia REST API without API keys.
    Returns the image URL, or None if not found.
    """
    if not name:
        return None

    # Clean query: strip degrees or parenthetical additions (e.g., 'EPFL - Computer Science' -> 'EPFL')
    clean_name = name.split(" - ")[0].split("(")[0].strip()
    encoded_title = urllib.parse.quote(clean_name.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

    headers = {
        "User-Agent": "GradCompass/1.0 (academic university tracker; contact@gradcompass.app)"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                
                # Check thumbnail or original image
                if "thumbnail" in data and "source" in data["thumbnail"]:
                    return data["thumbnail"]["source"]
                if "originalimage" in data and "source" in data["originalimage"]:
                    return data["originalimage"]["source"]
    except Exception as e:
        print(f"[Wikipedia Photo] Could not fetch photo for '{clean_name}': {e}")

    return None