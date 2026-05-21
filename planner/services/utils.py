# planner/services/utils.py
import re

def normalize_place_name(name, destination=""):
    """Safe normalization for deduplication"""

    if not name:
        return ""

    name = name.lower().strip()

    # Keep letters, numbers, spaces ONLY (safe for places)
    name = re.sub(r'[^a-z0-9\s]', ' ', name)

    # Normalize destination separately (avoid repeated .lower())
    dest = (destination or "").lower().strip()

    remove_words = [
        'official',
        'tourism',
        'tourist',
        'best',
        'famous',
        'entry',
        'gate',
        'viewpoint',
        'view point'
    ]

    # Add destination only if meaningful
    if dest:
        remove_words.append(dest)

    # SAFE word removal (word-based, not substring-based)
    words = name.split()

    cleaned_words = [
        w for w in words
        if w not in remove_words
    ]

    return ' '.join(cleaned_words).strip()


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    import math
    
    try:
        R = 6371

        lat1 = math.radians(float(lat1))
        lon1 = math.radians(float(lon1))

        lat2 = math.radians(float(lat2))
        lon2 = math.radians(float(lon2))

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(dlon / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )

        return R * c

    except:
        return 9999