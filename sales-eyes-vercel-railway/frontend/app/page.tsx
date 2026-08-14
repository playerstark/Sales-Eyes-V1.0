"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [prospectInput, setProspectInput] = useState("");
  const [isAuthed, setIsAuthed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsAuthed(!!localStorage.getItem("access_token"));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthed) {
      router.push("/login");
      return;
    }

    if (!prospectInput.trim()) return;

    setIsLoading(true);
    try {
      const session = await api.createSession(prospectInput);
      router.push(`/research/${session.id}`);
    } catch (err) {
      console.error("Error:", err);
      alert("Failed to start research. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-20">
      <div className="w-full max-w-2xl">
        <div className="mb-12 text-center">
          <h1 className="text-5xl font-bold text-maroon-500 mb-3">Sales Eyes</h1>
          <p className="text-xl text-maroon-400">
            AI-powered prospect research &amp; script generation
          </p>
        </div>

        {isAuthed ? (
          <>
            <form
              onSubmit={handleSubmit}
              className="rounded-2xl border-2 border-maroon-700 bg-maroon-950/50 p-8 shadow-xl mb-8"
            >
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-maroon-300 mb-2">
                  Who are you researching?
                </h2>
                <p className="text-maroon-400">
                  Name, role, and company is enough — e.g. "Sundar Pichai, CEO, Google."
                </p>
              </div>

              <textarea
                required
                placeholder="Sundar Pichai, CEO, Google"
                value={prospectInput}
                onChange={(e) => setProspectInput(e.target.value)}
                className="mb-6 w-full h-32 rounded-xl border-2 border-maroon-700 bg-maroon-900/50 px-4 py-3 text-white placeholder-white/40 outline-none focus:border-maroon-500 focus:ring-2 focus:ring-maroon-500/20 resize-none transition-all"
              />

              <button
                type="submit"
                disabled={isLoading || !prospectInput.trim()}
                className="w-full rounded-xl bg-gradient-to-r from-maroon-900 to-maroon-700 py-3 text-base font-semibold text-white transition hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed active:scale-98"
              >
                {isLoading ? "Starting…" : "Start"}
              </button>
            </form>

            <div className="text-center">
              <Link
                href="/dashboard"
                className="text-maroon-400 hover:text-maroon-300 underline underline-offset-2 text-sm"
              >
                View dashboard
              </Link>
            </div>
          </>
        ) : (
          <>
            <div className="rounded-2xl border-2 border-maroon-700 bg-maroon-950/50 p-8 shadow-xl mb-8 text-center">
              <h2 className="text-2xl font-bold text-maroon-300 mb-4">
                Get started
              </h2>
              <p className="text-maroon-400 mb-6">
                Sign up or log in to begin researching prospects
              </p>
              
              <div className="space-y-3">
                <Link
                  href="/register"
                  className="block px-6 py-3 rounded-xl bg-gradient-to-r from-maroon-900 to-maroon-700 text-white font-semibold hover:shadow-lg transition"
                >
                  Create Account
                </Link>
                <Link
                  href="/login"
                  className="block px-6 py-3 rounded-xl bg-maroon-950 border-2 border-maroon-700 text-maroon-300 font-semibold hover:border-maroon-600 hover:bg-maroon-900 transition"
                >
                  Sign In
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
