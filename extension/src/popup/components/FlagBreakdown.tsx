import React from "react";
import type { Flag } from "../types";

interface Props {
  flags: Flag[];
}

const SEVERITY_STYLES = {
  high: { dot: "bg-red-500", text: "text-red-700", bg: "bg-red-50" },
  moderate: { dot: "bg-yellow-500", text: "text-yellow-700", bg: "bg-yellow-50" },
  low: { dot: "bg-blue-500", text: "text-blue-700", bg: "bg-blue-50" },
  info: { dot: "bg-green-500", text: "text-green-700", bg: "bg-green-50" },
};

export default function FlagBreakdown({ flags }: Props) {
  if (flags.length === 0) {
    return (
      <div className="text-center py-3 text-sm text-gray-400">
        No flags triggered
      </div>
    );
  }

  // Sort: high first, then moderate, low, info
  const order = { high: 0, moderate: 1, low: 2, info: 3 };
  const sorted = [...flags].sort(
    (a, b) => (order[a.severity] ?? 4) - (order[b.severity] ?? 4)
  );

  return (
    <div className="space-y-1.5">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
        Flags
      </h3>
      {sorted.map((flag, i) => {
        const style = SEVERITY_STYLES[flag.severity] || SEVERITY_STYLES.info;
        return (
          <div
            key={i}
            className={`flex items-start gap-2 px-2.5 py-1.5 rounded-md ${style.bg}`}
          >
            <span
              className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${style.dot}`}
            />
            <span className={`text-xs ${style.text}`}>{flag.message}</span>
          </div>
        );
      })}
    </div>
  );
}
