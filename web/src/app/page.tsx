"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CloudSun } from "lucide-react";
import WeatherBackground from "@/components/WeatherBackground";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import ChatInput from "@/components/ChatInput";
import TypingIndicator from "@/components/TypingIndicator";
import MessageBubble, { ChatMessage } from "@/components/MessageBubble";
import { askQuestion } from "@/lib/api";
import { normalizeSeverity, Severity } from "@/lib/severity";

function newThreadId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

export default function Home() {
  // Generated client-side only, after mount: computing this during the
  // initial render would make the server-rendered id and the client's first
  // render id differ (crypto.randomUUID() is random each call), which is a
  // textbook React hydration mismatch. An empty string is the stable initial
  // value both sides agree on.
  const [threadId, setThreadId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [severity, setSeverity] = useState<Severity>("neutral");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setThreadId(newThreadId());
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  const send = async (text: string) => {
    setMessages((m) => [...m, { role: "user", content: text }]);
    setPending(true);
    try {
      const result = await askQuestion(text, threadId);
      setSeverity(normalizeSeverity(result.citation?.severity));
      setMessages((m) => [
        ...m,
        { role: "assistant", content: result.answer, result },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `Couldn't reach the backend: ${
            e instanceof Error ? e.message : String(e)
          }. Is the FastAPI server running (uvicorn api.main:app)?`,
          error: true,
        },
      ]);
    } finally {
      setPending(false);
    }
  };

  const newSession = () => {
    setThreadId(newThreadId());
    setMessages([]);
    setSeverity("neutral");
  };

  return (
    <div className="relative flex min-h-screen flex-col">
      <WeatherBackground severity={severity} signal={messages.length} />
      <div className="grain" />

      <div className="mx-auto flex w-full max-w-6xl flex-1 gap-5 p-4 lg:p-6">
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNewSession={newSession}
          threadId={threadId}
        />

        <main className="flex min-w-0 flex-1 flex-col gap-4">
          <Header onMenu={() => setSidebarOpen(true)} />

          <div className="glass flex flex-1 flex-col gap-4 overflow-y-auto rounded-3xl p-5">
            {messages.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="m-auto max-w-sm text-center"
              >
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: "spring", stiffness: 200, damping: 14 }}
                  className="relative mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-sky-400/20 via-indigo-400/15 to-violet-400/20 ring-1 ring-white/10"
                >
                  <div className="absolute inset-0 rounded-3xl bg-sky-400/15 blur-xl" />
                  <CloudSun size={28} className="relative text-sky-200" />
                </motion.div>
                <p className="font-display text-lg font-bold tracking-tight text-gradient">
                  Ask about an outdoor plan
                </p>
                <p className="mt-2 text-[13px] leading-relaxed text-[var(--text-muted)]">
                  Cycling, a picnic, taking the kids out, a commute — the bot
                  checks live weather and a written policy before answering.
                  Nothing it says is free-floating advice.
                </p>
              </motion.div>
            )}

            <AnimatePresence initial={false}>
              {messages.map((m, i) => (
                <MessageBubble key={i} message={m} />
              ))}
              {pending && (
                <TypingIndicator
                  key="typing"
                  label="Checking policy and live conditions…"
                />
              )}
            </AnimatePresence>
            <div ref={bottomRef} />
          </div>

          <ChatInput
            onSend={send}
            disabled={pending || !threadId}
            showSuggestions={messages.length === 0}
          />
        </main>
      </div>
    </div>
  );
}
