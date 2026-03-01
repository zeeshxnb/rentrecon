import React from "react";

export default function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6">
      <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
        <svg
          className="w-8 h-8 text-blue-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-700">Rent Recon</h2>
      <p className="text-sm text-gray-400 mt-2 text-center leading-relaxed">
        Navigate to a Facebook Marketplace rental listing and click the{" "}
        <span className="font-medium text-blue-600">Analyze Listing</span>{" "}
        button to check for scam indicators.
      </p>
    </div>
  );
}
