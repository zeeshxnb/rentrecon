# RentShield Implementation Plan

## Context

RentShield is a Chrome extension that detects rental scams in Facebook groups by cross-referencing listing data against 3 real estate APIs (Zillow, Rentcast, Realtor.com) and using Gemini AI for NLP/image analysis. The repo is greenfield -- only `idea.md` exists. This plan covers the full build split across 3 developers for a 24-hour hackathon.

---

## Project Structure

```
rentshield/
├── idea.md
├── .gitignore
├── .env.example
│
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── railway.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, CORS, lifespan
│   │   ├── config.py                # pydantic-settings
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # API routes
│   │   │   ├── schemas.py           # Request/response Pydantic models
│   │   │   └── deps.py              # Shared httpx client
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── gemini_nlp.py        # Gemini NLP extraction
│   │   │   ├── gemini_vision.py     # Gemini Vision image analysis
│   │   │   ├── zillow.py            # RapidAPI Zillow wrapper
│   │   │   ├── rentcast.py          # Rentcast API
│   │   │   ├── realtor.py           # Realtor.com via RapidAPI
│   │   │   └── scoring.py           # Orchestrator + composite scoring
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── nlp.py, vision.py, zillow.py, rentcast.py, realtor.py, scoring.py
│   │   ├── prompts/
│   │   │   ├── nlp_extraction.py    # Gemini NLP prompt templates
│   │   │   └── vision_analysis.py   # Gemini Vision prompt templates
│   │   └── utils/
│   │       ├── cache.py             # In-memory TTL cache (cachetools)
│   │       ├── rate_limiter.py      # API rate limiting
│   │       └── normalizers.py       # Address/price normalization
│   └── tests/
│       ├── conftest.py, test_api.py, test_scoring.py
│       ├── test_zillow.py, test_rentcast.py, test_realtor.py
│       ├── test_gemini_nlp.py, test_gemini_vision.py
│       └── fixtures/                # Sample posts + mock API responses
│
├── extension/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── public/
│   │   ├── manifest.json            # Manifest V3
│   │   └── icons/
│   └── src/
│       ├── content/
│       │   ├── content.js           # Entry point (vanilla JS)
│       │   ├── extractor.js         # DOM data extraction
│       │   ├── injector.js          # "Analyze Listing" button injection
│       │   └── content.css
│       ├── background/
│       │   └── service-worker.js    # Relay between content script and backend
│       ├── popup/
│       │   ├── index.html, main.tsx, App.tsx, index.css
│       │   ├── components/
│       │   │   ├── ScoreDisplay.tsx  # Circular SVG gauge (green/yellow/red)
│       │   │   ├── RiskBadge.tsx     # "Low/Moderate/High Risk" badge
│       │   │   ├── FlagBreakdown.tsx # List of triggered flags
│       │   │   ├── EvidenceSection.tsx # Source data cards
│       │   │   ├── ModuleScore.tsx   # Per-module score row
│       │   │   ├── LoadingState.tsx, ErrorState.tsx, EmptyState.tsx
│       │   │   └── Disclaimer.tsx
│       │   ├── hooks/useAnalysis.ts
│       │   └── types/index.ts
│       └── shared/
│           ├── constants.ts         # API_BASE_URL
│           └── messaging.ts         # Chrome messaging helpers
```

---

## Environment Variables

```env
# Backend .env
GEMINI_API_KEY=<key>
GEMINI_MODEL=gemini-2.0-flash
RAPIDAPI_KEY=<key>                   # Shared for Zillow + Realtor.com
ZILLOW_API_HOST=zillow-com1.p.rapidapi.com
REALTOR_API_HOST=realtor16.p.rapidapi.com
RENTCAST_API_KEY=<key>               # Direct API, not RapidAPI
RENTCAST_API_BASE_URL=https://api.rentcast.io/v1
ALLOWED_ORIGINS=chrome-extension://<id>
CACHE_TTL_SECONDS=3600
```

