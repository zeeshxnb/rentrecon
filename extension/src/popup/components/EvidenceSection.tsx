import React from "react";
import type { Evidence } from "../types";

interface Props {
  evidence: Evidence[];
}

const SOURCE_LABELS: Record<string, string> = {
  zillow: "Zillow",
  rentcast: "Rentcast",
  realtor: "Realtor.com",
  gemini_nlp: "AI Text Analysis",
  gemini_vision: "AI Image Analysis",
};

const SOURCE_COLORS: Record<string, string> = {
  zillow: "bg-blue-100 text-blue-700",
  rentcast: "bg-purple-100 text-purple-700",
  realtor: "bg-orange-100 text-orange-700",
  gemini_nlp: "bg-teal-100 text-teal-700",
  gemini_vision: "bg-indigo-100 text-indigo-700",
};

export default function EvidenceSection({ evidence }: Props) {
  if (evidence.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
        Evidence
      </h3>
      {evidence.map((item, i) => (
        <div
          key={i}
          className="flex items-start gap-2 px-2.5 py-2 bg-white border border-gray-200 rounded-md"
        >
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded font-medium flex-shrink-0 ${
              SOURCE_COLORS[item.source] || "bg-gray-100 text-gray-600"
            }`}
          >
            {SOURCE_LABELS[item.source] || item.source}
          </span>
          <div className="min-w-0">
            <p className="text-xs text-gray-500">{item.label}</p>
            <p className="text-xs font-medium text-gray-800 break-words">
              {item.value}
            </p>
            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[10px] text-blue-500 hover:underline"
              >
                View source
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
