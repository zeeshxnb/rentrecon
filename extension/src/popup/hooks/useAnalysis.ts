import { useState, useEffect } from "react";
import type { AnalysisResult } from "../types";
import { getLastAnalysis } from "../../shared/messaging";
import { RESULT_TTL_MS } from "../../shared/constants";

interface UseAnalysisReturn {
  result: AnalysisResult | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useAnalysis(): UseAnalysisReturn {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = () => {
    setLoading(true);
    setError(null);

    getLastAnalysis()
      .then((state) => {
        if (state.analysisInProgress) {
          setLoading(true);
          // Poll until analysis is done
          const interval = setInterval(() => {
            getLastAnalysis().then((s) => {
              if (!s.analysisInProgress) {
                clearInterval(interval);
                if (s.lastAnalysis) {
                  setResult(s.lastAnalysis);
                }
                setLoading(false);
              }
            });
          }, 500);
          return;
        }

        if (
          state.lastAnalysis &&
          state.lastAnalysisTimestamp &&
          Date.now() - state.lastAnalysisTimestamp < RESULT_TTL_MS
        ) {
          setResult(state.lastAnalysis);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to fetch analysis");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchAnalysis();
  }, []);

  return { result, loading, error, refresh: fetchAnalysis };
}
