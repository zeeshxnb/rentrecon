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
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"
          />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-700">RentShield</h2>
      <p className="text-sm text-gray-400 mt-2 text-center leading-relaxed">
        Navigate to a rental listing in a Facebook group and click the{" "}
        <span className="font-medium text-blue-600">Analyze Listing</span>{" "}
        button to check for scam indicators.
      </p>
    </div>
  );
}
