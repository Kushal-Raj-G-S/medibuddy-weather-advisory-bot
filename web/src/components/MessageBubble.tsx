"use client";

import { motion } from "framer-motion";
import { CloudSun, User } from "lucide-react";
import CitationCard from "./CitationCard";
import TraceViewer from "./TraceViewer";
import { AskResult } from "@/lib/api";
import { normalizeSeverity, SEVERITY_META } from "@/lib/severity";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  result?: AskResult;
  error?: boolean;
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const severity = normalizeSeverity(message.result?.citation.severity);
  const meta = SEVERITY_META[severity];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 28 }}
      className={`flex w-full gap-3 ${isUser ? "flex-row-reverse self-end" : "self-start"}`}
      style={{ maxWidth: "min(640px, 92%)" }}
    >
      <div
        className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl ring-1 ${
          isUser
            ? "bg-gradient-to-br from-violet-400/20 to-fuchsia-400/20 ring-violet-400/25"
            : "bg-gradient-to-br from-sky-400/20 to-cyan-400/20 ring-sky-400/25"
        }`}
      >
        {isUser ? (
          <User size={15} className="text-violet-200" />
        ) : (
          <CloudSun size={15} className="text-sky-200" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div
          className={`glass relative rounded-2xl px-4 py-3 text-[13.5px] leading-relaxed whitespace-pre-wrap ${
            isUser ? "rounded-tr-md" : "rounded-tl-md"
          } ${message.error ? "ring-1 ring-rose-400/40" : ""}`}
        >
          {!isUser && !message.error && message.result?.citation.sop_id && (
            <span
              className={`absolute top-3 -left-[1px] h-[calc(100%-1.5rem)] w-[2.5px] rounded-full ${meta.dot} opacity-70`}
            />
          )}
          {message.content}
        </div>

        {!isUser && message.result && (
          <>
            <CitationCard citation={message.result.citation} />
            <TraceViewer trace={message.result.trace} />
          </>
        )}
      </div>
    </motion.div>
  );
}
