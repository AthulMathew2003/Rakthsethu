import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.exceptions import ValidationException

logger = logging.getLogger(__name__)

# Standard 14 districts of Kerala in alphabetical order
KERALA_DISTRICTS: List[str] = [
    "Alappuzha",
    "Ernakulam",
    "Idukki",
    "Kannur",
    "Kasaragod",
    "Kollam",
    "Kottayam",
    "Kozhikode",
    "Malappuram",
    "Palakkad",
    "Pathanamthitta",
    "Thiruvananthapuram",
    "Thrissur",
    "Wayanad",
]

# District canonical normalization map (case-insensitive)
DISTRICT_LOOKUP: Dict[str, str] = {d.lower(): d for d in KERALA_DISTRICTS}

# Common alternative spellings and locality aliases mapped to canonical local body & district
ALIASES: Dict[str, Dict[str, str]] = {
    "Kottayam": {
        "pala": "Pala",
        "palai": "Pala",
        "gandhinagar": "Gandhinagar",
        "kottayam east": "Kottayam",
        "medical college": "Arpookkara",
    },
    "Ernakulam": {
        "kochi corporation": "Kochi",
        "cochin": "Kochi",
        "kakkanad": "Thrikkakara",
        "tripunithura": "Tripunithura",
        "thrippunithura": "Tripunithura",
    },
    "Kozhikode": {
        "kozhikode corporation": "Kozhikode",
        "calicut": "Kozhikode",
        "feroke": "Feroke",
        "faroke": "Feroke",
        "koyilandy": "Koyilandy",
        "koilandy": "Koyilandy",
    },
    "Thrissur": {
        "thrissur corporation": "Thrissur",
        "trichur": "Thrissur",
        "guruvayur": "Guruvayur",
        "guruvayoor": "Guruvayur",
    },
    "Palakkad": {
        "palakkad municipality": "Palakkad",
        "palghat": "Palakkad",
        "ottapalam": "Ottappalam",
        "ottappalam": "Ottappalam",
    },
    "Thiruvananthapuram": {
        "thiruvananthapuram corporation": "Thiruvananthapuram",
        "trivandrum": "Thiruvananthapuram",
        "secretariat": "Thiruvananthapuram",
        "medical college": "Thiruvananthapuram",
        "kazhakkoottam": "Thiruvananthapuram",
        "kazhakoottam": "Thiruvananthapuram",
    },
    "Alappuzha": {
        "alappuzha municipality": "Alappuzha",
        "alleppey": "Alappuzha",
    },
    "Kollam": {
        "kollam corporation": "Kollam",
        "quilon": "Kollam",
    },
    "Wayanad": {
        "mananthavady": "Mananthavady",
        "mananthavadi": "Mananthavady",
        "mananthavady municipality": "Mananthavady",
    },
}

_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "kerala_locations.json")

_CACHED_LOCAL_BODIES: Optional[Dict[str, List[Dict[str, str]]]] = None


def _load_locations_data() -> Dict[str, List[Dict[str, str]]]:
    global _CACHED_LOCAL_BODIES
    if _CACHED_LOCAL_BODIES is not None:
        return _CACHED_LOCAL_BODIES

    if not os.path.exists(_DATA_PATH):
        logger.warning("Kerala locations data file not found at %s", _DATA_PATH)
        return {d: [] for d in KERALA_DISTRICTS}

    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        raw: Dict[str, List[Dict[str, str]]] = json.load(f)

    # Normalize district keys and augment with common names if needed
    normalized: Dict[str, List[Dict[str, str]]] = {}
    for dist in KERALA_DISTRICTS:
        lbs = list(raw.get(dist, []))
        # Ensure common standard names are included in list
        existing_names = {lb["name"].lower() for lb in lbs}
        if dist == "Kottayam":
            if "pala" not in existing_names:
                lbs.append({"code": "M05019", "name": "Pala", "type": "Municipality"})
            if "gandhinagar" not in existing_names:
                lbs.append({"code": "L05001", "name": "Gandhinagar", "type": "Locality"})
        elif dist == "Ernakulam":
            if "tripunithura" not in existing_names:
                lbs.append({"code": "M07021", "name": "Tripunithura", "type": "Municipality"})
            if "kakkanad" not in existing_names:
                lbs.append({"code": "L07001", "name": "Kakkanad", "type": "Locality"})
        elif dist == "Kozhikode":
            if "feroke" not in existing_names:
                lbs.append({"code": "M11080", "name": "Feroke", "type": "Municipality"})
            if "koyilandy" not in existing_names:
                lbs.append({"code": "M11049", "name": "Koyilandy", "type": "Municipality"})
        elif dist == "Thrissur":
            if "guruvayur" not in existing_names:
                lbs.append({"code": "M08036", "name": "Guruvayur", "type": "Municipality"})
        elif dist == "Palakkad":
            if "ottapalam" not in existing_names:
                lbs.append({"code": "M09039", "name": "Ottapalam", "type": "Municipality"})
        elif dist == "Wayanad":
            if "mananthavady" not in existing_names:
                lbs.append({"code": "M12081", "name": "Mananthavady", "type": "Municipality"})

        # Sort alphabetically
        lbs.sort(key=lambda x: x["name"])
        normalized[dist] = lbs

    _CACHED_LOCAL_BODIES = normalized
    return _CACHED_LOCAL_BODIES


