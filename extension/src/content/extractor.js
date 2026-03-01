/**
 * extractor.js - DOM data extraction for Facebook rental posts.
 *
 * Uses structural selectors (role, dir, aria attributes) rather than
 * class names, since Facebook's class names are dynamically generated
 * and change frequently.
 */

/**
 * Extract all listing data from a Facebook post element.
 */
export function extractPostData(postElement) {
  return {
    post_text: extractText(postElement),
    image_urls: extractImageUrls(postElement),
    has_video: detectVideo(postElement),
    facebook_poster_name: extractPosterName(postElement),
    source_url: window.location.href,
  };
}

/**
 * Extract post text using multiple strategies.
 * Facebook wraps post text in nested divs with dir="auto".
 */
function extractText(el) {
  // Strategy 1: Find all dir="auto" text nodes
  const textNodes = el.querySelectorAll('[dir="auto"]');
  const texts = Array.from(textNodes)
    .map((n) => n.innerText.trim())
    .filter((t) => t.length > 0);

  // Deduplicate (FB sometimes renders text twice in different containers)
  const unique = [...new Set(texts)];

  if (unique.length > 0) {
    return unique.join("\n");
  }

  // Strategy 2: Fallback to innerText of the entire post
  return el.innerText || "";
}

/**
 * Extract image URLs from the post.
 * Facebook hosts images on scontent-*.fbcdn.net CDN.
 */
export function extractImageUrls(el) {
  const urls = new Set();

  // Strategy 1: Direct img tags with Facebook CDN URLs
  const imgs = el.querySelectorAll('img[src*="scontent"]');
  for (const img of imgs) {
    if (!isProfileOrEmoji(img.src)) {
      urls.add(img.src);
    }
  }

  // Strategy 2: Images inside photo containers
  const photoImgs = el.querySelectorAll(
    '[data-visualcompletion] img, [role="img"] img'
  );
  for (const img of photoImgs) {
    if (img.src && img.src.includes("scontent") && !isProfileOrEmoji(img.src)) {
      urls.add(img.src);
    }
  }

  return Array.from(urls);
}

/**
 * Detect if a video element is present in the post.
 */
export function detectVideo(el) {
  // Check for HTML5 video element
  if (el.querySelector("video")) return true;

  // Check for Facebook's video player wrappers
  if (el.querySelector("[data-video-id]")) return true;
  if (el.querySelector('[aria-label*="video" i]')) return true;
  if (el.querySelector('[aria-label*="Video" i]')) return true;

  return false;
}

/**
 * Extract the poster's name from the post.
 */
export function extractPosterName(el) {
  // Strategy 1: Profile name rendering role
  const profileName = el.querySelector(
    '[data-ad-rendering-role="profile_name"]'
  );
  if (profileName) return profileName.innerText.trim();

  // Strategy 2: Heading links (h2, h3, h4)
  const headingLink = el.querySelector("h2 a, h3 a, h4 a");
  if (headingLink) return headingLink.innerText.trim();

  // Strategy 3: Strong tag near the top
  const strong = el.querySelector("strong");
  if (strong) return strong.innerText.trim();

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
    lower.includes("32x32")
  );
}
