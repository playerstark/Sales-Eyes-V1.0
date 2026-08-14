"use client";

import { useMemo } from "react";
import clsx from "clsx";

interface ConfidenceScoreProps {
  score: number; // 0.0 to 1.0
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  interactive?: boolean;
}

export default function ConfidenceScore({
  score,
  size = "md",
  showLabel = true,
  interactive = false,
}: ConfidenceScoreProps) {
  const percentage = Math.round(score * 100);

  // Determine color based on confidence level
  const getColor = (s: number) => {
    if (s >= 0.85) return "bg-green-600"; // High confidence
    if (s >= 0.70) return "bg-yellow-600"; // Medium confidence
    return "bg-red-600"; // Low confidence
  };

  const getTextColor = (s: number) => {
    if (s >= 0.85) return "text-green-400";
    if (s >= 0.70) return "text-yellow-400";
    return "text-red-400";
  };

  const getSizeclasses = () => {
    switch (size) {
      case "sm":
        return "text-xs px-2 py-1";
      case "lg":
        return "text-base px-3 py-2";
      default:
        return "text-sm px-2.5 py-1.5";
    }
  };

  const getLabel = (s: number) => {
    if (s >= 0.85) return "High";
    if (s >= 0.70) return "Medium";
    return "Low";
  };

  return (
    <div
      className={clsx(
        "inline-flex items-center gap-2 rounded-lg border",
        getColor(score),
        "border-opacity-30 bg-opacity-10",
        interactive && "cursor-help"
      )}
      title={`${percentage}% confidence`}
    >
      <div className={clsx("font-semibold", getTextColor(score), getSizeclasses())}>
        {percentage}%
      </div>
      {showLabel && (
        <span className={clsx("text-xs font-medium", getTextColor(score), "mr-1")}>
          {getLabel(score)}
        </span>
      )}
    </div>
  );
}
