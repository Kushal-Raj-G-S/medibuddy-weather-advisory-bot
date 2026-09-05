"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ShieldCheck, ShieldOff, Tag } from "lucide-react";
import { Citation } from "@/lib/api";
import { normalizeSeverity, SEVERITY_META } from "@/lib/severity";

export default function CitationCard({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false);
  const severity = normalizeSeverity(citation.severity);
  const meta = SEVERITY_META[severity];
  const cited = Object.entries(citation.cited_values || {});

  return (
    <div className="mt-2 w-full max-w-full">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs ring-1 transition-colors ${meta.bg} ${meta.ring} hover:brightness-125`}
      >
        {citation.sop_id ? (
          <ShieldCheck size={14} className={meta.text} />
        ) : (
          <ShieldOff size={14} className={meta.text} />
        )}
        <span className={`font-medium ${meta.text}`}>
          {citation.sop_id ? `${citation.sop_id} · ${meta.label}` : meta.label}
        </span>
        <span className="truncate text-[var(--text-muted)]">
          {citation.sop_title || citation.reason || "no source"}
        </span>
        <ChevronDown
          size={14}
          className={`ml-auto shrink-0 text-[var(--text-muted)] transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="glass mt-2 space-y-3 rounded-xl p-4 text-xs">
              {citation.sop_id ? (
                <>
                  <div className="grid grid-cols-2 gap-3 text-[var(--text-muted)] sm:grid-cols-3">
                    <Field label="Policy id" value={citation.sop_id} />
                    <Field label="Category" value={citation.category} />
                    <Field label="Location" value={citation.location} />
                    <Field label="Basis" value={citation.basis} />
                    <Field
                      label="Fetched at"
                      value={
                        citation.fetched_at
                          ? new Date(citation.fetched_at).toLocaleTimeString()
                          : undefined
                      }
                    />
                  </div>

                  {cited.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-[var(--text-muted)]">
                        Values quoted from the live API
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {cited.map(([k, v]) => (
                          <span
                            key={k}
                            className="rounded-full bg-white/8 px-2.5 py-1 ring-1 ring-white/10"
                          >
                            <span className="text-[var(--text-muted)]">
                              {k}
                            </span>
                            <span className="ml-1.5 font-medium text-[var(--text-primary)]">
                              {v}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {citation.co_applying && citation.co_applying.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-[var(--text-muted)]">
                        Also matched, disclosed but not led with
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {citation.co_applying.map((c) => {
                          const m = SEVERITY_META[normalizeSeverity(c.severity)];
                          return (
                            <span
                              key={c.id}
                              className={`flex items-center gap-1 rounded-full px-2.5 py-1 ring-1 ${m.bg} ${m.ring}`}
                            >
                              <Tag size={10} className={m.text} />
                              <span className={m.text}>{c.id}</span>
                              <span className="text-[var(--text-muted)]">
                                {c.title}
                              </span>
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-[var(--text-muted)]">
                  {citation.reason === "no_sop_applies" &&
                    "No written policy covers this question, so no citation is shown by design."}
                  {citation.reason === "weather_unavailable" &&
                    `Weather data could not be retrieved: ${
                      citation.detail || "unknown error"
                    }.`}
                  {citation.reason === "location_missing" &&
                    "No location was resolved for this question yet."}
                  {citation.reason === "instruction_override_refused" &&
                    "This message tried to override policy; the request was refused rather than answered off-policy."}
                  {citation.reason === "failed_output_validation" &&
                    "The composed draft failed an internal grounding check and was discarded before reaching you."}
                  {!citation.reason && "No policy was cited for this reply."}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-[var(--text-primary)]">{value}</p>
    </div>
  );
}