---

## Backend Dependencies

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.1
httpx==0.28.1
google-genai==1.5.0
python-dotenv==1.0.1
cachetools==5.5.1
slowapi==0.1.9
pytest==8.3.4
pytest-asyncio==0.25.0
pytest-httpx==0.35.0
```

---

## API Endpoints

### `POST /api/v1/analyze` (primary endpoint)

**Request:**
```python
class AnalyzeRequest(BaseModel):
    post_text: str
    image_urls: list[str] = []
    has_video: bool = False
    facebook_poster_name: str | None = None
    source_url: str | None = None
```

**Response:**
```python
class AnalyzeResponse(BaseModel):
    composite_score: int              # 0-100
    risk_level: str                   # "low" | "moderate" | "high"
    risk_color: str                   # "green" | "yellow" | "red"
    modules: ModuleBreakdown          # Per-module scores
    flags: list[Flag]                 # All triggered flags
    evidence: list[Evidence]          # Source data cards
    extracted_data: ExtractedData     # What Gemini extracted
    disclaimer: str
    processing_time_ms: int
    api_errors: list[str]             # Transparency on failures
```

### `GET /api/v1/health` (health check)
### `POST /api/v1/analyze/dry-run` (dev only, uses mock data)

---

## 3 External API Integrations

### 1. RapidAPI Zillow Wrapper (`zillow-com1.p.rapidapi.com`)
- **Used for:** Address lookup, listing verification, rent estimate, comparable rentals
- **Endpoints:** `/propertyExtendedSearch`, `/property`, `/rentEstimate`, `/similarForRent`
- **Rate limit:** ~500 req/month (free tier). Cache property lookups 1 hour.
- **Fallback:** Skip module, return 0 points with `status: "error"`

### 2. Rentcast API (`api.rentcast.io/v1`)
- **Used for:** Zip-level median rent, market statistics, bedroom-specific medians
- **Endpoints:** `/markets` (zipCode param), `/listings/rental/long-term`
- **Rate limit:** 20 req/sec hard limit. Cache market data 24 hours.
- **Fallback:** Fall back to Zillow `rentEstimate`. If both fail, skip price module.

### 3. Realtor.com via RapidAPI (`realtor16.p.rapidapi.com`)
- **Used for:** Cross-referencing listings found on Zillow, agent/broker verification
- **Endpoints:** `/search` or `/property_list/`, `/property_detail`
- **Rate limit:** ~100 req/month (most constrained). Cache 6 hours.
- **Fallback:** Address lookup runs with Zillow alone. Cross-reference sub-score skipped.

---

## Five Scoring Modules

### Module 1: Address Lookup & Verification (max +25)
- Fires only if Gemini NLP extracts a full address
- Queries Zillow AND Realtor.com for the address
- Scoring:
  - Listing found + posted rent < 70% of listed rent → +20
  - Poster name != agent/owner name → +5
  - Poster name == agent/owner → -5 (reduces score)
  - For Sale only (not For Rent) → +15
  - Listing found on one platform but not other → +5
  - No listing found for claimed address → +10
  - No address extracted → module skipped, 0 points

### Module 2: Price Anomaly Detection (max +30)
- Fires only if Gemini NLP extracts rent amount AND zip code
- Queries Rentcast for area median, Zillow `rentEstimate` as backup
- Scoring:
  - Rent < 65% of median → +30 (HIGH)
  - Rent < 80% of median → +15 (MODERATE)
  - Rent < 90% of median → +5 (slight)
  - Normal range → 0
- Evidence: "Area median for {zip}: ${median}/mo. Listed: ${rent}/mo. {pct}% below."

### Module 3: NLP Description Analysis (max +25)
- Gemini extracts: rent, zip, contact info, suspicious phrases, missing signals
- Suspicious phrase scoring (max 15 pts):
  - Urgency language → +3 each
  - Deposit pressure → +4 each (weighted highest)
  - Avoidance language → +3 each
  - Vagueness → +2 each
- External contact info (max 7 pts):
  - Phone in post → +2, Email in post → +2, Payment apps (Venmo/Zelle/CashApp) → +3
- Missing legitimacy signals (max 3 pts):
  - No address → +1, No lease terms → +1, No landlord name → +1

### Module 4: Image Analysis via Gemini Vision (max +20)
- Send up to 5 image URLs to Gemini Vision
- Scoring:
  - 0 images → +5, 1-2 images → +3
  - Watermark detected → +4 per image
  - Stock photo detected → +4 per image
  - Professional staging + location inconsistency → +3 per image

### Module 5: Video Presence (bonus -15)
- Content script checks DOM for `<video>`, `[data-video-id]`, `[aria-label*="video"]`
- Video detected → -15 points. No video → 0.

### Composite Score = sum of all modules, clamped to [0, 100]
- 0-30: Low Risk (green) | 31-60: Moderate Risk (yellow) | 61-100: High Risk (red)

---

## Scoring Engine Orchestration (`services/scoring.py`)

```
Phase 1: Gemini NLP extraction (must complete first -- other modules depend on it)
Phase 2: Run in parallel via asyncio.gather:
  - Address lookup (Zillow + Realtor.com) -- only if address extracted
  - Price anomaly (Rentcast + Zillow) -- only if rent + zip extracted
  - Image analysis (Gemini Vision) -- only if images present
