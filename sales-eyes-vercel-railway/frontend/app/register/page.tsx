"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.register(email, password, fullName);
      const { access_token } = await api.login(email, password);
      localStorage.setItem("access_token", access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-black px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl border-2 border-maroon-700 bg-maroon-950/50 p-8 shadow-xl animate-fade-in"
      >
        <h1 className="mb-6 text-2xl font-bold text-maroon-500">Create your account</h1>

        {error && (
          <div className="mb-4 rounded-lg bg-red-950 border border-red-800 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        )}

        <label className="mb-1 block text-sm font-medium text-maroon-300">Full name</label>
        <input
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="mb-4 w-full rounded-lg border-2 border-maroon-700 bg-maroon-900/50 px-3 py-2 text-sm text-white outline-none transition focus:border-maroon-500 focus:ring-2 focus:ring-maroon-500/20"
        />

        <label className="mb-1 block text-sm font-medium text-maroon-300">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 w-full rounded-lg border-2 border-maroon-700 bg-maroon-900/50 px-3 py-2 text-sm text-white outline-none transition focus:border-maroon-500 focus:ring-2 focus:ring-maroon-500/20"
        />

        <label className="mb-1 block text-sm font-medium text-maroon-300">Password</label>
        <input
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-6 w-full rounded-lg border-2 border-maroon-700 bg-maroon-900/50 px-3 py-2 text-sm text-white outline-none transition focus:border-maroon-500 focus:ring-2 focus:ring-maroon-500/20"
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-gradient-to-r from-maroon-900 to-maroon-700 py-2.5 text-sm font-semibold text-white transition hover:shadow-lg disabled:opacity-60"
        >
          {loading ? "Creating account..." : "Create account"}
        </button>

        <p className="mt-4 text-center text-sm text-white/60">
          Already have an account?{" "}
          <Link href="/login" className="text-maroon-400 hover:text-maroon-300 hover:underline">
            Log in
          </Link>
        </p>
      </form>
    </main>
  );
}
