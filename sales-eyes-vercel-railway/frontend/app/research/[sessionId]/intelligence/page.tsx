"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Loader, ChevronLeft, Zap } from "lucide-react";
import { api } from "@/lib/api";
import CandidateCard from "@/components/Intelligence/CandidateCard";

interface Candidate {
  id: string;
  canonical_full_name: string;
  canonical_company?: string;
  canonical_title?: string;
  verification_status: "pending" | "accept" | "reject" | "uncertain";
  confidence: number;
  conflict_count: number;
}

interface JobStatus {
  job_id: string;
  status: string;
  progress_percent: number;
  current_step?: string;
  message?: string;
  error?: string;
}

export default function IntelligencePage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;
  const jobIdParam = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "").get("job_id");

  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(!!jobIdParam);

  // Poll job status if research is running
  useEffect(() => {
    if (!jobIdParam || !polling) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await api.getIntelligenceJobStatus(jobIdParam);
        setJobStatus(status);

        if (status.status === "completed" || status.status === "failed") {
          setPolling(false);
          if (status.status === "completed") {
            // Refresh candidates
            fetchCandidates();
          }
        }
      } catch (err) {
        console.error("Error polling job status:", err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [jobIdParam, polling]);

  const fetchCandidates = async () => {
    try {
      setLoading(true);
      const data = await api.getIntelligenceCandidates(sessionId);
      setCandidates((data.candidates || []) as Candidate[]);
      setError(null);
    } catch (err) {
      console.error("Error fetching candidates:", err);
      setError("Failed to load candidates");
    } finally {
      setLoading(false);
    }
  };

  // Fetch candidates on mount
  useEffect(() => {
    if (!polling) {
      fetchCandidates();
    }
  }, [sessionId, polling]);

  const handleStartResearch = async () => {
    try {
      setLoading(true);
      const result = await api.startIntelligenceResearch(sessionId);
      const url = new URL(window.location.href);
      url.searchParams.set("job_id", result.job_id);
      router.push(url.toString());
    } catch (err) {
      console.error("Error starting research:", err);
      setError("Failed to start research");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-black text-white px-4 py-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/research/${sessionId}`}
            className="flex items-center gap-2 text-maroon-400 hover:text-maroon-300 mb-4"
          >
            <ChevronLeft className="w-4 h-4" />
            Back to Research
          </Link>

          <h1 className="text-4xl font-bold text-maroon-500 mb-2">Prospect Intelligence</h1>
          <p className="text-maroon-400">Research, verify, and approve prospect profiles</p>
        </div>

        {/* Job Progress Section */}
        {jobStatus && polling && (
          <div className="rounded-lg border-2 border-maroon-800 bg-maroon-950/50 p-6 mb-8">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <Loader className="w-5 h-5 text-maroon-500 animate-spin" />
                <div>
                  <h2 className="text-xl font-semibold text-white">Research in Progress</h2>
                  <p className="text-sm text-maroon-400">{jobStatus.current_step || "Initializing..."}</p>
                </div>
              </div>
              <span className="px-3 py-1 rounded-full bg-maroon-600 text-maroon-100 text-sm font-medium">
                {jobStatus.progress_percent}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-black/50 rounded-full h-2 overflow-hidden border border-maroon-700">
              <div
                className="bg-gradient-to-r from-maroon-600 to-maroon-500 h-full transition-all duration-500"
                style={{ width: `${jobStatus.progress_percent}%` }}
              />
            </div>

            {jobStatus.message && (
              <p className="text-xs text-maroon-400 mt-3">{jobStatus.message}</p>
            )}

            {jobStatus.error && (
              <div className="mt-3 p-3 rounded bg-red-900/30 border border-red-700">
                <p className="text-sm text-red-300">Error: {jobStatus.error}</p>
              </div>
            )}
          </div>
        )}

        {/* Start Research CTA */}
        {!polling && candidates.length === 0 && !error && (
          <div className="rounded-lg border-2 border-maroon-700 bg-maroon-950/30 p-8 text-center mb-8">
            <Zap className="w-12 h-12 text-maroon-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">No Research Yet</h2>
            <p className="text-maroon-400 mb-6">Start the intelligence research to find and verify prospects</p>
            <button
              onClick={handleStartResearch}
              disabled={loading}
              className="px-6 py-2 rounded-lg bg-maroon-600 hover:bg-maroon-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? "Starting..." : "Start Intelligence Research"}
            </button>
          </div>
        )}

        {/* Error Message */}
        {error && !polling && (
          <div className="rounded-lg border border-red-700 bg-red-900/20 p-4 mb-8">
            <p className="text-red-300">{error}</p>
            <button
              onClick={fetchCandidates}
              className="text-sm text-red-400 hover:text-red-300 mt-2 underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Candidates List */}
        {candidates.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white">
                Found {candidates.length} Candidate{candidates.length > 1 ? "s" : ""}
              </h2>
              {!polling && (
                <button
                  onClick={handleStartResearch}
                  disabled={loading}
                  className="px-4 py-2 rounded-lg border border-maroon-600 text-maroon-400 hover:bg-maroon-900/30 font-medium disabled:opacity-50 transition"
                >
                  {loading ? "Researching..." : "Research Again"}
                </button>
              )}
            </div>

            <div className="space-y-3">
              {candidates.map((candidate) => (
                <CandidateCard
                  key={candidate.id}
                  id={candidate.id}
                  sessionId={sessionId}
                  name={candidate.canonical_full_name}
                  company={candidate.canonical_company}
                  title={candidate.canonical_title}
                  confidence={candidate.confidence}
                  conflictCount={candidate.conflict_count}
                  verificationStatus={candidate.verification_status}
                />
              ))}
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && candidates.length === 0 && !jobStatus && (
          <div className="flex justify-center py-12">
            <Loader className="w-8 h-8 text-maroon-500 animate-spin" />
          </div>
        )}
      </div>
    </main>
  );
}
