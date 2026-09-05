export type Severity =
  | "informational"
  | "low"
  | "moderate"
  | "high"
  | "critical"
  | "neutral";

export const SEVERITY_ORDER: Severity[] = [
  "informational",
  "low",
  "moderate",
  "high",
  "critical",
];

export function normalizeSeverity(value?: string | null): Severity {
  const v = (value || "").toLowerCase();
  if ((SEVERITY_ORDER as string[]).includes(v)) return v as Severity;
  return "neutral";
}

export const SEVERITY_META: Record<
  Severity,
  { label: string; text: string; bg: string; ring: string; dot: string }
> = {
  informational: {
    label: "Informational",
    text: "text-sky-200",
    bg: "bg-sky-400/15",
    ring: "ring-sky-400/40",
    dot: "bg-sky-400",
  },
  low: {
    label: "Low",
    text: "text-emerald-200",
    bg: "bg-emerald-400/15",
    ring: "ring-emerald-400/40",
    dot: "bg-emerald-400",
  },
  moderate: {
    label: "Moderate",
    text: "text-amber-200",
    bg: "bg-amber-400/15",
    ring: "ring-amber-400/40",
    dot: "bg-amber-400",
  },
  high: {
    label: "High",
    text: "text-orange-200",
    bg: "bg-orange-400/15",
    ring: "ring-orange-400/40",
    dot: "bg-orange-400",
  },
  critical: {
    label: "Critical",
    text: "text-rose-200",
    bg: "bg-rose-400/15",
    ring: "ring-rose-400/40",
    dot: "bg-rose-400",
  },
  neutral: {
    label: "No policy cited",
    text: "text-slate-300",
    bg: "bg-slate-400/10",
    ring: "ring-slate-400/30",
    dot: "bg-slate-400",
  },
};

export function skyClass(severity: Severity): string {
  return `sky-${severity}`;
}