def get_districts() -> List[str]:
    """Returns the sorted list of all 14 official districts of Kerala."""
    return list(KERALA_DISTRICTS)


def get_local_bodies(district: str, search: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Returns the local bodies (Grama Panchayats, Municipalities, Corporations)
    for the specified Kerala district.
    """
    canonical_dist = DISTRICT_LOOKUP.get(district.strip().lower())
    if not canonical_dist:
        raise ValidationException(
            f"'{district}' is not a valid Kerala district. Must be one of: {', '.join(KERALA_DISTRICTS)}"
        )

    data = _load_locations_data()
    lbs = data.get(canonical_dist, [])

    if search and search.strip():
        term = search.strip().lower()
        return [lb for lb in lbs if term in lb["name"].lower() or term in lb.get("code", "").lower()]

    return lbs


def validate_district_and_panchayat(
    district: str,
    panchayat: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Validates that:
    1. The district is one of Kerala's 14 districts.
    2. If panchayat/local-body is provided, it belongs to the selected district.

    Returns:
        (canonical_district, canonical_panchayat)
    Raises:
        ValidationException if district or local-body combination is invalid.
    """
    if not district or not str(district).strip():
        raise ValidationException("District is required.")

    canonical_dist = DISTRICT_LOOKUP.get(str(district).strip().lower())
    if not canonical_dist:
        raise ValidationException(
            f"'{district}' is not a valid Kerala district. Must be one of: {', '.join(KERALA_DISTRICTS)}"
        )

    if not panchayat or not str(panchayat).strip():
        # Backward compatibility: existing records or bulk operations without panchayat
        return canonical_dist, None

    cleaned_p = str(panchayat).strip()
    norm_p = cleaned_p.lower()

    # Check alias lookup for this district
    district_aliases = ALIASES.get(canonical_dist, {})
    if norm_p in district_aliases:
        return canonical_dist, district_aliases[norm_p]

    # Strip generic suffix like "Corporation", "Municipality", "Panchayat", "Grama Panchayat"
    suffix_clean = re.sub(
        r"\s+(corporation|municipal corporation|municipality|grama panchayat|panchayat)$",
        "",
        norm_p,
        flags=re.IGNORECASE,
    ).strip()

    if suffix_clean in district_aliases:
        return canonical_dist, district_aliases[suffix_clean]

    # Match against local bodies belonging to this district
    data = _load_locations_data()
    dist_lbs = data.get(canonical_dist, [])

    for lb in dist_lbs:
        lb_name = lb["name"]
        lb_norm = lb_name.lower()
        lb_suffix_clean = re.sub(
            r"\s+(corporation|municipal corporation|municipality|grama panchayat|panchayat)$",
            "",
            lb_norm,
            flags=re.IGNORECASE,
        ).strip()

        if norm_p == lb_norm or suffix_clean == lb_suffix_clean or norm_p == lb_suffix_clean:
            return canonical_dist, lb_name

    # If not found in this district, check if it belongs to a different district to provide a helpful error
    other_dist = None
    for other, other_lbs in data.items():
        if other == canonical_dist:
            continue
        for lb in other_lbs:
            if norm_p == lb["name"].lower() or suffix_clean == lb["name"].lower():
                other_dist = other
                break
        if other_dist:
            break

    if other_dist:
        raise ValidationException(
            f"'{cleaned_p}' belongs to district '{other_dist}', not '{canonical_dist}'."
        )

    raise ValidationException(
        f"'{cleaned_p}' is not a recognized local body in district '{canonical_dist}'."
    )
