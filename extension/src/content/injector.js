/**
 * injector.js - Injects the "Analyze Listing" button into Facebook posts.
 *
 * Uses a MutationObserver to watch for dynamically loaded posts
 * (Facebook uses infinite scroll) and injects the button on each post.
 */

import { extractPostData } from "./extractor.js";

const BUTTON_CLASS = "rentshield-analyze-btn";

/**
 * Initialize the injector: scan existing posts and watch for new ones.
 */
export function initInjector() {
  // Inject on all existing posts
  const existingPosts = document.querySelectorAll('[role="article"]');
  existingPosts.forEach((post) => injectButton(post));

  // Watch for new posts loaded via infinite scroll
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;

        // Check if the added node itself is a post
        if (node.getAttribute && node.getAttribute("role") === "article") {
          injectButton(node);
        }

        // Check children for posts
        const posts = node.querySelectorAll
          ? node.querySelectorAll('[role="article"]')
          : [];
        posts.forEach((post) => injectButton(post));
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
}

/**
 * Inject the RentShield "Analyze Listing" button into a post element.
 */
function injectButton(postElement) {
  // Don't inject twice
  if (postElement.querySelector(`.${BUTTON_CLASS}`)) return;

  const btn = document.createElement("button");
  btn.className = BUTTON_CLASS;
  btn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px; vertical-align: middle;">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
    <span>Analyze Listing</span>
  `;

  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    e.preventDefault();

    // Update button state
    btn.disabled = true;
    btn.querySelector("span").textContent = "Analyzing...";
    btn.classList.add("rentshield-loading");

    try {
      const data = extractPostData(postElement);

      // Send to service worker
      chrome.runtime.sendMessage(
        { type: "ANALYZE_LISTING", payload: data },
        (response) => {
          btn.disabled = false;
          btn.querySelector("span").textContent = "Analyze Listing";
          btn.classList.remove("rentshield-loading");

          if (chrome.runtime.lastError) {
            console.error("RentShield error:", chrome.runtime.lastError);
            return;
          }

          if (response && response.success) {
            btn.querySelector("span").textContent = "View Results";
            btn.classList.add("rentshield-done");
          }
        }
      );
    } catch (err) {
      console.error("RentShield extraction error:", err);
      btn.disabled = false;
      btn.querySelector("span").textContent = "Analyze Listing";
      btn.classList.remove("rentshield-loading");
    }
  });

  // Position relative to post
  postElement.style.position = "relative";
  postElement.appendChild(btn);
}
