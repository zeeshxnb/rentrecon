import React from "react";

interface Props {
  text: string;
}

export default function Disclaimer({ text }: Props) {
  return (
    <div className="mt-4 px-3 py-2 bg-gray-100 rounded-md">
      <p className="text-[10px] text-gray-500 text-center leading-relaxed">
        {text}
      </p>
    </div>
  );
}
