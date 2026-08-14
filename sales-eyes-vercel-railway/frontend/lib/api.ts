const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiError {
  detail: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }

  return res.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string, full_name?: string) =>
    request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request("/api/auth/me"),

  // Research endpoints
  createSession: (prospectInput: string) =>
    request<{ id: string }>("/api/research/sessions", {
      method: "POST",
      body: JSON.stringify({ prospect_input: prospectInput }),
    }),

  getSession: (sessionId: string) =>
    request(`/api/research/sessions/${sessionId}`),

  generatePlan: (sessionId: string) =>
    request(`/api/research/sessions/${sessionId}/plan`, {
      method: "POST",
    }),

  getFindings: (sessionId: string) =>
    request(`/api/research/sessions/${sessionId}/findings`),

  selectFindings: (sessionId: string, findingIds: string[]) =>
    request(`/api/research/sessions/${sessionId}/findings/select`, {
      method: "POST",
      body: JSON.stringify({ finding_ids: findingIds }),
    }),

  generateScript: (sessionId: string, methodology: string, findingIds: string[]) =>
    request(`/api/research/sessions/${sessionId}/generate-script`, {
      method: "POST",
      body: JSON.stringify({ methodology, finding_ids: findingIds }),
    }),

  getSettings: () =>
    request("/api/research/settings"),

  updateSettings: (settings: Record<string, any>) =>
    request("/api/research/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),

  // Materials endpoints
  uploadMaterial: async (
    sessionId: string,
    file: File,
    materialType: string,
    name: string,
    description?: string
  ) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("material_type", materialType);
    formData.append("name", name);
    formData.append("session_id", sessionId);
    if (description) formData.append("description", description);

    const res = await fetch(`${API_URL}/api/materials/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }

    return res.json();
  },

  getMaterials: (sessionId: string) =>
    request(`/api/materials/session/${sessionId}`),

  deleteMaterial: (materialId: string) =>
    request(`/api/materials/${materialId}`, {
      method: "DELETE",
    }),

  analyzeMaterials: (sessionId: string) =>
    request(`/api/research/sessions/${sessionId}/analyze-materials`, {
      method: "POST",
    }),

  generatePainPoints: (sessionId: string) =>
    request(`/api/research/sessions/${sessionId}/generate-pain-points`, {
      method: "POST",
    }),

  // Intelligence endpoints
  createIntelligenceSession: (prospectName: string, prospectCompany?: string) =>
    request("/api/intelligence/sessions", {
      method: "POST",
      body: JSON.stringify({ prospect_name: prospectName, prospect_company: prospectCompany }),
    }),

  startIntelligenceResearch: (sessionId: string) =>
    request<{ session_id: string; job_id: string; status: string }>(`/api/intelligence/sessions/${sessionId}/research`, {
      method: "POST",
    }),

  getIntelligenceJobStatus: (jobId: string) =>
    request<{ job_id: string; status: string; progress_percent: number; current_step?: string; message?: string; error?: string }>(`/api/intelligence/jobs/${jobId}/status`, {
      method: "GET",
    }),

  getIntelligenceCandidates: (sessionId: string) =>
    request<{
      session_id: string;
      total_candidates: number;
      candidates: Array<{
        id: string;
        canonical_full_name: string;
        canonical_company?: string;
        canonical_title?: string;
        verification_status: string;
        confidence: number;
        conflict_count: number;
      }>;
    }>(`/api/intelligence/sessions/${sessionId}/candidates`, {
      method: "GET",
    }),

  getIntelligenceCandidateDetail: (candidateId: string) =>
    request(`/api/intelligence/candidates/${candidateId}`, {
      method: "GET",
    }),

  verifyCandidateIdentity: (candidateId: string, payload: { decision: string; manual_corrections?: Record<string, string> }) =>
    request(`/api/intelligence/candidates/${candidateId}/verify`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getIntelligenceVerifiedProfile: (sessionId: string) =>
    request(`/api/intelligence/sessions/${sessionId}/verified-profile`, {
      method: "GET",
    }),

  deleteIntelligenceSession: (sessionId: string) =>
    request(`/api/intelligence/sessions/${sessionId}`, {
      method: "DELETE",
    }),
};
