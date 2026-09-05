"use client";

import { motion } from "framer-motion";
import { CloudLightning, Menu, ShieldCheck } from "lucide-react";

export default function Header({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="glass-strong flex items-center justify-between rounded-3xl px-5 py-4">
      <div className="flex items-center gap-3.5">
        <button
          onClick={onMenu}
          className="rounded-xl p-2 text-[var(--text-muted)] transition hover:bg-white/8 hover:text-[var(--text-primary)] lg:hidden"
        >
          <Menu size={18} />
        </button>

        <motion.div
          initial={{ rotate: -10, scale: 0.85, opacity: 0 }}
          animate={{ rotate: 0, scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 16 }}
          className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400/25 via-indigo-400/20 to-violet-400/25 ring-1 ring-white/15"
        >
          <div className="absolute inset-0 rounded-2xl bg-sky-400/10 blur-md" />
          <CloudLightning size={20} className="relative text-sky-200" />
        </motion.div>

        <div className="min-w-0">
          <h1 className="font-display truncate text-[0.95rem] leading-tight font-bold tracking-tight text-gradient sm:text-xl">
            <span className="sm:hidden">Weather-Advisory Bot</span>
            <span className="hidden sm:inline">Weather-Advisory Support Bot</span>
          </h1>
          <p className="hidden text-[11.5px] text-[var(--text-faint)] sm:block">
            Every reply traces to a written policy, or an honest refusal.
          </p>
        </div>
      </div>

      <div className="hidden items-center gap-1.5 rounded-full bg-emerald-400/10 px-3 py-1.5 text-[11px] font-medium text-emerald-200 ring-1 ring-emerald-400/25 sm:flex">
        <ShieldCheck size={13} />
        Policy-grounded
      </div>
    </header>
  );
}
