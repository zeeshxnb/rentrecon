import React, { useEffect, useState } from "react";

interface Props {
  score: number;
  color: "green" | "yellow" | "red";
}

const COLOR_MAP = {
  green: { stroke: "#22c55e", bg: "#f0fdf4", text: "#15803d" },
  yellow: { stroke: "#eab308", bg: "#fefce8", text: "#a16207" },
  red: { stroke: "#ef4444", bg: "#fef2f2", text: "#dc2626" },
};

export default function ScoreDisplay({ score, color }: Props) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const colors = COLOR_MAP[color];

  // Animate score from 0 to final value
  useEffect(() => {
    const duration = 800;
    const start = performance.now();

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out curve
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.round(eased * score));
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }, [score]);

  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="flex flex-col items-center py-4">
      <div className="relative w-36 h-36">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          {/* Background circle */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="10"
          />
          {/* Score arc */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            style={{ transition: "stroke-dashoffset 0.1s ease" }}
          />
        </svg>
        {/* Score number in center */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-4xl font-bold"
            style={{ color: colors.text }}
          >
            {animatedScore}
          </span>
          <span className="text-xs text-gray-500 mt-1">/ 100</span>
        </div>
      </div>
    </div>
  );
}
