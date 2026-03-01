import re


def normalize_address(address: str) -> str:
    """Normalize an address string for consistent matching and cache keys."""
    if not address:
        return ""
    addr = address.strip().lower()
    # Remove apartment/unit/suite suffixes
    addr = re.sub(r'\b(apt|unit|suite|ste|#)\s*\S+', '', addr, flags=re.IGNORECASE)
    # Standardize abbreviations
    replacements = {
        r'\bstreet\b': 'st',
        r'\bavenue\b': 'ave',
        r'\bboulevard\b': 'blvd',
        r'\bdrive\b': 'dr',
        r'\blane\b': 'ln',
        r'\broad\b': 'rd',
        r'\bcourt\b': 'ct',
        r'\bplace\b': 'pl',
        r'\bcircle\b': 'cir',
        r'\bnorth\b': 'n',
        r'\bsouth\b': 's',
        r'\beast\b': 'e',
        r'\bwest\b': 'w',
    }
    for pattern, replacement in replacements.items():
        addr = re.sub(pattern, replacement, addr)
    # Collapse whitespace
    addr = re.sub(r'\s+', ' ', addr).strip()
    return addr


def normalize_price(price_str: str | float | int | None) -> float | None:
    """Extract a numeric price from various formats."""
    if price_str is None:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    cleaned = re.sub(r'[^\d.]', '', str(price_str))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_zip(zip_code: str | None) -> str | None:
    """Extract a 5-digit US zip code."""
    if not zip_code:
        return None
    match = re.search(r'\b(\d{5})\b', str(zip_code))
    return match.group(1) if match else None


def name_match(name1: str | None, name2: str | None) -> bool:
    """Check if two names are likely the same person (case-insensitive, fuzzy)."""
    if not name1 or not name2:
        return False
    n1 = name1.strip().lower()
    n2 = name2.strip().lower()
    if n1 == n2:
        return True
    # Check if one name contains the other (handles "John" vs "John Smith")
    if n1 in n2 or n2 in n1:
        return True
    # Check last name match
    parts1 = n1.split()
    parts2 = n2.split()
    if len(parts1) > 1 and len(parts2) > 1 and parts1[-1] == parts2[-1]:
        return True
    return False
