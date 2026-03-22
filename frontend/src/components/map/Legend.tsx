"use client";

interface LegendProps {
  metric: "drs" | "ebs";
}

export default function Legend({ metric }: LegendProps) {
  const isDrs = metric === "drs";

  return (
    <div className="absolute bottom-6 left-6 bg-gray-900/90 backdrop-blur-md rounded-xl px-5 py-3.5 z-10 border border-gray-700/50 shadow-xl">
      <div className="text-xs font-semibold text-gray-300 mb-2 tracking-wide">
        {isDrs ? "Displacement Risk Score" : "Environmental Benefit Score"}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-gray-500 font-medium">
          {isDrs ? "Low" : "Poor"}
        </span>
        <div
          className="h-2.5 w-40 rounded-full"
          style={{
            background: isDrs
              ? "linear-gradient(to right, #00c800, #ffff00, #ffa500, #ff0000, #8b0000)"
              : "linear-gradient(to right, #ff0000, #ffff00, #00c800)",
          }}
        />
        <span className="text-[10px] text-gray-500 font-medium">
          {isDrs ? "Critical" : "Good"}
        </span>
      </div>
      <div className="flex justify-between mt-1.5">
        <span className="text-[9px] text-gray-600">0</span>
        <span className="text-[9px] text-gray-600">25</span>
        <span className="text-[9px] text-gray-600">50</span>
        <span className="text-[9px] text-gray-600">75</span>
        <span className="text-[9px] text-gray-600">100</span>
      </div>
    </div>
  );
}
