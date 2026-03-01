import React, { useState } from "react";
import type { ModuleResult } from "../types";

interface Props {
  name: string;
  module: ModuleResult;
}

const MODULE_LABELS: Record<string, string> = {
  address_lookup: "Address Verification",
  price_anomaly: "Price Analysis",
  nlp_analysis: "Text Analysis",
  image_analysis: "Image Analysis",
  video_presence: "Video Check",
};

const STATUS_ICONS: Record<string, string> = {
  completed: "",
  skipped: "—",
  error: "!",
};

export default function ModuleScore({ name, module: mod }: Props) {
  const [expanded, setExpanded] = useState(false);
  const label = MODULE_LABELS[name] || name;
  const isBonus = mod.max_score < 0;

  return (
    <div className="border border-gray-200 rounded-lg mb-2 overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-50 transition"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">
            {STATUS_ICONS[mod.status]}
          </span>
          <span className="text-sm font-medium text-gray-700">{label}</span>
          {mod.status === "skipped" && (
            <span className="text-xs text-gray-400">(skipped)</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-sm font-semibold ${
              mod.score > 15
                ? "text-red-600"
                : mod.score > 5
                ? "text-yellow-600"
                : mod.score < 0
                ? "text-green-600"
                : "text-gray-600"
            }`}
          >
            {mod.score > 0 ? "+" : ""}
            {mod.score}
          </span>
          <span className="text-xs text-gray-400">
            / {isBonus ? "" : "+"}
            {mod.max_score}
          </span>
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${
              expanded ? "rotate-180" : ""
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-2 border-t border-gray-100">
          <p className="text-xs text-gray-500 mt-1">{mod.details}</p>
          {mod.sub_flags.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {mod.sub_flags.map((flag, i) => (
                <li key={i} className="text-xs text-gray-600 flex gap-1">
                  <span className="text-gray-400">-</span>
                  {flag}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
