"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const METHODOLOGIES = [
  { name: "SPIN", description: "Discovery-led — Situation, Problem, Implication, Need-Payoff questions." },
  { name: "Sandler", description: "Trust-first, no-pressure — pain funnel and mutual qualification." },
  { name: "Challenger", description: "Insight-led — teach, tailor, and take control of the conversation." },
];

type Message =
  | { id: string; role: "user"; kind: "text"; text: string }
  | { id: string; role: "assistant"; kind: "text"; text: string }
  | { id: string; role: "assistant"; kind: "status"; text: string }
  | { id: string; role: "assistant"; kind: "summary"; text: string }
  | { id: string; role: "assistant"; kind: "upload" }
  | { id: string; role: "assistant"; kind: "methodology" }
  | { id: string; role: "assistant"; kind: "script"; text: string; methodology: string };

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

// Plain `Omit<Message, "id">` does not distribute over the union — it
// collapses Message into a type that only has the fields common to every
// variant, which is why TS rejected object literals with `text` below.
// This distributive version preserves each variant's own shape.
type NewMessage = { [K in Message["kind"]]: Omit<Extract<Message, { kind: K }>, "id"> }[Message["kind"]];

export default function ChatResearchPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [prospectLabel, setProspectLabel] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const started = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const token = () =>
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const authHeaders = (extra: Record<string, string> = {}) => ({
    Authorization: `Bearer ${token()}`,
    ...extra,
  });

  const push = (msg: NewMessage) => {
    const withId = { ...msg, id: uid() } as Message;
    setMessages((prev) => [...prev, withId]);
    return withId.id;
  };

  const replaceStatus = (id: string, text: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id && m.kind === "status" ? { ...m, text } : m))
    );
  };

  const removeMessage = (id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!token()) {
      router.push("/login");
      return;
    }
    if (started.current) return;
    started.current = true;
    runResearchFlow();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runResearchFlow() {
    try {
      const sessionRes = await fetch(`${API_URL}/api/research/sessions/${sessionId}`, {
        headers: authHeaders(),
      });
      if (!sessionRes.ok) throw new Error("Couldn't load this research session.");
      const session = await sessionRes.json();

      push({ role: "user", kind: "text", text: session.prospect_input });

      // Resume support: if this session already went further than the
      // planning stage (e.g. the page was reloaded), skip straight to
      // wherever it left off instead of re-running research.
      if (session.generated_output) {
        setProspectLabel(labelFor(session));
        if (session.research_summary) {
          push({ role: "assistant", kind: "summary", text: session.research_summary });
        }
        push({
          role: "assistant",
          kind: "script",
          text: session.generated_output,
          methodology: session.methodology || "",
        });
        return;
      }

      const statusId = push({ role: "assistant", kind: "status", text: "Building a research plan…" });

      const planRes = await fetch(`${API_URL}/api/research/sessions/${sessionId}/plan`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!planRes.ok) {
        const errBody = await planRes.json().catch(() => ({}));
        throw new Error(errBody.detail || "Failed to generate research plan.");
      }

      // Re-fetch so we have the parsed prospect_name/company/title for the
      // header label and for the methodology-selection copy later.
      const refreshed = await fetch(`${API_URL}/api/research/sessions/${sessionId}`, {
        headers: authHeaders(),
      }).then((r) => r.json());
      setProspectLabel(labelFor(refreshed));

      replaceStatus(statusId, "Searching the public web and checking recent news…");

      const executeRes = await fetch(`${API_URL}/api/research/sessions/${sessionId}/execute`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!executeRes.ok) {
        const errBody = await executeRes.json().catch(() => ({}));
        throw new Error(errBody.detail || "Failed to execute research plan.");
      }

      replaceStatus(statusId, "Reading through what I found…");

      const summaryRes = await fetch(`${API_URL}/api/research/sessions/${sessionId}/summarize`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!summaryRes.ok) {
        const errBody = await summaryRes.json().catch(() => ({}));
        throw new Error(errBody.detail || "Research summarization failed.");
      }
      const { research_summary } = await summaryRes.json();

      removeMessage(statusId);
      push({ role: "assistant", kind: "summary", text: research_summary });

      push({
        role: "assistant",
        kind: "text",
        text: "Now — upload a document about your product (a one-pager, brochure, or spec sheet works). I'll use it to ground the pitch in what you actually offer.",
      });
      push({ role: "assistant", kind: "upload" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong during research.");
    }
  }

  function labelFor(session: any) {
    if (session.prospect_name) {
      return [session.prospect_name, session.prospect_title, session.prospect_company]
        .filter(Boolean)
        .join(" — ");
    }
    return session.prospect_input?.slice(0, 60) || "";
  }

  async function handleUpload(file: File) {
    const uploadMsgId = push({ role: "assistant", kind: "status", text: `Uploading ${file.name}…` });
    try {
      // Validate file type
      const validTypes = [".pdf", ".docx", ".txt", ".md"];
      const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
      if (!validTypes.includes(fileExt)) {
        throw new Error(`Invalid file type. Supported: PDF, DOCX, TXT, MD. Got: ${fileExt}`);
      }

      // Validate file size (10MB limit)
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        throw new Error(`File too large. Maximum size: 10MB. Got: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
      }

      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("material_type", "product_info");
      formData.append("name", file.name);
      formData.append("file", file);

      const res = await fetch(`${API_URL}/api/materials/upload`, {
        method: "POST",
        headers: authHeaders(),
        body: formData,
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || "Upload failed — try a PDF, DOCX, or TXT file.");
      }

      removeMessage(uploadMsgId);
      setUploadedFile(file.name);
      push({ role: "user", kind: "text", text: `Uploaded: ${file.name}` });
      push({ role: "assistant", kind: "text", text: "Got it. Which sales framework should I write the script in?" });
      push({ role: "assistant", kind: "methodology" });
    } catch (err) {
      removeMessage(uploadMsgId);
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  async function handleSkipUpload() {
    push({ role: "user", kind: "text", text: "Skip — no product document" });
    push({ role: "assistant", kind: "text", text: "No problem, I'll keep the value proposition generic. Which sales framework should I use?" });
    push({ role: "assistant", kind: "methodology" });
  }

  async function handleMethodology(methodology: string) {
    push({ role: "user", kind: "text", text: methodology });
    const statusId = push({ role: "assistant", kind: "status", text: `Writing your ${methodology} script…` });

    try {
      const res = await fetch(`${API_URL}/api/research/sessions/${sessionId}/generate-script`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ methodology, finding_ids: [] }),
        signal: AbortSignal.timeout(120000), // 2 minute timeout
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || "Script generation failed. Please try again.");
      }
      const { script } = await res.json();

      removeMessage(statusId);
      push({ role: "assistant", kind: "script", text: script, methodology });
    } catch (err) {
      removeMessage(statusId);
      if (err instanceof TypeError && err.message.includes("signal")) {
        setError("Script generation took too long. Please try again.");
      } else {
        setError(err instanceof Error ? err.message : "Script generation failed.");
      }
    }
  }

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <div className="sticky top-0 z-10 bg-black/90 backdrop-blur border-b border-maroon-800/50 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <div className="text-sm text-maroon-400">Researching</div>
            <div className="font-semibold text-maroon-200">{prospectLabel || "…"}</div>
          </div>
          <Link href="/" className="text-sm text-maroon-400 hover:text-maroon-300 underline underline-offset-2">
            New research
          </Link>
        </div>
      </div>

      <div className="flex-1 max-w-3xl w-full mx-auto px-4 py-8 space-y-4">
        {messages.map((m) => (
          <ChatBubble
            key={m.id}
            message={m}
            onUpload={handleUpload}
            onSkipUpload={handleSkipUpload}
            onMethodology={handleMethodology}
            uploadedFile={uploadedFile}
          />
        ))}

        {error && (
          <div className="p-4 rounded-xl bg-red-950 border border-red-800 text-red-200 text-sm animate-fadeIn">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function ChatBubble({
  message,
  onUpload,
  onSkipUpload,
  onMethodology,
  uploadedFile,
}: {
  message: Message;
  onUpload: (file: File) => void;
  onSkipUpload: () => void;
  onMethodology: (m: string) => void;
  uploadedFile: string | null;
}) {
  const isUser = message.role === "user";

  if (message.kind === "status") {
    return (
      <div className="flex justify-start animate-fadeIn">
        <div className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-maroon-950 border border-maroon-800 text-maroon-300 text-sm">
          <div className="h-4 w-4 border-2 border-maroon-500 border-t-transparent rounded-full animate-spin" />
          {message.text}
        </div>
      </div>
    );
  }

  if (message.kind === "upload") {
    return (
      <div className="flex justify-start animate-fadeIn">
        <div className="max-w-md w-full">
          <UploadWidget onUpload={onUpload} onSkip={onSkipUpload} uploadedFile={uploadedFile} />
        </div>
      </div>
    );
  }

  if (message.kind === "methodology") {
    return (
      <div className="flex justify-start animate-fadeIn">
        <div className="max-w-md w-full grid gap-2">
          {METHODOLOGIES.map((m) => (
            <button
              key={m.name}
              onClick={() => onMethodology(m.name)}
              className="text-left p-4 rounded-xl border-2 border-maroon-800 bg-maroon-950/50 hover:border-maroon-600 hover:bg-maroon-950 transition-all"
            >
              <div className="font-bold text-maroon-300">{m.name}</div>
              <div className="text-sm text-white/60">{m.description}</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (message.kind === "summary") {
    return (
      <div className="flex justify-start animate-fadeIn">
        <div className="max-w-lg w-full p-5 rounded-2xl bg-maroon-950 border border-maroon-700">
          <div className="text-xs font-semibold text-maroon-400 uppercase tracking-wide mb-2">
            Research Report
          </div>
          <div className="text-sm text-white/85 whitespace-pre-wrap leading-relaxed">{message.text}</div>
        </div>
      </div>
    );
  }

  if (message.kind === "script") {
    return (
      <div className="flex justify-start animate-fadeIn">
        <div className="max-w-lg w-full p-5 rounded-2xl bg-gradient-to-br from-maroon-950 to-maroon-900 border-2 border-maroon-600">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold text-maroon-300 uppercase tracking-wide">
              {message.methodology} Script
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => navigator.clipboard.writeText(message.text)}
                className="text-xs px-3 py-1 rounded-lg bg-maroon-800 hover:bg-maroon-700 text-white transition"
              >
                Copy
              </button>
              <button
                onClick={() => downloadText(message.text, "sales-script.txt")}
                className="text-xs px-3 py-1 rounded-lg bg-maroon-800 hover:bg-maroon-700 text-white transition"
              >
                Download
              </button>
            </div>
          </div>
          <div className="text-sm text-white/90 whitespace-pre-wrap leading-relaxed">{message.text}</div>
        </div>
      </div>
    );
  }

  // Plain text bubble (user or assistant)
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fadeIn`}>
      <div
        className={`max-w-md px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "bg-gradient-to-r from-maroon-900 to-maroon-700 text-white"
            : "bg-maroon-950 border border-maroon-800 text-white/85"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}

function UploadWidget({
  onUpload,
  onSkip,
  uploadedFile,
}: {
  onUpload: (file: File) => void;
  onSkip: () => void;
  uploadedFile: string | null;
}) {
  const [dragOver, setDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  if (uploadedFile) {
    return (
      <div className="p-4 rounded-xl bg-green-950/30 border border-green-700/50 text-green-300 text-sm animate-fadeIn">
        ✓ Successfully uploaded: {uploadedFile}
      </div>
    );
  }

  const handleFileSelect = async (file: File) => {
    setIsProcessing(true);
    onUpload(file);
    setIsProcessing(false);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!isProcessing) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file && !isProcessing) handleFileSelect(file);
      }}
      className={`p-6 rounded-2xl border-2 border-dashed text-center transition-all ${
        dragOver ? "border-maroon-500 bg-maroon-950" : "border-maroon-700 bg-maroon-950/50"
      } ${isProcessing ? "opacity-60" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt,.md"
        className="hidden"
        disabled={isProcessing}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFileSelect(file);
        }}
      />
      <p className="text-sm text-white/70 mb-3">{isProcessing ? "Processing…" : "Drag a file here, or"}</p>
      <div className="flex gap-3 justify-center">
        <button
          onClick={() => inputRef.current?.click()}
          disabled={isProcessing}
          className="px-4 py-2 rounded-lg bg-gradient-to-r from-maroon-900 to-maroon-700 text-white text-sm font-semibold hover:shadow-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Choose file
        </button>
        <button
          onClick={onSkip}
          disabled={isProcessing}
          className="px-4 py-2 rounded-lg bg-maroon-950 border border-maroon-700 text-maroon-300 text-sm font-semibold hover:border-maroon-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Skip
        </button>
      </div>
      <p className="text-xs text-white/40 mt-3">PDF, DOCX, TXT, or MD (max 10MB)</p>
    </div>
  );
}

function downloadText(text: string, filename: string) {
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
