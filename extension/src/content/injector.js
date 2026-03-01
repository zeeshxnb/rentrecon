/**
 * injector.js - Injects the "Analyze Listing" button into Facebook Marketplace listings.
 *
 * Targets /marketplace/item/ pages and places the button above the listing title.
 * Uses a MutationObserver since Facebook is an SPA and loads content dynamically.
 */

import { extractListingData, isMarketplaceListing } from "./extractor.js";

const CONTAINER_CLASS = "recon-container";
const BUTTON_CLASS = "recon-analyze-btn";
const RESULTS_CLASS = "recon-results";

// Cache results per listing URL so re-analyzing doesn't hit APIs again
const resultCache = new Map();

export function initInjector() {
  tryInject();

  // React instantly to every DOM change (the checks inside are very cheap)
  new MutationObserver(() => {
    if (isMarketplaceListing()) {
      if (!document.querySelector(`.${CONTAINER_CLASS}`)) tryInject();
    } else {
      cleanup();
    }
  }).observe(document.body, { childList: true, subtree: true });

  function onNavigate() {
    if (isMarketplaceListing()) tryInject();
    else cleanup();
  }

  window.addEventListener("popstate", onNavigate);

  // Poll for URL changes and missing button -- pushState/replaceState overrides
  // don't work from the content script's isolated world
  let lastUrl = location.href;
  setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      cleanup();
    }
    // Continuously retry injection if on a listing page with no button
    if (isMarketplaceListing() && !document.querySelector(`.${CONTAINER_CLASS}`)) {
      tryInject();
    }
  }, 300);
}

function cleanup() {
  document.querySelectorAll(`.${CONTAINER_CLASS}`).forEach(el => el.remove());
  // Keep cache (results stay valid for the session)
}

function tryInject() {
  if (!isMarketplaceListing()) return;
  if (document.querySelector(`.${CONTAINER_CLASS}`)) return;

  const anchorEl = findAnchorElement();
  if (!anchorEl) return; // MutationObserver will call us again when it appears

  injectContainer(anchorEl);
}

function findAnchorElement() {
  const main = document.querySelector('[role="main"]');
  if (!main) return null;

  // Strategy 1: Find the "Message" / "Send message" button row and inject after it
  const buttons = main.querySelectorAll('[role="button"], button');
  for (const btn of buttons) {
    const text = (btn.innerText || btn.textContent || "").trim();
    if (text === "Message" || text === "Send Message" || text === "Send message") {
      // Walk up to the row container (the div holding Message + bookmark + ... buttons)
      let row = btn.closest("div");
      // Walk up a few levels to get the full button row wrapper
      for (let i = 0; i < 3 && row && row.parentNode; i++) {
        const parent = row.parentNode;
        // Stop when the parent contains significantly more than just the button row
        if (parent.querySelectorAll('[role="button"], button').length > 6) break;
        row = parent;
      }
      // The next sibling after the button row is where we inject before
      if (row && row.nextElementSibling) return row.nextElementSibling;
    }
  }

  // Strategy 2: Find any details section heading and inject before it
  const allSpans = main.querySelectorAll("span, h2, h3, h4");
  for (const el of allSpans) {
    const text = el.innerText.trim();
    if (text === "Building details" || text === "Building Details" ||
        text === "Unit details" || text === "Unit Details" ||
        text === "Property details" || text === "Property Details" ||
        text === "Home details" || text === "Home Details") {
      let section = el.closest("div");
      if (section) return section;
      return el;
    }
  }

  // Strategy 3: Find the listing title heading
  for (const tag of ["h1", "h2"]) {
    for (const h of main.querySelectorAll(tag)) {
      const text = h.innerText.trim();
      if (text.length > 3 && !text.includes("Marketplace") && !text.includes("Facebook")) {
        return h;
      }
    }
  }

  // Strategy 4: Fallback to top of main content
  if (main.firstElementChild) return main.firstElementChild;

  return null;
}

/**
 * Calculate the safety score (100% = safe, 0% = scam).
 */
function calcSafetyScore(data) {
  const inverted = 100 - data.composite_score;

  if (!data.modules) return inverted;

  const penalties = {
    address_lookup: 15,
    price_anomaly: 20,
    nlp_analysis: 15,
    image_analysis: 10,
    video_presence: 5,
  };

  let totalPenalty = 0;
  for (const [key, penalty] of Object.entries(penalties)) {
    const mod = data.modules[key];
    if (mod && mod.status !== "completed") {
      totalPenalty += penalty;
    }
  }

  const capped = Math.max(0, inverted - totalPenalty);
  return Math.round(capped);
}

/**
 * Pick color based on safety percentage (100=green, 0=red).
 */
function safetyColor(safety) {
  if (safety > 70) return "#4ade80";
  if (safety >= 40) return "#fbbf24";
  return "#f87171";
}

/**
 * Get all reasons from the analysis result.
 * Always ordered: green → yellow → red. No gray.
 * Unverified modules show as yellow warnings instead of gray.
 */
