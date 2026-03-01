import React from "react";
import { useAnalysis } from "./hooks/useAnalysis";
import ScoreDisplay from "./components/ScoreDisplay";
import RiskBadge from "./components/RiskBadge";
import ModuleScore from "./components/ModuleScore";
import FlagBreakdown from "./components/FlagBreakdown";
import EvidenceSection from "./components/EvidenceSection";
import LoadingState from "./components/LoadingState";
import ErrorState from "./components/ErrorState";
import EmptyState from "./components/EmptyState";
import Disclaimer from "./components/Disclaimer";

export default function App() {
  const { result, loading, error, refresh } = useAnalysis();

  return (
    <div className="w-[400px] min-h-[500px] max-h-[600px] overflow-y-auto bg-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-2">
        <svg
          className="w-5 h-5 text-blue-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <h1 className="text-base font-bold text-gray-800">Rent Recon</h1>
        {result && (
          <span className="ml-auto text-[10px] text-gray-400">
            {result.processing_time_ms}ms
          </span>
        )}
      </div>

      <div className="px-4 py-2">
        {/* States */}
        {loading && <LoadingState />}
        {error && <ErrorState message={error} onRetry={refresh} />}
        {!loading && !error && !result && <EmptyState />}

        {/* Results */}
        {!loading && !error && result && (
          <>
            <ScoreDisplay
              score={result.composite_score}
              color={result.risk_color}
            />
            <RiskBadge level={result.risk_level} />

            {/* Module breakdown */}
            <div className="mb-3">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                Module Scores
              </h3>
              {Object.entries(result.modules).map(([name, mod]) => (
                <ModuleScore key={name} name={name} module={mod} />
              ))}
            </div>

            {/* Flags */}
            <div className="mb-3">
              <FlagBreakdown flags={result.flags} />
            </div>

            {/* Evidence */}
            <div className="mb-3">
              <EvidenceSection evidence={result.evidence} />
            </div>

            {/* API errors (transparency) */}
            {result.api_errors.length > 0 && (
              <div className="mb-3 px-2.5 py-2 bg-orange-50 border border-orange-200 rounded-md">
                <p className="text-[10px] font-medium text-orange-600 mb-1">
                  Some services were unavailable:
                </p>
                {result.api_errors.map((err, i) => (
                  <p key={i} className="text-[10px] text-orange-500">
                    {err}
                  </p>
                ))}
              </div>
            )}

            <Disclaimer text={result.disclaimer} />
          </>
        )}
      </div>
    </div>
  );
}
