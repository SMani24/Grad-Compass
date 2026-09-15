import json
import urllib.request
import urllib.parse
from pathlib import Path
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="grad_compass_desktop")
CACHE_DIR = Path(__file__).resolve().parent.parent / "ui" / "cache" / "images"

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

def fetch_and_cache_university_photo(uni_id: int, name: str) -> str:
    """
    Queries Wikipedia API for a campus image, downloads it to ui/cache/images/{uni_id}.jpg,
    and returns the local relative web path ('cache/images/{uni_id}.jpg').
    """
    if not name:
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target_file = CACHE_DIR / f"{uni_id}.jpg"

    # Return immediately if already cached on disk
    if target_file.exists() and target_file.stat().st_size > 0:
        return f"cache/images/{uni_id}.jpg"

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
                img_url = None
                if "thumbnail" in data and "source" in data["thumbnail"]:
                    img_url = data["thumbnail"]["source"]
                elif "originalimage" in data and "source" in data["originalimage"]:
                    img_url = data["originalimage"]["source"]

                if img_url:
                    img_req = urllib.request.Request(img_url, headers=headers)
                    with urllib.request.urlopen(img_req, timeout=8) as img_resp:
                        with open(target_file, "wb") as f:
                            f.write(img_resp.read())
                    return f"cache/images/{uni_id}.jpg"
    except Exception as e:
        print(f"[Photo Cache] Could not fetch/cache photo for '{clean_name}': {e}")

    return None