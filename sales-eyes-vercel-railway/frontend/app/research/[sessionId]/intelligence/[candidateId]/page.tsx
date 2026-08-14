"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Save, Loader, Check, X } from "lucide-react";
import { api } from "@/lib/api";
import ConfidenceScore from "@/components/Intelligence/ConfidenceScore";
import EvidenceTimeline from "@/components/Intelligence/EvidenceTimeline";
import ConflictPanel from "@/components/Intelligence/ConflictPanel";

interface CandidateDetail {
  id: string;
  canonical_full_name: string;
  canonical_company?: string;
  canonical_title?: string;
  canonical_location?: string;
  merged_data: Record<string, any>;
  verification_status: string;
  confidence: number;
  score_details: any;
  evidence: Array<any>;
  conflicts: Array<any>;
  sources_count: number;
}

export default function CandidateReviewPage() {
  const router = useRouter();
  const params = useParams();
  const candidateId = params.candidateId as string;
  const sessionId = params.sessionId as string;

  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [expandScores, setExpandScores] = useState(false);

  const [decision, setDecision] = useState<"accept" | "reject" | "uncertain">("accept");
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [showCorrections, setShowCorrections] = useState(false);

  useEffect(() => {
    fetchCandidate();
  }, [candidateId]);

  const fetchCandidate = async () => {
    try {
      setLoading(true);
      const data = await api.getIntelligenceCandidateDetail(candidateId);
      setCandidate(data as CandidateDetail);
      setError(null);
    } catch (err) {
      console.error("Error fetching candidate:", err);
      setError("Failed to load candidate details");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    try {
      setVerifying(true);
      await api.verifyCandidateIdentity(candidateId, {
        decision,
        manual_corrections: corrections,
      });

      // Redirect back to candidate list
      router.push(`/research/${sessionId}/intelligence`);
    } catch (err) {
      console.error("Error verifying candidate:", err);
      setError("Failed to verify candidate");
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <Loader className="w-8 h-8 text-maroon-500 animate-spin" />
      </main>
    );
  }

  if (!candidate || error) {
    return (
      <main className="min-h-screen bg-black text-white px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <Link
            href={`/research/${sessionId}/intelligence`}
            className="flex items-center gap-2 text-maroon-400 hover:text-maroon-300 mb-8"
          >
            <ChevronLeft className="w-4 h-4" />
            Back to Candidates
          </Link>
          <div className="rounded-lg border border-red-700 bg-red-900/20 p-4">
            <p className="text-red-300">{error || "Candidate not found"}</p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-white px-4 py-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <Link
          href={`/research/${sessionId}/intelligence`}
          className="flex items-center gap-2 text-maroon-400 hover:text-maroon-300 mb-6"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Candidates
        </Link>

        {/* Candidate Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">
                {candidate.canonical_full_name}
              </h1>
              <p className="text-maroon-400">
                {candidate.canonical_title && candidate.canonical_company
                  ? `${candidate.canonical_title} at ${candidate.canonical_company}`
                  : candidate.canonical_company ||
                    candidate.canonical_title ||
                    "Unknown role"}
              </p>
              {candidate.canonical_location && (
                <p className="text-sm text-maroon-400">📍 {candidate.canonical_location}</p>
              )}
            </div>

            <div className="text-right">
              <ConfidenceScore score={candidate.confidence} size="lg" />
              <p className="text-xs text-maroon-400 mt-2">{candidate.sources_count} sources</p>
            </div>
          </div>
        </div>

        {/* Two-Column Layout */}
        <div className="grid grid-cols-3 gap-6 mb-8">
          {/* Left Column: Evidence & Conflicts */}
          <div className="col-span-2 space-y-6">
            {/* Evidence Section */}
            <div className="rounded-lg border border-maroon-800 bg-maroon-950/30 p-6">
              <EvidenceTimeline evidence={candidate.evidence} />
            </div>

            {/* Conflicts Section */}
            {candidate.conflicts && candidate.conflicts.length > 0 && (
              <div className="rounded-lg border border-maroon-800 bg-maroon-950/30 p-6">
                <ConflictPanel conflicts={candidate.conflicts} />
              </div>
            )}
          </div>

          {/* Right Column: Scores & Verification */}
          <div className="col-span-1 space-y-6">
            {/* Score Breakdown */}
            <div className="rounded-lg border border-maroon-800 bg-maroon-950/30 p-6">
              <button
                onClick={() => setExpandScores(!expandScores)}
                className="w-full text-left mb-3 hover:opacity-80 transition"
              >
                <h3 className="font-semibold text-white">Score Breakdown</h3>
                <p className="text-xs text-maroon-400">Component details</p>
              </button>

              {expandScores && candidate.score_details.component_scores && (
                <div className="space-y-2 mt-3 pt-3 border-t border-maroon-700">
                  {Object.entries(
                    candidate.score_details.component_scores as Record<string, number>
                  ).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-xs text-maroon-400 capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm font-semibold text-white">
                        {Math.round((value as number) * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Verification Gate */}
            <div className="rounded-lg border border-maroon-800 bg-maroon-950/30 p-6">
              <h3 className="font-semibold text-white mb-4">Verification Decision</h3>

              {/* Decision Buttons */}
              <div className="space-y-2 mb-6">
                <button
                  onClick={() => setDecision("accept")}
                  className={`w-full px-4 py-2 rounded-lg border-2 font-medium transition flex items-center justify-center gap-2 ${
                    decision === "accept"
                      ? "border-green-600 bg-green-600/20 text-green-300"
                      : "border-maroon-700 bg-maroon-900/20 text-maroon-300 hover:border-green-700"
                  }`}
                >
                  <Check className="w-4 h-4" />
                  Accept
                </button>

                <button
                  onClick={() => setDecision("reject")}
                  className={`w-full px-4 py-2 rounded-lg border-2 font-medium transition flex items-center justify-center gap-2 ${
                    decision === "reject"
                      ? "border-red-600 bg-red-600/20 text-red-300"
                      : "border-maroon-700 bg-maroon-900/20 text-maroon-300 hover:border-red-700"
                  }`}
                >
                  <X className="w-4 h-4" />
                  Reject
                </button>

                <button
                  onClick={() => setDecision("uncertain")}
                  className={`w-full px-4 py-2 rounded-lg border-2 font-medium transition ${
                    decision === "uncertain"
                      ? "border-yellow-600 bg-yellow-600/20 text-yellow-300"
                      : "border-maroon-700 bg-maroon-900/20 text-maroon-300 hover:border-yellow-700"
                  }`}
                >
                  Uncertain
                </button>
              </div>

              {/* Corrections Toggle */}
              {decision === "accept" && (
                <div className="border-t border-maroon-700 pt-4">
                  <button
                    onClick={() => setShowCorrections(!showCorrections)}
                    className="text-sm text-maroon-400 hover:text-maroon-300 underline"
                  >
                    {showCorrections ? "Hide corrections" : "Add corrections"}
                  </button>

                  {showCorrections && (
                    <div className="space-y-3 mt-4">
                      <div>
                        <label className="text-xs text-maroon-400 block mb-1">Email</label>
                        <input
                          type="email"
                          placeholder={candidate.merged_data.email || "john@example.com"}
                          value={corrections.email || ""}
                          onChange={(e) =>
                            setCorrections({ ...corrections, email: e.target.value })
                          }
                          className="w-full bg-black/50 border border-maroon-700 rounded px-2 py-1 text-sm text-white"
                        />
                      </div>

                      <div>
                        <label className="text-xs text-maroon-400 block mb-1">Phone</label>
                        <input
                          type="tel"
                          placeholder={candidate.merged_data.phone || "+1-555-0100"}
                          value={corrections.phone || ""}
                          onChange={(e) =>
                            setCorrections({ ...corrections, phone: e.target.value })
                          }
                          className="w-full bg-black/50 border border-maroon-700 rounded px-2 py-1 text-sm text-white"
                        />
                      </div>

                      <div>
                        <label className="text-xs text-maroon-400 block mb-1">Title</label>
                        <input
                          type="text"
                          placeholder={candidate.canonical_title || "VP Sales"}
                          value={corrections.title || ""}
                          onChange={(e) =>
                            setCorrections({ ...corrections, title: e.target.value })
                          }
                          className="w-full bg-black/50 border border-maroon-700 rounded px-2 py-1 text-sm text-white"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Submit Button */}
              <button
                onClick={handleVerify}
                disabled={verifying}
                className="w-full mt-6 px-4 py-2 rounded-lg bg-maroon-600 hover:bg-maroon-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
              >
                {verifying ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Submit Decision
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
