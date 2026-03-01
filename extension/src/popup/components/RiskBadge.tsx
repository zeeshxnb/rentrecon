import React from "react";

interface Props {
  level: "low" | "moderate" | "high";
}

const BADGE_STYLES = {
  low: "bg-green-100 text-green-800 border-green-300",
  moderate: "bg-yellow-100 text-yellow-800 border-yellow-300",
  high: "bg-red-100 text-red-800 border-red-300",
};

const LABELS = {
  low: "Low Risk",
  moderate: "Moderate Risk",
  high: "High Risk",
};

const DESCRIPTIONS = {
  low: "Proceed with normal caution",
  moderate: "Verify independently before any payment",
  high: "Strong indicators of a scam listing",
};

export default function RiskBadge({ level }: Props) {
  return (
    <div className="text-center mb-4">
      <span
        className={`inline-block px-4 py-1.5 rounded-full text-sm font-semibold border ${BADGE_STYLES[level]}`}
      >
        {LABELS[level]}
      </span>
      <p className="text-xs text-gray-500 mt-1">{DESCRIPTIONS[level]}</p>
    </div>
  );
}