Phase 3: NLP scoring (synchronous, uses NLP extraction result)
Phase 4: Video presence scoring (trivial, from request.has_video)
Phase 5: Sum scores, clamp, collect flags + evidence, build response
```

---

## Chrome Extension Architecture

### Content Script (`content.js` + `extractor.js` + `injector.js`)
- MutationObserver watches for new posts (infinite scroll)
- Injects "Analyze Listing" button on `[role="article"]` elements
- On click: extracts post_text, image_urls, has_video, poster_name
- **DOM extraction uses multi-strategy approach** (never rely on class names):
  - Strategy 1: `[role="article"]` container
  - Strategy 2: `[data-ad-rendering-role="profile_name"]` ancestor
  - Strategy 3: Walk up from clicked button
  - Text: concatenate `[dir="auto"]` spans, deduplicate
  - Images: `img[src*="scontent"]`, filter out emoji/profile pics
  - Video: check for `<video>`, `[data-video-id]`, `[aria-label*="video"]`
  - Poster name: `h2 a`, `h3 a`, `[data-ad-rendering-role="profile_name"]`

### Service Worker (`service-worker.js`)
- Receives `ANALYZE_LISTING` message from content script
- POSTs to backend `/api/v1/analyze`
- Stores result in `chrome.storage.local` for popup to read
- Handles `GET_LAST_ANALYSIS` messages from popup

### Popup UI (React + TailwindCSS)
- On open: reads `lastAnalysis` from storage
- Displays: ScoreDisplay (SVG gauge), RiskBadge, ModuleScore x5, FlagBreakdown, EvidenceSection, Disclaimer
- States: Loading, Error, Empty ("Navigate to a Facebook group post"), Result
- Popup size: 400px x 600px

---

## Potential Pitfalls & Mitigations

| Pitfall | Severity | Mitigation |
|---------|----------|------------|
| **Facebook DOM instability** | CRITICAL | Never use class names. Use `[role]`, `[dir]`, semantic attrs. Multi-strategy extraction in `extractor.js`. Single file to update when DOM changes. |
| **API rate limit exhaustion** | HIGH | Aggressive caching (1hr property, 24hr market, 6hr realtor). Request counting. Degrade gracefully at 80% threshold. Pre-warm cache for demo. |
| **CORS issues** | HIGH | Configure FastAPI CORSMiddleware. Service worker `fetch` bypasses CORS, but popup direct calls need it. Use `allow_origins=["*"]` in dev, specific origins in prod. |
| **Facebook image URL inaccessibility** | HIGH | Test if Gemini can fetch `scontent-*.fbcdn.net` URLs. Fallback: content script converts to base64 via canvas, or backend downloads via httpx then sends bytes to Gemini. HEAD request validation before Vision call. |
| **Gemini latency (3-8s per call)** | MEDIUM | Use `gemini-2.0-flash`. Run NLP first, then Vision in parallel with real estate APIs. 12s timeout for Gemini, regex fallback if NLP times out. |
| **Missing data in post** | MEDIUM | Every module has a "skipped" state returning 0 points. UI shows which modules contributed. Even NLP + Video alone produce a useful score. |
| **Service worker lifecycle (MV3)** | MEDIUM | `fetch` keeps worker alive during requests. Store state in `chrome.storage.local`. Popup shows retry on no-response. |
| **API key security** | MEDIUM | All keys in backend `.env`, never in extension. Extension only talks to our backend. Rate limit backend with `slowapi`. |
| **Extension size limit (4MB)** | LOW | Vite tree-shaking + TailwindCSS purge. Expected ~200-300KB. |

---

## Error Handling & Graceful Degradation

**Principle: No single API failure prevents returning a result.**

- Gemini NLP fails → regex fallback extracts rent (`$X,XXX`), zip (`\d{5}`), phone, email
- Gemini Vision fails → image module returns 0, `status: "error"`
- Zillow 429/5xx → return cached result or skip module
- Rentcast fails → use Zillow `rentEstimate` as fallback
- Realtor.com fails → address lookup runs with Zillow alone
- All 3 real estate APIs fail → only NLP + Vision modules contribute, lower confidence warning
- DOM extraction fails → popup shows "Could not extract listing data" error

**Timeouts:**
- External API calls: 8 seconds
- Gemini calls: 12 seconds
- Total `/analyze` request: 20 seconds

---

## Caching Strategy (in-memory TTLCache, no Redis needed)

| Cache Key | TTL | Rationale |
|-----------|-----|-----------|
| `zillow:property:{address_hash}` | 1 hour | Property data stable |
| `zillow:rent_estimate:{address_hash}` | 1 hour | Same |
| `rentcast:market:{zip_code}` | 24 hours | Monthly statistics |
| `realtor:property:{address_hash}` | 6 hours | Moderate refresh |
| `gemini:nlp:{text_hash}` | 30 minutes | Same text = same extraction |
| `gemini:vision:{urls_hash}` | 1 hour | Same images = same analysis |

---

## Work Split (3 People)

### Backend Dev 1 (BD1): Core API + Gemini + Scoring Engine
**Files:** `main.py`, `config.py`, `router.py`, `schemas.py`, `deps.py`, `gemini_nlp.py`, `gemini_vision.py`, `scoring.py`, `prompts/*`, `models/nlp.py`, `models/vision.py`, `models/scoring.py`

### Backend Dev 2 (BD2): 3 External API Integrations + Data Layer
**Files:** `zillow.py`, `rentcast.py`, `realtor.py`, `models/zillow.py`, `models/rentcast.py`, `models/realtor.py`, `cache.py`, `rate_limiter.py`, `normalizers.py`, all test files

### Frontend Dev (FE): Chrome Extension (Content Script + Popup)
**Files:** Everything under `extension/`

---

## Phased Timeline

### Phase 1: Foundation (Hours 1-4)

**BD1:**
1. Set up FastAPI skeleton (`main.py`, `config.py`, `requirements.txt`, `Dockerfile`)
2. Define ALL Pydantic models (`schemas.py`, `models/*`) -- **coordinate with BD2 on model interfaces**
3. Implement `/api/v1/health` endpoint
4. Implement `/api/v1/analyze` stub returning mock data -- **FE needs this to start integration**

**BD2:**
1. Set up cache utility (`utils/cache.py`)
2. Implement Zillow service + model -- test with real API key
3. Implement Rentcast service + model
4. Implement Realtor.com service + model

**FE:**
1. Set up Vite + React + TailwindCSS project
2. Create `manifest.json` (Manifest V3)
3. Implement content script (`content.js`, `extractor.js`, `injector.js`) -- **start early, highest risk**
4. Implement service worker -- **needs API shape from BD1 task 2**

### Phase 2: Core Logic (Hours 4-8)

**BD1:**
5. Implement Gemini NLP service + prompt templates -- test with sample posts
6. Implement Gemini Vision service + prompt templates
7. Implement NLP scoring logic in `scoring.py`

**BD2:**
5. Implement data normalization layer (addresses, prices, zips)
6. Implement address lookup scoring logic (Zillow + Realtor cross-reference)
7. Implement price anomaly scoring logic (Rentcast + Zillow fallback)
8. Write unit tests for all 3 API services with mock fixtures

**FE:**
5. Build all popup components with mock data (ScoreDisplay, FlagBreakdown, etc.)
6. Implement `useAnalysis` hook
7. Wire popup App.tsx with state management

### Phase 3: Integration (Hours 8-12)

**BD1:**
8. Wire scoring engine orchestrator (the `analyze_listing` function with `asyncio.gather`)
9. Replace `/analyze` stub with real orchestrator
10. Add error handling, timeouts, graceful degradation
11. Deploy to Railway

**BD2:**
9. Integration test all 3 APIs end-to-end with real data
10. Implement rate limiting (`slowapi` in `main.py`)
11. Write cache warming script for demo addresses

**FE:**
8. Integration test with live backend
9. Polish UI (loading states, error states, animations)
10. Test on real Facebook group posts

### Phase 4: Polish & Demo Prep (Hours 12-16)
All devs: Fix bugs, optimize perf (< 5s target), record backup demo video, prepare slides, test 5+ real posts.

---

## Critical Coordination Points

1. **Hour 1:** All 3 agree on `AnalyzeRequest`/`AnalyzeResponse` schema shapes
2. **Hour 4:** BD1 deploys stub endpoint; FE confirms integration works
3. **Hour 8:** BD1 + BD2 sync on scoring module interfaces
4. **Hour 10:** All 3 test end-to-end with real data

## Dependency Graph (Critical Path)

```
BD1: Schemas → Stub endpoint → Gemini NLP → Gemini Vision → Scoring Engine → Real endpoint → Deploy
                    │                                              ↑
BD2: Cache → Zillow → Rentcast → Realtor → Normalizer → API Scoring Logic ─┘
                                                                    │
FE:  Vite setup → Content Script → Service Worker → Popup UI → Integration → Polish
                                         │                          ↑
                                         └── needs API shape ───────┘
```

---

## Deployment

**Backend (Railway):**
1. Push to GitHub → Connect Railway → Set env vars → Deploy
2. Verify `/api/v1/health` returns 200
3. Note public URL, update extension's `API_BASE_URL`

**Extension:**
1. `npm run build` → load `dist/` as unpacked extension in Chrome

**Pre-Demo Checklist:**
- [ ] Backend health check passing
- [ ] All API keys set (GEMINI, RAPIDAPI, RENTCAST)
- [ ] Extension loaded with correct backend URL
- [ ] Cache pre-warmed with 2-3 test addresses
- [ ] Facebook group with test posts bookmarked
- [ ] Backup screenshots of successful results

---

## Verification / Testing

1. **Unit tests:** `pytest` for all services with mocked API responses
2. **Integration test:** FastAPI TestClient with mocked externals, verify full request/response
3. **Manual E2E:** Load extension → navigate to FB group → click Analyze → verify popup shows score < 5s
4. **Test fixtures:** 5 canonical posts (obvious scam, hijacked listing, legitimate, minimal, edge case)
5. **Facebook DOM test:** Verify content script on 3+ different FB group post formats
