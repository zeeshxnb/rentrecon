// Backend API URL - change this when deploying
export const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

// Analysis result freshness threshold (5 minutes)
export const RESULT_TTL_MS = 5 * 60 * 1000;
