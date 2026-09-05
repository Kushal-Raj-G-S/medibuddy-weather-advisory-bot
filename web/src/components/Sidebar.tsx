"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RefreshCcw, ScrollText, Sparkles, X } from "lucide-react";
import { fetchPolicy, PolicySummary } from "@/lib/api";
import { normalizeSeverity, SEVERITY_META } from "@/lib/severity";

interface Props {
  open: boolean;
  onClose: () => void;
  onNewSession: () => void;
  threadId: string;
}

function usePolicy() {
  const [policy, setPolicy] = useState<PolicySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPolicy()
      .then(setPolicy)
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false));
  }, []);

  return { policy, loading, error };
}

function SidebarContent({
  onNewSession,
  threadId,
}: {
  onNewSession: () => void;
  threadId: string;
}) {
  const { policy, loading, error } = usePolicy();

  return (
    <div className="flex h-full flex-col gap-6">
      <div className="flex items-center gap-2.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400/25 to-violet-400/25 ring-1 ring-white/10">
          <Sparkles size={14} className="text-sky-300" />
        </span>
        <h2 className="font-display text-sm font-semibold tracking-tight">
          Session
        </h2>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between rounded-xl bg-white/[0.03] px-3 py-2.5 ring-1 ring-white/[0.06]">
          <span className="text-[11px] text-[var(--text-faint)]">thread</span>
          <code className="text-[11px] text-sky-300">
            {threadId ? threadId.slice(0, 8) : "…"}
          </code>
        </div>
        <button
          onClick={onNewSession}
          className="group flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-sky-400/20 to-violet-400/20 px-3 py-2.5 text-xs font-medium text-sky-100 ring-1 ring-sky-400/25 transition hover:from-sky-400/30 hover:to-violet-400/30 hover:ring-sky-400/40"
        >
          <RefreshCcw
            size={13}
            className="transition-transform duration-500 group-hover:rotate-180"
          />
          New session
        </button>
      </div>

      <div className="hairline h-px border-t" />

      <div className="flex min-h-0 flex-1 flex-col gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-violet-400/25 to-fuchsia-400/25 ring-1 ring-white/10">
            <ScrollText size={14} className="text-violet-300" />
          </span>
          <h3 className="font-display text-sm font-semibold tracking-tight">
            Loaded policy
          </h3>
        </div>

        {loading && (
          <div className="space-y-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="shimmer h-11 rounded-xl" />
            ))}
          </div>
        )}

        {error && (
          <p className="rounded-xl bg-rose-400/10 p-3 text-xs text-rose-200 ring-1 ring-rose-400/25">
            {error}
          </p>
        )}

        {policy && (
          <>
            <p className="text-[11px] leading-relaxed text-[var(--text-faint)]">
              <span className="text-[var(--text-muted)]">{policy.count} SOPs</span>{" "}
              across {policy.categories.length} categories. Edit{" "}
              <code className="text-sky-300/90">sops/sops.yaml</code> — it
              reloads on the next question, no restart.
            </p>
            <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto pr-0.5">
              {policy.sops.map((s) => {
                const meta = SEVERITY_META[normalizeSeverity(s.severity)];
                return (
                  <div
                    key={s.id}
                    className={`rounded-xl px-3 py-2 ring-1 transition hover:brightness-110 ${meta.bg} ${meta.ring}`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${meta.dot}`} />
                      <span className={`text-[11px] font-medium ${meta.text}`}>
                        {s.id}
                      </span>
                      {s.override && (
                        <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[9px] tracking-wide text-[var(--text-muted)] uppercase">
                          override
                        </span>
                      )}
                      {s.judgment_based && (
                        <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[9px] tracking-wide text-[var(--text-muted)] uppercase">
                          fuzzy
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-[11px] text-[var(--text-primary)]/90">
                      {s.title}
                    </p>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function Sidebar({ open, onClose, onNewSession, threadId }: Props) {
  return (
    <>
      {/* Desktop: a permanent panel in normal flow, no transform tricks. */}
      <aside className="glass-strong sticky top-6 hidden h-[calc(100vh-3rem)] w-[300px] shrink-0 rounded-3xl p-5 lg:block">
        <SidebarContent onNewSession={onNewSession} threadId={threadId} />
      </aside>

      {/* Mobile: an overlay drawer, animated, dismissible. */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
              onClick={onClose}
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 32 }}
              className="glass-strong fixed inset-y-0 left-0 z-50 w-[300px] max-w-[85vw] overflow-y-auto rounded-r-3xl p-5 lg:hidden"
            >
              <button
                onClick={onClose}
                className="absolute top-4 right-4 rounded-lg p-1.5 text-[var(--text-muted)] hover:bg-white/10"
              >
                <X size={16} />
              </button>
              <SidebarContent onNewSession={onNewSession} threadId={threadId} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
