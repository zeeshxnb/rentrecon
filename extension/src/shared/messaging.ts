/**
 * Chrome extension messaging helpers.
 * Typed wrappers around chrome.runtime.sendMessage.
 */

import type { AnalysisResult } from "../popup/types";

export interface AnalysisState {
  lastAnalysis: AnalysisResult | null;
  lastAnalysisTimestamp: number | null;
  analysisInProgress: boolean;
}

export function getLastAnalysis(): Promise<AnalysisState> {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "GET_LAST_ANALYSIS" }, (response) => {
      resolve({
        lastAnalysis: response?.lastAnalysis || null,
        lastAnalysisTimestamp: response?.lastAnalysisTimestamp || null,
        analysisInProgress: response?.analysisInProgress || false,
      });
    });
  });
}

export function clearAnalysis(): Promise<void> {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "CLEAR_ANALYSIS" }, () => {
      resolve();
    });
  });
}
