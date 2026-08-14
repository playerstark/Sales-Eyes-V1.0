"use client";

import Link from "next/link";
import { ChevronRight, AlertCircle } from "lucide-react";
import ConfidenceScore from "./ConfidenceScore";

interface CandidateCardProps {
  id: string;
  sessionId: string;
  name: string;
  company?: string;
  title?: string;
  confidence: number;
  conflictCount: number;
  verificationStatus: "pending" | "accept" | "reject" | "uncertain";
}

export default function CandidateCard({
  id,
  sessionId,
  name,
  company,
  title,
  confidence,
  conflictCount,
  verificationStatus,
}: CandidateCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "accept":
        return "bg-green-600/20 border-green-700";
      case "reject":
        return "bg-red-600/20 border-red-700";
      case "uncertain":
        return "bg-yellow-600/20 border-yellow-700";
      default:
        return "bg-maroon-600/20 border-maroon-700";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "accept":
        return "Verified";
      case "reject":
        return "Rejected";
      case "uncertain":
        return "Uncertain";
      default:
        return "Pending";
    }
  };

  return (
    <Link href={`/research/${sessionId}/intelligence/${id}`}>
      <div className={`rounded-lg border p-4 hover:border-maroon-600 hover:bg-maroon-900/20 transition cursor-pointer ${getStatusColor(verificationStatus)}`}>
        {/* Header with name and status */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white mb-1">{name}</h3>
            <p className="text-sm text-maroon-400">
              {title && company ? `${title} at ${company}` : company || title || "Unknown role"}
            </p>
          </div>
          <span className="px-2 py-1 rounded text-xs font-medium text-maroon-200 bg-maroon-800/50 whitespace-nowrap ml-2">
            {getStatusLabel(verificationStatus)}
          </span>
        </div>

        {/* Metrics row */}
        <div className="flex items-center justify-between pt-3 border-t border-maroon-800/30">
          <ConfidenceScore score={confidence} size="sm" showLabel />

          {conflictCount > 0 && (
            <div className="flex items-center gap-1 text-yellow-500">
              <AlertCircle className="w-4 h-4" />
              <span className="text-xs font-medium">{conflictCount} conflict{conflictCount > 1 ? "s" : ""}</span>
            </div>
          )}

          <ChevronRight className="w-5 h-5 text-maroon-500 flex-shrink-0" />
        </div>
      </div>
    </Link>
  );
}