function getReasons(data) {
  const good = [];
  const bad = [];
  const warn = [];

  const modulesWithFlags = new Set();

  if (data.flags && data.flags.length > 0) {
    const sorted = [...data.flags].sort((a, b) => {
      const order = { high: 0, moderate: 1, low: 2, info: 3 };
      return (order[a.severity] ?? 4) - (order[b.severity] ?? 4);
    });
    for (const flag of sorted) {
      modulesWithFlags.add(flag.category);
      if (flag.severity === "info") {
        good.push({ text: flag.message, type: "good" });
      } else if (flag.severity === "moderate" || flag.severity === "low") {
        warn.push({ text: flag.message, type: "warn" });
      } else {
        bad.push({ text: flag.message, type: "bad" });
      }
    }
  }

  // Green signals now come from "info" severity flags emitted by the backend.
  // No need to pull from module details anymore.

  // Unverified modules -- show as yellow warnings (not gray)
  if (data.modules) {
    const skippedNames = {
      address_lookup: "Address could not be verified",
      price_anomaly: "Price could not be compared to market",
      nlp_analysis: "Description analysis unavailable",
      image_analysis: "Images could not be analyzed",
    };
    for (const [key, msg] of Object.entries(skippedNames)) {
      const mod = data.modules[key];
      if (mod && mod.status !== "completed") {
        warn.push({ text: msg, type: "warn" });
      }
    }
  }

  // Always: green → yellow → red
  const ordered = [...good, ...warn, ...bad];

  if (ordered.length === 0) {
    ordered.push({ text: "Analysis complete, no strong signals detected", type: "good" });
  }

  return ordered;
}

/**
 * Inject the Rent Recon container above the title, separator below.
 */
function injectContainer(anchorEl) {
  if (!anchorEl.parentNode) return;

  const container = document.createElement("div");
  container.className = CONTAINER_CLASS;

  const btn = document.createElement("button");
  btn.className = BUTTON_CLASS;
  btn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px; vertical-align: middle;">
      <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
    <span>Analyze Listing</span>
  `;
  container.appendChild(btn);

  const separator = document.createElement("div");
  separator.className = "recon-separator";
  container.appendChild(separator);

  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    e.preventDefault();

    const cacheKey = window.location.pathname;

    // Return cached result instantly if available
    if (resultCache.has(cacheKey)) {
      showResults(container, btn, separator, resultCache.get(cacheKey));
      return;
    }

    btn.disabled = true;
    btn.querySelector("span").textContent = "Analyzing...";
    btn.classList.add("recon-loading");

    try {
      const data = extractListingData();

      chrome.runtime.sendMessage(
        { type: "ANALYZE_LISTING", payload: data },
        (response) => {
          if (chrome.runtime.lastError) {
            console.error("Rent Recon error:", chrome.runtime.lastError.message);
            btn.disabled = false;
            btn.querySelector("span").textContent = "Analyze Listing";
            btn.classList.remove("recon-loading");
            return;
          }

          if (response && response.success) {
            resultCache.set(cacheKey, response.data);
            // Complete the fill animation, then show results
            btn.classList.add("recon-fill-done");
            setTimeout(() => {
              showResults(container, btn, separator, response.data);
            }, 350);
          } else {
            btn.disabled = false;
            btn.querySelector("span").textContent = "Analyze Listing";
            btn.classList.remove("recon-loading");
            console.error("Rent Recon analysis failed:", response?.error);
          }
        }
      );
    } catch (err) {
      console.error("Rent Recon extraction error:", err);
      btn.disabled = false;
      btn.querySelector("span").textContent = "Analyze Listing";
      btn.classList.remove("recon-loading");
    }
  });

  try {
    anchorEl.parentNode.insertBefore(container, anchorEl);
  } catch (err) {
    console.warn("Rent Recon: could not insert container", err);
  }
}

/**
 * Replace the button with the results box. Keep separator at bottom.
 */
function showResults(container, btn, separator, data) {
  btn.remove();

  const safety = calcSafetyScore(data);
  const color = safetyColor(safety);
  const reasons = getReasons(data);

  const box = document.createElement("div");
  box.className = RESULTS_CLASS;

  const reasonsHtml = reasons
    .map((r) => {
      let icon, cls;
      if (r.type === "good") {
        icon = "&#10003;"; cls = "recon-reason-good";
      } else if (r.type === "bad") {
        icon = "&#10007;"; cls = "recon-reason-bad";
      } else {
        icon = "&#9888;"; cls = "recon-reason-warn";
      }
      const truncated = r.text.length > 80 ? r.text.slice(0, 77) + "..." : r.text;
      return `<div class="recon-reason ${cls}">${icon} ${truncated}</div>`;
    })
    .join("");

  box.innerHTML = `
    <button class="recon-close" title="Close">&times;</button>
    <div class="recon-score-line">
      <span class="recon-score-label">Recon Score:</span>
      <span class="recon-score-value" style="color: ${color}">${safety}%</span>
    </div>
    <div class="recon-reasons">${reasonsHtml}</div>
  `;

  container.insertBefore(box, separator);

  box.querySelector(".recon-close").addEventListener("click", (e) => {
    e.stopPropagation();
    e.preventDefault();
    box.remove();

    // Show a "View Recon Score" button to re-open cached results
    const viewBtn = document.createElement("button");
    viewBtn.className = BUTTON_CLASS;
    viewBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px; vertical-align: middle;">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <span>View Recon Score</span>`;
    container.insertBefore(viewBtn, separator);

    viewBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      ev.preventDefault();
      viewBtn.remove();
      showResults(container, viewBtn, separator, data);
    });
  });
}
