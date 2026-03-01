# RentShield
**AI Rental Scam Risk Detector — Chrome Extension**
Product Requirements Document | Hackathon Build | 24-Hour Scope

---

## 1. Objective

RentShield is a Chrome extension that analyzes rental listings inside Facebook groups and returns a composite Scam Risk Score. It automates the grunt work of cross-referencing listing data against real-time external sources, surfacing specific red flags so renters can make informed decisions before sending a deposit.

The tool is advisory, not definitive. It flags potential issues and explains why — empowering users rather than replacing their judgment.

---

## 2. Problem Statement

Rental scams are widespread in Facebook housing groups. Common tactics include:

- Copying legitimate Zillow listings and re-posting at below-market prices
- Posing as landlords or agents for properties they don't own
- Pressuring renters to wire deposits before any in-person viewing
- Using stolen photos from real listings to appear legitimate

There is currently no automated tool inside Facebook that helps renters assess listing legitimacy in real time. RentShield fills that gap.

---

## 3. Target Users

- College students searching for off-campus housing
- First-time renters unfamiliar with market norms
- Relocating professionals scouting remotely
- International renters unfamiliar with U.S. rental market conventions

---

## 4. Demo Flow

| Step | Action |
|------|--------|
| 1 | User opens a rental post in a Facebook Group |
| 2 | Clicks the "Analyze Listing" button injected by the extension |
| 3 | Content script extracts post text and image URLs from the rendered DOM |
| 4 | Data is sent to the FastAPI backend |
| 5 | Backend runs four scoring modules in parallel |
| 6 | Composite risk score and flag breakdown returned as JSON |
| 7 | Extension popup renders the score, flags, and supporting evidence |

---

## 5. Scam Detection Features

RentShield uses five independent signals. Four contribute positive risk points; one (video presence) is a legitimacy bonus that reduces the score.

### 5.1 Address Lookup & Listing Verification

If an address is present in the post text, the backend queries a real-time Zillow API wrapper (via RapidAPI) to check for a live listing at that address.

Key logic:
- **Listing found on Zillow + posted rent significantly lower than Zillow price → HIGH RISK.** This is the signature scam pattern: copying a real listing and undercutting the price.
- **Listing found on Zillow as For Sale only, not For Rent → MODERATE RISK.**
- **No listing found for a claimed specific address → MODERATE RISK.**
- Attempt to cross-reference the Facebook poster name / contact info with the agent or owner listed on the Zillow record. A mismatch is flagged; a match reduces risk score slightly.

Note: Most posts will not include a full address. This module fires only when an address is detected and gracefully skips otherwise.

### 5.2 Price Anomaly Detection

Even without a full address, a zip code or neighborhood name is usually present. The backend extracts this via Gemini NLP, then queries a real-time rent data API (Rentcast or RapidAPI Zillow) for active listings and median rent in that zip code.

Scoring thresholds:
- Rent < 65% of zip median → HIGH RISK (+30 points)
- Rent < 80% of zip median → MODERATE RISK (+15 points)
- Rent within normal range → No penalty

Evidence shown to user: *"Area median for 92612: $2,100/mo. Listed price: $1,100/mo. 48% below median."*

### 5.3 NLP Analysis of Listing Description

The full post text is sent to Gemini with a structured extraction prompt. Gemini returns a JSON object containing:

- Extracted monthly rent
- Extracted zip code or neighborhood
- Extracted contact info (phone, email, Venmo/Zelle/CashApp mentions)
- Suspicious phrases detected
- Missing legitimacy signals (no address, no photos mentioned, no lease terms)

Suspicious phrase categories flagged:
- **Urgency language:** "must move fast", "only one unit left", "responding to first applicant"
- **Deposit-first pressure:** "send deposit to hold", "wire transfer", "Zelle only"
- **Avoidance language:** "out of town", "no showings", "contact by email only"
- **Vagueness:** no price stated, no address, no lease length

Each suspicious phrase category adds points to the risk score. Contact info found outside the Facebook platform (raw phone/email/payment app in post body) adds additional points.

### 5.4 Image Analysis via Gemini Vision

Image URLs extracted from the post are sent to Gemini Vision for qualitative analysis. The prompt asks Gemini to evaluate:

- Do the photos look like authentic landlord photos or suspiciously professional/stock-like?
- Is the number of images abnormally low (e.g., only 1–2 photos for a full apartment)?
- Does the visible neighborhood, architecture, or environment seem consistent with the claimed location?
- Are there any visible watermarks, logos, or visual artifacts suggesting images were pulled from another site?

