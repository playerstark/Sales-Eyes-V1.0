"use client";

import { useState } from "react";
import clsx from "clsx";
import { ChevronDown, AlertCircle, ExternalLink } from "lucide-react";

interface Conflict {
  id: string;
  conflict_type: string;
  field_name: string;
  value_a: string;
  value_b: string;
  source_a_url: string;
  source_b_url: string;
  severity: "high" | "medium" | "low";
  resolution?: string;
}

interface ConflictPanelProps {
  conflicts: Conflict[];
}

export default function ConflictPanel({ conflicts }: ConflictPanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (!conflicts || conflicts.length === 0) {
    return null;
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-900/20 border-red-700";
      case "medium":
        return "bg-yellow-900/20 border-yellow-700";
      default:
        return "bg-blue-900/20 border-blue-700";
    }
  };

  const getSeverityBadgeColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-600 text-red-100";
      case "medium":
        return "bg-yellow-600 text-yellow-100";
      default:
        return "bg-blue-600 text-blue-100";
    }
  };

  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname.replace("www.", "");
    } catch {
      return "source";
    }
  };

  return (
    <div className="rounded-lg border border-maroon-800 bg-maroon-950/30 p-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between hover:opacity-80 transition"
      >
        <div className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-500" />
          <h3 className="text-base font-semibold text-maroon-300">
            {conflicts.length} {conflicts.length === 1 ? "Conflict" : "Conflicts"} Found
          </h3>
        </div>
        <ChevronDown
          className={clsx("w-5 h-5 transition-transform", expanded && "rotate-180")}
        />
      </button>

      {expanded && (
        <div className="mt-4 space-y-3">
          {conflicts.map((conflict) => (
            <div
              key={conflict.id}
              className={clsx("rounded-lg border p-3", getSeverityColor(conflict.severity))}
            >
              {/* Conflict Header */}
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h4 className="font-medium text-white">
                    {conflict.field_name}
                  </h4>
                  <p className="text-xs text-maroon-300 capitalize">
                    {conflict.conflict_type.replace(/_/g, " ")}
                  </p>
                </div>
                <span className={clsx("px-2 py-1 rounded text-xs font-semibold", getSeverityBadgeColor(conflict.severity))}>
                  {conflict.severity.toUpperCase()}
                </span>
              </div>

              {/* Values Comparison */}
              <div className="space-y-2">
                {/* Value A */}
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <p className="text-xs text-maroon-400 mb-1">Source A</p>
                    <p className="text-sm text-white bg-black/30 rounded px-2 py-1 break-words">
                      "{conflict.value_a}"
                    </p>
                    <a
                      href={conflict.source_a_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-maroon-400 hover:text-maroon-300 flex items-center gap-1 mt-1"
                    >
                      {getDomain(conflict.source_a_url)}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>

                {/* Value B */}
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <p className="text-xs text-maroon-400 mb-1">Source B</p>
                    <p className="text-sm text-white bg-black/30 rounded px-2 py-1 break-words">
                      "{conflict.value_b}"
                    </p>
                    <a
                      href={conflict.source_b_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-maroon-400 hover:text-maroon-300 flex items-center gap-1 mt-1"
                    >
                      {getDomain(conflict.source_b_url)}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>

              {conflict.resolution && (
                <div className="mt-2 pt-2 border-t border-maroon-700">
                  <p className="text-xs text-maroon-400">
                    <span className="font-semibold">Resolution:</span> {conflict.resolution}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
