"use client";

import { useState } from "react";
import clsx from "clsx";
import { ChevronDown, ExternalLink } from "lucide-react";
import ConfidenceScore from "./ConfidenceScore";

interface Evidence {
  id: string;
  fact_type: string;
  fact_value: string;
  source_url: string;
  source_snippet?: string;
  confidence: number;
}

interface EvidenceTimelineProps {
  evidence: Evidence[];
}

export default function EvidenceTimeline({ evidence }: EvidenceTimelineProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!evidence || evidence.length === 0) {
    return (
      <div className="rounded-lg border border-maroon-800 bg-maroon-950/20 p-4 text-center">
        <p className="text-maroon-400">No evidence available</p>
      </div>
    );
  }

  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname.replace("www.", "");
    } catch {
      return "source";
    }
  };

  const getFactLabel = (type: string) => {
    return type
      .replace(/_/g, " ")
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-maroon-300">Evidence Trail ({evidence.length})</h3>

      <div className="space-y-2">
        {evidence.map((item, index) => (
          <div
            key={item.id}
            className="rounded-lg border border-maroon-800 bg-maroon-950/30 overflow-hidden"
          >
            {/* Evidence Header */}
            <button
              onClick={() =>
                setExpandedId(expandedId === item.id ? null : item.id)
              }
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-maroon-900/30 transition"
            >
              <div className="flex items-center gap-3 flex-1 text-left">
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">
                    {getFactLabel(item.fact_type)}
                  </p>
                  <p className="text-xs text-maroon-400 truncate">
                    "{item.fact_value}"
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <ConfidenceScore score={item.confidence} size="sm" showLabel={false} />
                <ChevronDown
                  className={clsx(
                    "w-4 h-4 text-maroon-400 transition-transform flex-shrink-0",
                    expandedId === item.id && "rotate-180"
                  )}
                />
              </div>
            </button>

            {/* Evidence Details */}
            {expandedId === item.id && (
              <div className="px-4 py-3 bg-black/20 border-t border-maroon-800 space-y-2">
                <div>
                  <p className="text-xs text-maroon-400 mb-1">Source</p>
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-maroon-300 hover:text-maroon-200 flex items-center gap-2 break-all"
                  >
                    {getDomain(item.source_url)}
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  </a>
                </div>

                {item.source_snippet && (
                  <div>
                    <p className="text-xs text-maroon-400 mb-1">Context</p>
                    <p className="text-sm text-maroon-100 bg-black/30 rounded p-2 italic">
                      "{item.source_snippet}"
                    </p>
                  </div>
                )}

                <div className="flex items-center gap-2 pt-1">
                  <p className="text-xs text-maroon-400">Confidence:</p>
                  <ConfidenceScore score={item.confidence} size="sm" showLabel />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