Gemini returns a structured confidence score and a brief explanation surfaced directly to the user as evidence.

### 5.5 Video Presence Detection (Legitimacy Bonus)

The content script checks the rendered Facebook post DOM for the presence of a video element — a walkthrough, tour, or any video attached to the listing. No video analysis is performed; presence alone is the signal.

Why this matters: a scammer copying a Zillow listing will have stolen photos but almost never a genuine walkthrough video. Video production requires physical access to the property, making it one of the strongest low-effort legitimacy signals available without any backend analysis.

Scoring effect:
- **Video detected → −15 point reduction** to the composite score (legitimacy bonus)
- No video detected → no penalty, no bonus

UI display: shown as a green checkmark — *"✅ Video walkthrough present — significantly reduces fraud likelihood"* — so the tool feels balanced rather than purely a red-flag machine.

---

## 6. Composite Risk Scoring

| Module | Max Points | Key Signals |
|--------|-----------|-------------|
| Address Lookup & Verification | +25 | Price lower than Zillow, For Sale only, poster mismatch |
| Price Anomaly Detection | +30 | Rent vs. zip median deviation |
| NLP Description Analysis | +25 | Suspicious phrases, deposit pressure, missing info, external contact |
| Image Analysis (Gemini Vision) | +20 | Suspicious staging, location mismatch, watermarks, image count |
| Video Presence (Legitimacy Bonus) | −15 | Video walkthrough detected → score reduced |

**Final score = sum of module scores, capped at 100, minimum 0.**

Score interpretation:
- **0–30: Low Risk** — Proceed with normal caution
- **31–60: Moderate Risk** — Verify independently before any payment
- **61–100: High Risk** — Strong indicators of a scam listing

---

## 7. UI Requirements

The extension popup must display:

- A prominent Scam Risk Score with color coding (green / yellow / red)
- A flag breakdown section listing each triggered signal with a brief explanation
- An evidence section showing supporting data (e.g., area median rent, Zillow match status, Gemini image assessment)
- A disclaimer: *"RentShield is advisory. Always verify listings independently before sending any payment."*

The popup should be demo-friendly: clean layout, readable at a glance, no raw JSON visible.

---

## 8. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Chrome Extension | Manifest V3, Vanilla JS | Content script reads rendered DOM; no backend scraping of Facebook |
| Extension UI (Popup) | React + TailwindCSS | Single popup component; color-coded score display |
| Backend API | Python + FastAPI | Hosted on Railway or Render |
| NLP & Structured Extraction | Google Gemini API | Extracts rent, zip, contact info, suspicious phrases from post text |
| Image Analysis | Gemini Vision API | Evaluates listing images for authenticity and location consistency |
| Price Data | RapidAPI Zillow wrapper + Rentcast API | Real-time zip-level median rent and active listing data |
| Address Lookup | RapidAPI Zillow wrapper | Checks live listing existence; retrieves listed price and agent info |

---

## 9. Architecture Overview

```
Facebook Page (Rendered DOM)
    ↓  Content Script (reads post text + image URLs + video presence)
FastAPI Backend
    ├── Gemini NLP        →  structured JSON (rent, zip, phrases, contact)
    ├── Gemini Vision     →  image risk assessment
    ├── RapidAPI Zillow   →  address lookup + agent info
    ├── Rentcast / RapidAPI  →  zip median rent + active listings
    └── Scoring Engine   →  composite score + flag list
    ↓  JSON response
Extension Popup  →  Score + Flags + Evidence displayed to user
```

---

## 10. Out of Scope (Hackathon Build)

- Real-time ML classifier trained on scam data (rule-based scoring only)
- Agent identity verification against state licensing databases
- Craigslist, Apartments.com, or other platform support
- Community scam reporting network
- Backend scraping of Facebook (all data comes from the already-rendered DOM)

---

## 11. Success Criteria

- Risk score generated in under 5 seconds on a live or simulated Facebook listing
- At least 4 distinct risk signals surfaced in the flag breakdown
- At least 2 real-time external data sources queried (Zillow/Rentcast + Gemini)
- Live demo functions end-to-end without manual intervention
- UI is readable and color-coded at a glance for a non-technical judge

---

## 12. Future Roadmap

- Train a logistic regression or lightweight ML classifier on a labeled scam dataset
- Integrate state landlord license lookup APIs
- Add Venmo / CashApp / Zelle payment handle fraud signals
- Community-sourced scam reporting to build a known-scammer database
- Expand to Craigslist, Apartments.com, and other rental platforms

---

*RentShield helps renters avoid sending deposits to scammers.*