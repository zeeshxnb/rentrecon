VISION_ANALYSIS_PROMPT = """You are analyzing images from a Facebook rental listing to detect potential scam indicators.

For EACH image, evaluate these factors:

1. AUTHENTICITY: Does this look like a genuine photo taken by a landlord/tenant with a phone, or does it look like:
   - A stock photo from a website
   - A professionally staged real estate photo (very high quality, perfect lighting, no personal items)
   - An image clearly grabbed from another listing site

2. WATERMARKS: Are there any visible:
   - Watermarks or logos (Zillow, Realtor.com, Shutterstock, Getty, etc.)
   - Text overlays from other listing sites
   - "Virtual staging" labels

3. IMAGE QUALITY: Is the quality inconsistent with a regular landlord photo?
   - Extremely high quality + perfect lighting = possibly stolen from professional listing
   - Very low quality or blurry = possibly hiding details

4. LOCATION CONSISTENCY: If multiple images are provided:
   - Do they appear to be from the same property?
   - Does the architecture/neighborhood style seem consistent?

For each image, rate authenticity as: "authentic", "suspicious", or "stock_photo"
Provide a confidence score from 0.0 to 1.0.

Then provide a SHORT overall summary (one sentence max, under 80 characters). Keep each image explanation to one short sentence as well.

Respond with a valid JSON object:
{{
    "assessments": [
        {{
            "image_index": number,
            "authenticity": "authentic" | "suspicious" | "stock_photo",
            "confidence": number,
            "watermark_detected": boolean,
            "professional_staging": boolean,
            "location_consistent": boolean | null,
            "explanation": string
        }}
    ],
    "overall_risk_score": number (0-20),
    "summary": string
}}"""
