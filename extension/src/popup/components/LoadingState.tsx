import React from "react";

export default function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6">
      <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4" />
      <h2 className="text-lg font-semibold text-gray-700">Analyzing Listing</h2>
      <p className="text-sm text-gray-400 mt-1 text-center">
        Cross-referencing with Zillow, Rentcast, and Realtor.com...
      </p>
    </div>
  );
}
