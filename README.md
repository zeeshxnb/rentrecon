# Rent Recon

IrvineHacks 2026 Project by Zeeshan, Andrew, Jason

## Overview

Rent Recon is an algorithm-based Chrome extension tool that assists in rental property search on Facebook Marketplace by identifying signs of fraudulence. It scrapes the listing content (address, description, images, etc) and cross-references multiple real estate databases to suggest a fraud risk score from 0 to 100, with concrete reasoning attached.

## Algorithm

The algorithm determines the suggested fraud risk score based on 5 features:

| Feature | Max Penalty | Details |
|---|---|---|
| **Address Lookup** | −25 | Cross-references poster name against listing agents on record; flags missing addresses, removed/inactive listings, and properties listed for sale instead of rent |
| **Price Anomaly** | −30 | Compares posted rent against area median and MLS listed rent; escalating penalties for deeper discounts |
| **NLP Analysis** | −25 | Detects missing legitimacy signals (no address, no lease terms), urgency/avoidance language, payment app mentions, and deposit pressure |
| **Image Analysis** | −20 | Flags stock photos, staged images, suspiciously few photos, and missing images entirely |
| **Video Presence** | +15 bonus | Video walkthrough detected, significantly reduces fraud likelihood |

## Architecture

```
┌──────────────────────┐       POST /api/v1/analyze       ┌──────────────────────────┐
│   Chrome Extension   │ ──────────────────────────────▶  │      FastAPI Backend      │
│                      │                                   │                           │
│  Content Script      │                                   │  ┌─────────────────────┐  │
│  ├─ extractor.js     │                                   │  │   Scoring Engine    │  │
│  ├─ injector.js      │                                   │  └──┬──┬──┬──┬──┬─────┘  │
│  └─ content.js       │                                   │     │  │  │  │  │        │
│                      │       analysis results            │     ▼  ▼  ▼  ▼  ▼        │
│  Background Worker   │ ◀──────────────────────────────── │  NLP │Price│Addr│Img│Vid │
│  └─ service-worker   │                                   │     │  │  │  │  │        │
│                      │                                   │     ▼  ▼  ▼  ▼  ▼        │
│  Popup UI (React)    │                                   │  Gemini  Rentcast  Zillow │
│  └─ Score + Flags    │                                   │  API     API       API    │
└──────────────────────┘                                   └──────────────────────────┘
```

## Tech Stack

**Extension** — React 18, TypeScript, Tailwind CSS, Vite, CRXJS (Manifest V3)

**Backend** — Python 3.12, FastAPI, Pydantic, httpx, Google Gemini (NLP + Vision), Rentcast API, Zillow API (RapidAPI), cachetools, SlowAPI

## Getting Started

### Prerequisites

- [Conda](https://docs.conda.io/en/latest/)
- [Node.js](https://nodejs.org/)
- API keys for: Google Gemini, Rentcast, RapidAPI (Zillow)

### Backend

```bash
# Create and activate the conda environment
conda env create -f environment.yml
conda activate rentrecon

# Configure environment variables
cp backend/.env.example backend/.env   # then fill in your API keys

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Health check: `GET /api/v1/health`.

### Extension

```bash
cd extension

# Install dependencies
npm install

# Build the extension
npm run build
```

Then load the built extension in Chrome:
1. Navigate to `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** and select the `extension/dist` directory

### Usage

1. Open [Facebook Marketplace](https://www.facebook.com/marketplace) and navigate to a property rental listing.
2. Click the **Analyze Listing** button on the page.
3. View the Recon Score breakdown with concrete evidence and reasoning.


## Challenges

- **Ideation & scoping** — Narrowing down from broad real estate tooling ideas to a well-defined, buildable project.
- **Accuracy vs. trust** — Pivoted from predicting fraud probability to producing explainable, evidence-backed warnings, since ground truth data is scarce.
- **Algorithm design** — Researched real-world scam patterns from news articles, personal experiences, and community forums to inform the scoring rubric.
- **UI output tuning** — Carefully constructed prompt guardrails to produce results that are relevant, concise, and well-formatted for the extension UI.

## Future Work

- Expand compatibility to other web browsers (Firefox, Edge)
- Evaluate the model against labeled datasets for concrete reliability metrics
- Improve scoring accuracy with ML models, landlord background checks, description similarity detection, and reverse image search
- Link directly to Zillow references and similar listings so users can verify findings themselves
