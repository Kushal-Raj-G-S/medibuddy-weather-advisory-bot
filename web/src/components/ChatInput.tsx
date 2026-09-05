"use client";

import { useState, KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { ArrowUp, CloudRain, Sun, Users } from "lucide-react";

const SUGGESTIONS = [
  { icon: CloudRain, text: "Is it safe to cycle in Bhopal today?" },
  { icon: Sun, text: "Is today a good day for a picnic in Bengaluru?" },
  { icon: Users, text: "Should I take my kid to the park this evening?" },
];

export default function ChatInput({
  onSend,
  disabled,
  showSuggestions,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
  showSuggestions: boolean;
}) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="w-full">
      {showSuggestions && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-3 flex flex-wrap gap-2"
        >
          {SUGGESTIONS.map(({ icon: Icon, text }, i) => (
            <motion.button
              key={text}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.06 }}
              whileHover={{ y: -2 }}
              onClick={() => onSend(text)}
              disabled={disabled}
              className="glass flex items-center gap-1.5 rounded-full px-3.5 py-2 text-xs text-[var(--text-muted)] transition hover:text-[var(--text-primary)] disabled:opacity-40"
            >
              <Icon size={12} className="text-sky-300/80" />
              {text}
            </motion.button>
          ))}
        </motion.div>
      )}

      <div
        className={`glass-strong flex items-end gap-2 rounded-2xl p-2 pl-4 transition-shadow ${
          focused ? "shadow-[0_0_0_1px_rgba(125,211,252,0.35),0_0_32px_-8px_rgba(125,211,252,0.35)]" : ""
        }`}
      >
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          rows={1}
          placeholder="Ask about an outdoor activity, e.g. is it safe to cycle today?"
          className="max-h-32 min-h-[24px] flex-1 resize-none bg-transparent py-2 text-sm outline-none placeholder:text-[var(--text-faint)]"
        />
        <motion.button
          whileHover={{ scale: value.trim() ? 1.05 : 1 }}
          whileTap={{ scale: 0.92 }}
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400 to-sky-500 text-slate-950 shadow-[0_4px_16px_-4px_rgba(56,189,248,0.6)] transition disabled:cursor-not-allowed disabled:bg-none disabled:bg-white/8 disabled:text-[var(--text-faint)] disabled:shadow-none"
        >
          <ArrowUp size={16} strokeWidth={2.4} />
        </motion.button>
      </div>
    </div>
  );
}
