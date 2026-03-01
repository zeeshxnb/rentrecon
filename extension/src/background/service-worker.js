/**
 * service-worker.js - Background service worker for RentShield.
 *
 * Handles communication between content script and backend API.
 * Stores analysis results in chrome.storage.local for the popup to read.
 */

import { API_BASE_URL } from "../shared/constants.js";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ANALYZE_LISTING") {
    handleAnalyze(message.payload)
      .then((result) => {
        // Store result for popup to read
        chrome.storage.local.set({
          lastAnalysis: result,
          lastAnalysisTimestamp: Date.now(),
          analysisInProgress: false,
        });
        sendResponse({ success: true, data: result });
      })
      .catch((error) => {
        chrome.storage.local.set({ analysisInProgress: false });
        sendResponse({ success: false, error: error.message });
      });

    // Set loading state
    chrome.storage.local.set({ analysisInProgress: true });

    // Return true to indicate async response
    return true;
  }

  if (message.type === "GET_LAST_ANALYSIS") {
    chrome.storage.local.get(
      ["lastAnalysis", "lastAnalysisTimestamp", "analysisInProgress"],
      (result) => {
        sendResponse(result);
      }
    );
    return true;
  }

});

/**
 * Send listing data to the backend for analysis.
 */
async function handleAnalyze(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  return response.json();
}
