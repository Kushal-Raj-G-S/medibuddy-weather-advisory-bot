"use client";

import { motion } from "framer-motion";
import { CloudLightning } from "lucide-react";

export default function TypingIndicator({ label }: { label: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className="flex items-center gap-3 self-start"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sky-400/15 ring-1 ring-sky-400/30">
        <CloudLightning size={16} className="text-sky-200" />
      </div>
      <div className="glass flex items-center gap-2 rounded-2xl rounded-tl-sm px-4 py-3">
        <span className="text-xs text-[var(--text-muted)]">{label}</span>
        <span className="flex gap-1">
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-sky-300" />
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-sky-300" />
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-sky-300" />
        </span>
      </div>
    </motion.div>
  );
}
