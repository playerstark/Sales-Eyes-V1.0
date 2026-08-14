"use client";

import { useState, useEffect } from "react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [deepseekKey, setDeepseekKey] = useState("");
  const [deepseekEndpoint, setDeepseekEndpoint] = useState("");
  const [newsapiEndpoint, setNewsapiEndpoint] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const stored = localStorage.getItem("settings");
      if (stored) {
        const settings = JSON.parse(stored);
        setDeepseekKey(settings.deepseekKey || "");
        setDeepseekEndpoint(settings.deepseekEndpoint || "");
        setNewsapiEndpoint(settings.newsapiEndpoint || "");
      }
    }
  }, [isOpen]);

  const handleSave = () => {
    const settings = {
      deepseekKey,
      deepseekEndpoint,
      newsapiEndpoint,
    };
    localStorage.setItem("settings", JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-maroon-950 border-2 border-maroon-700 rounded-2xl p-8 max-w-md w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-maroon-400">Settings</h2>
          <button
            onClick={onClose}
            className="text-maroon-400 hover:text-maroon-300 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        <div className="space-y-5">
          {/* DeepSeek API Key */}
          <div>
            <label className="block text-sm font-semibold text-maroon-300 mb-2">
              DeepSeek API Key
            </label>
            <input
              type="password"
              value={deepseekKey}
              onChange={(e) => setDeepseekKey(e.target.value)}
              placeholder="sk-..."
              className="w-full px-3 py-2 rounded-lg border-2 border-maroon-700 bg-maroon-900/50 text-white placeholder-white/40 focus:border-maroon-500 focus:ring-2 focus:ring-maroon-500/20 outline-none transition text-sm"
            />
            <p className="text-xs text-white/50 mt-1">
              Get your key from{" "}
              <a href="https://api.deepseek.com" target="_blank" rel="noopener noreferrer" className="text-maroon-400 hover:text-maroon-300">
                api.deepseek.com
              </a>
            </p>
          </div>

          {/* DeepSeek Endpoint */}
          <div>
            <label className="block text-sm font-semibold text-maroon-300 mb-2">
              DeepSeek Endpoint (optional)
            </label>
            <input
              type="text"
              value={deepseekEndpoint}
              onChange={(e) => setDeepseekEndpoint(e.target.value)}
              placeholder="https://api.deepseek.com/v1/chat/completions"
              className="w-full px-3 py-2 rounded-lg border-2 border-maroon-700 bg-maroon-900/50 text-white placeholder-white/40 focus:border-maroon-500 focus:ring-2 focus:ring-maroon-500/20 outline-none transition text-sm"
            />
          </div>

          {/* NewsAPI Endpoint */}
          <div>
            <label className="block text-sm font-semibold text-maroon-300 mb-2">
              NewsAPI Endpoint (optional)
            </label>
            <input
              type="text"
              value={newsapiEndpoint}
              onChange={(e) => setNewsapiEndpoint(e.target.value)}
              placeholder="https://newsapi.org/v2"
              className="w-full px-3 py-2 rounded-lg border-2 border-maroon-700 bg-maroon-900/50 text-white placeholder-white/40 focus:border-maroon-500 focus:ring-2 focus:ring-maroon-500/20 outline-none transition text-sm"
            />
          </div>

          {/* Status Message */}
          {saved && (
            <div className="p-3 rounded-lg bg-green-950 border border-green-800 text-green-200 text-sm">
              Settings saved successfully
            </div>
          )}

          {/* Save Button */}
          <button
            onClick={handleSave}
            className="w-full py-2 rounded-lg bg-gradient-to-r from-maroon-900 to-maroon-700 text-white font-semibold hover:shadow-lg transition mt-6"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}
