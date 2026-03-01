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
let debounceTimer = null;

export function initInjector() {
  tryInject();

  const observer = new MutationObserver(() => {
    if (debounceTimer) return;
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      if (isMarketplaceListing() && !document.querySelector(`.${CONTAINER_CLASS}`)) {
        tryInject();
      }
    }, 300);
  });

  observer.observe(document.body, { childList: true, subtree: true });

  window.addEventListener("popstate", () => tryInject());

  const origPushState = history.pushState;
  history.pushState = function (...args) {
    origPushState.apply(this, args);
    setTimeout(tryInject, 300);
  };
}

function tryInject() {
  if (!isMarketplaceListing()) return;
  if (document.querySelector(`.${CONTAINER_CLASS}`)) return;

  const titleEl = findTitleElement();
  if (!titleEl) {
    setTimeout(tryInject, 500);
    return;
  }

  injectContainer(titleEl);
}

function findTitleElement() {
  const main = document.querySelector('[role="main"]');
  const root = main || document.body;

  const headings = root.querySelectorAll("h1");
  for (const h of headings) {
    const text = h.innerText.trim();
    if (text.length > 3 && !text.includes("Marketplace") && !text.includes("Facebook")) {
      return h;
    }
  }

  const h2s = root.querySelectorAll("h2");
  for (const h of h2s) {
    const text = h.innerText.trim();
    if (text.length > 3 && !text.includes("Marketplace") && !text.includes("Facebook")) {
      return h;
    }
  }

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

  // Good signals from completed modules — only genuinely positive results
  if (data.modules) {
    for (const key of ["video_presence", "address_lookup", "price_anomaly", "nlp_analysis", "image_analysis"]) {
      if (modulesWithFlags.has(key)) continue;
      const mod = data.modules[key];
      if (!mod || mod.status !== "completed") continue;

      if (key === "video_presence") {
        // Only show video as good if video was actually found (score < 0 = bonus)
        if (mod.score < 0) good.push({ text: mod.details, type: "good" });
        continue;
      }

      if (mod.score <= 0 && mod.details) {
        good.push({ text: mod.details, type: "good" });
      }
    }
  }

  // Unverified modules — show as yellow warnings (not gray)
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
    ordered.push({ text: "Analysis complete — no strong signals detected", type: "good" });
  }

  return ordered;
}

/**
 * Inject the Rent Recon container above the title, separator below.
 */
function injectContainer(titleEl) {
  if (!titleEl.parentNode) return;

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
            showResults(container, btn, separator, response.data);
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
    titleEl.parentNode.insertBefore(container, titleEl);
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
      return `<div class="recon-reason ${cls}">${icon} ${r.text}</div>`;
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
    container.remove();
  });
}
