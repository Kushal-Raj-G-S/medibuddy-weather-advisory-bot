export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Citation {
  sop_id: string | null;
  sop_title?: string;
  severity?: string;
  category?: string;
  reason?: string;
  detail?: string;
  co_applying?: { id: string; title: string; severity: string }[];
  location?: string;
  basis?: string;
  fetched_at?: string;
  cited_values?: Record<string, string>;
}

export interface TraceEntry {
  node: string;
  [key: string]: unknown;
}

export interface AskResult {
  answer: string;
  citation: Citation;
  interpretation: Record<string, unknown>;
  trace: TraceEntry[];
}

export interface PolicySummary {
  count: number;
  categories: string[];
  sops: {
    id: string;
    title: string;
    category: string;
    severity: string;
    override: boolean;
    judgment_based: boolean;
  }[];
}

export async function askQuestion(
  question: string,
  threadId: string
): Promise<AskResult> {
  const response = await fetch(`${API_BASE}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, thread_id: threadId }),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status}: ${body}`);
  }
  return response.json();
}

export async function fetchPolicy(): Promise<PolicySummary> {
  const response = await fetch(`${API_BASE}/api/policy`);
  if (!response.ok) throw new Error(`API error ${response.status}`);
  return response.json();
}
