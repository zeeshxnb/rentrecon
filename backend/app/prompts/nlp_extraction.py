NLP_EXTRACTION_PROMPT = """You are analyzing a Facebook rental listing post for potential scam indicators.
Extract the following information from the post text. If a field is not present, return null.

REQUIRED EXTRACTIONS:
1. rent_amount: Monthly rent as a number (no dollar sign). Return null if not stated.
2. zip_code: 5-digit US zip code. Return null if not present.
3. full_address: Complete street address if present. Return null if not found.
4. neighborhood: Neighborhood or area name if mentioned. Return null if not found.
5. bedrooms: Number of bedrooms as integer. Return null if not stated.
6. bathrooms: Number of bathrooms as float. Return null if not stated.
7. contact_phone: Array of phone numbers found in the post text.
8. contact_email: Array of email addresses found in the post text.
9. payment_apps: Array of payment app mentions (look for: Venmo, Zelle, CashApp, PayPal, wire transfer, Western Union, Money Order, Bitcoin, Crypto).

SUSPICIOUS PHRASE DETECTION:
Identify phrases matching these categories. For each, provide the exact phrase, category, and severity.

Categories:
- "urgency": "must move fast", "only one unit left", "first come first served", "won't last", "act now", "responding to first applicant", "available immediately must commit"
- "deposit_pressure": "send deposit to hold", "wire transfer required", "Zelle only", "pay before viewing", "deposit required before showing", "non-refundable deposit", "secure it now with payment"
- "avoidance": "out of town", "no showings", "contact by email only", "cannot meet in person", "overseas", "military deployment", "traveling abroad"
- "vagueness": no price stated, no address provided, "DM for details", "message for price", "DM for info", no lease length mentioned

Severity: "high" if the phrase is a strong scam indicator, "moderate" if somewhat suspicious, "low" if mildly notable.

MISSING LEGITIMACY SIGNALS:
Check if these are ABSENT from the post and list any that are missing:
- "no_address": No street address or specific location
- "no_price": No monthly rent price stated
- "no_photos_mentioned": No reference to photos or images
- "no_lease_terms": No mention of lease length, move-in date, or rental terms
- "no_landlord_name": No property management company or landlord name

SCORING (0-10 scale):
- urgency_score: How much urgency pressure is in the text (0=none, 10=extreme)
- deposit_pressure_score: How much payment pressure is present (0=none, 10=extreme)
- avoidance_score: How much avoidance of verification is present (0=none, 10=extreme)
- vagueness_score: How vague/incomplete the listing is (0=complete, 10=extremely vague)

POST TEXT TO ANALYZE:
{post_text}

Respond with a valid JSON object matching this exact schema:
{{
    "rent_amount": number | null,
    "zip_code": string | null,
    "full_address": string | null,
    "neighborhood": string | null,
    "bedrooms": number | null,
    "bathrooms": number | null,
    "contact_phone": [string],
    "contact_email": [string],
    "payment_apps": [string],
    "suspicious_phrases": [
        {{"phrase": string, "category": string, "severity": string}}
    ],
    "missing_signals": [string],
    "urgency_score": number,
    "deposit_pressure_score": number,
    "avoidance_score": number,
    "vagueness_score": number
}}"""
