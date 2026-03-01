/**
 * extractor.js - DOM data extraction for Facebook Marketplace rental listings.
 *
 * Targets /marketplace/item/ pages. Grabs ALL visible text from the listing
 * so the backend NLP can extract rent, address, ZIP, beds/baths, amenities,
 * and suspicious phrases. Uses structural selectors (role, dir, aria attrs)
 * rather than class names.
 */

/**
 * Check if we're on a Marketplace item page.
 */
export function isMarketplaceListing() {
  return window.location.pathname.includes("/marketplace/item/");
}

/**
 * Extract all listing data from the current Marketplace page.
 */
export function extractListingData() {
  return {
    post_text: extractAllText(),
    image_urls: extractImageUrls(),
    has_video: detectVideo(),
    facebook_poster_name: extractSellerName(),
    source_url: window.location.href,
  };
}

/**
 * Extract ALL visible text from the listing page.
 *
 * Uses innerText on the main content area to capture everything:
 * title, price, description, address, Unit Details (beds, baths, sqft,
 * amenities), Rental Location (city, state, ZIP), Walk Score, etc.
 * The backend NLP is designed to parse this and extract structured fields.
 */
function extractAllText() {
  const mainContent = document.querySelector('[role="main"]');
  if (mainContent) {
    const fullText = mainContent.innerText;
    // Cap at 10K chars to keep NLP calls reasonable
    if (fullText.length > 10000) {
      return fullText.slice(0, 10000);
    }
    return fullText;
  }

  // Fallback: gather text from dir="auto" elements
  const parts = new Set();
  const textNodes = document.body.querySelectorAll('[dir="auto"]');
  for (const node of textNodes) {
    const text = node.innerText.trim();
    if (text.length > 2) parts.add(text);
  }
  return [...parts].join("\n");
}

/**
 * Extract listing image URLs from the page.
 */
export function extractImageUrls() {
  const urls = new Set();

  // Marketplace listing images are large scontent images
  const imgs = document.querySelectorAll('img[src*="scontent"]');
  for (const img of imgs) {
    const src = img.src;
    const isLarge =
      (img.naturalWidth > 100 || img.width > 100) &&
      !isProfileOrEmoji(src);

    if (isLarge) {
      urls.add(src);
    }
  }

  // Also grab from image carousel / gallery containers
  const galleryImgs = document.querySelectorAll(
    '[aria-label*="photo" i] img, [aria-label*="image" i] img, [data-visualcompletion] img'
  );
  for (const img of galleryImgs) {
    if (img.src && img.src.includes("scontent") && !isProfileOrEmoji(img.src)) {
      urls.add(img.src);
    }
  }

  return Array.from(urls);
}

/**
 * Detect if a video is part of the actual listing (not nav, ads, stories).
 * Scoped to the listing's media/content area only.
 */
export function detectVideo() {
  const main = document.querySelector('[role="main"]');
  if (!main) return false;

  // Check for actual video elements within the listing content
  const videos = main.querySelectorAll("video");
  for (const v of videos) {
    // Must have meaningful dimensions (not a hidden/preload element)
    if (v.offsetWidth > 100 && v.offsetHeight > 100) return true;
  }

  // Check for Facebook's video player markers within listing area
  if (main.querySelector("[data-video-id]")) return true;

  // Check for video-specific containers (not nav links like "Watch")
  // Only match aria-labels that suggest an embedded video player, not navigation
  const videoEls = main.querySelectorAll('[aria-label*="video" i]');
  for (const el of videoEls) {
    // Skip navigation links and small elements
    if (el.tagName === "A" && el.closest("nav")) continue;
    if (el.offsetWidth > 200 && el.offsetHeight > 100) return true;
  }

  return false;
}

/**
 * Extract the seller's name from the listing page.
 */
export function extractSellerName() {
  // Marketplace shows seller info — look for profile links
  const links = document.querySelectorAll('a[href*="/marketplace/profile/"], a[href*="/user/"]');
  for (const link of links) {
    const text = link.innerText.trim();
    if (text.length > 1 && text.length < 50 && !text.includes("Marketplace")) {
      return text;
    }
  }

  // Fallback: look for seller section
  const allText = document.querySelectorAll('[dir="auto"]');
  let foundSeller = false;
  for (const el of allText) {
    const text = el.innerText.trim();
    if (text === "Seller" || text.includes("Listed by")) {
      foundSeller = true;
      continue;
    }
    if (foundSeller && text.length > 1 && text.length < 50) {
      return text;
    }
  }

  return null;
}

/**
 * Filter out profile pictures, emoji images, and reaction icons.
 */
function isProfileOrEmoji(url) {
  const lower = url.toLowerCase();
  return (
    lower.includes("emoji") ||
    lower.includes("profile") ||
    lower.includes("avatar") ||
    lower.includes("36x36") ||
    lower.includes("40x40") ||
    lower.includes("32x32") ||
    lower.includes("28x28")
  );
}
