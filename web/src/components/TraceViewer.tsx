"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, GitBranch } from "lucide-react";
import { TraceEntry } from "@/lib/api";

const NODE_LABEL: Record<string, string> = {
  interpret: "Interpreted the question",
  fetch: "Fetched live weather",
  match: "Matched against policy",
  compose: "Composed a draft reply",
  verify: "Verified the draft",
  ask_location: "Asked for a location",
  report_unavailable: "Reported weather unavailable",
  report_no_guidance: "Reported no policy applies",
  refuse_override: "Refused an override attempt",
  report_verification_failure: "Refused an ungrounded draft",
};

export default function TraceViewer({ trace }: { trace: TraceEntry[] }) {
  const [open, setOpen] = useState(false);
  if (!trace?.length) return null;

  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
      >
        <GitBranch size={12} />
        Decision trace ({trace.length} steps)
        <ChevronDown
          size={12}
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <ol className="glass mt-2 space-y-2 rounded-xl p-3">
              {trace.map((entry, i) => (
                <li key={i} className="flex gap-2 text-[11px]">
                  <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-sky-400/20 text-[9px] text-sky-200 ring-1 ring-sky-400/30">
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-[var(--text-primary)]">
                      {NODE_LABEL[entry.node as string] || (entry.node as string)}
                    </p>
                    <pre className="mt-0.5 overflow-x-auto text-[10px] leading-relaxed text-[var(--text-muted)]">
                      {JSON.stringify(
                        Object.fromEntries(
                          Object.entries(entry).filter(([k]) => k !== "node")
                        ),
                        null,
                        0
                      )}
                    </pre>
                  </div>
                </li>
              ))}
            </ol>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
