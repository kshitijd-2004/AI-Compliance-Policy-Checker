import { format } from "date-fns";

export type PolicyType =
  | "confidentiality"
  | "external_communication"
  | "data_privacy"
  | "security"
  | "hr";

export interface PolicyDocument {
  id: number;
  title: string;
  file_path: string;
  policy_type: PolicyType;
  department?: string;
  version?: string;
  created_at: string;
}

export interface ComplianceIssue {
  type: string;
  policy_reference?: string;
  excerpt?: string;
  explanation: string;
}

export interface ComplianceCheckResponse {
  overall_risk: "NONE" | "LOW" | "MEDIUM" | "HIGH";
  issues: ComplianceIssue[];
  suggested_text?: string | null;
}

export interface ComplianceCheckLog {
  id: number;
  created_at: string;
  text: string;
  department?: string;
  policy_type?: PolicyType;
  overall_risk: "NONE" | "LOW" | "MEDIUM" | "HIGH";
  issues?: ComplianceIssue[];
  suggested_text?: string | null;
}

/* ---------- Base config ---------- */

// Use Vite environment variable if set, otherwise default to localhost
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

/**
 * Helper for JSON requests to the FastAPI backend.
 */
async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    // Let caller override headers if needed (e.g., FormData)
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Request failed: ${res.status} ${res.statusText} ${text || ""}`.trim()
    );
  }

  // Some endpoints might return no content
  if (res.status === 204) return undefined as unknown as T;

  return (await res.json()) as T;
}

/* ---------- API surface used by your React app ---------- */

export const api = {
  /** Run a compliance check on a piece of text. */
  checkCompliance: async (
    text: string,
    department?: string,
    policy_type?: string
  ): Promise<ComplianceCheckResponse> => {
    return request<ComplianceCheckResponse>("/compliance/check", {
      method: "POST",
      body: JSON.stringify({
        text,
        department: department || null,
        policy_type: policy_type || null,
      }),
    });
  },

  /** Get compliance logs (optionally filtered by department and/or risk). */
  getLogs: async (
    department?: string,
    risk?: "NONE" | "LOW" | "MEDIUM" | "HIGH"
  ): Promise<ComplianceCheckLog[]> => {
    const params = new URLSearchParams();
    if (department) params.set("department", department);
    if (risk) params.set("risk", risk);

    const query = params.toString();
    const path = `/compliance/logs${query ? `?${query}` : ""}`;

    return request<ComplianceCheckLog[]>(path);
  },

  /** Get a single log by ID (if you ever need detail view). */
  getLogById: async (id: number): Promise<ComplianceCheckLog> => {
    return request<ComplianceCheckLog>(`/compliance/logs/${id}`);
  },

  /** List all policy documents. */
  getPolicies: async (): Promise<PolicyDocument[]> => {
    return request<PolicyDocument[]>("/policies/");
  },

  /**
   * Upload a new policy document (multipart form data).
   * Expects FastAPI handler like:
   *   file: UploadFile = File(...)
   *   title: str = Form(...)
   *   policy_type: PolicyType = Form(...)
   *   department: str | None = Form(None)
   */
  uploadPolicy: async (
    file: File,
    title: string,
    type: PolicyType,
    department?: string
  ): Promise<PolicyDocument> => {
    const form = new FormData();
    form.append("file", file);
    form.append("title", title);
    form.append("policy_type", type);
    if (department) form.append("department", department);

    return request<PolicyDocument>("/policies/", {
      method: "POST",
      body: form,
      // Important: DO NOT manually set Content-Type here; browser will set boundary
    });
  },

  /** Backend health check */
  health: async (): Promise<{
    status: string;
    db_ok?: boolean;
    pinecone_ok?: boolean;
  }> => {
    return request("/health");
  },
};
