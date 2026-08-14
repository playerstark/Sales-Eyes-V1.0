"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface Me {
  email: string;
  full_name: string | null;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<Me | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Unauthorized");
        return res.json();
      })
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("access_token");
        router.push("/login");
      });
  }, [router]);

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-black">
        <p className="text-maroon-500">Loading...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-white px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-4xl font-bold text-maroon-500 mb-2">
          Welcome{user.full_name ? `, ${user.full_name}` : ""} 👋
        </h1>
        <p className="text-maroon-400 mb-8">{user.email}</p>

        <div className="grid gap-6 md:grid-cols-2">
          <Link
            href="/"
            className="group p-8 rounded-2xl border-2 border-maroon-800 bg-maroon-950/50 hover:border-maroon-600 hover:bg-maroon-950 transition-all"
          >
            <div className="text-maroon-500 text-3xl mb-3">🔍</div>
            <h2 className="text-xl font-bold text-maroon-300 mb-2">Start New Research</h2>
            <p className="text-white/60">Begin a new prospect research session</p>
          </Link>

          <div className="p-8 rounded-2xl border-2 border-maroon-800/50 bg-maroon-950/30">
            <div className="text-maroon-500 text-3xl mb-3">📊</div>
            <h2 className="text-xl font-bold text-maroon-300 mb-2">Recent Sessions</h2>
            <p className="text-white/60">Check back soon for your session history</p>
          </div>
        </div>
      </div>
    </main>
  );
}
