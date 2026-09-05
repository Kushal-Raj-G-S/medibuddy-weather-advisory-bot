"use client";

import { useEffect, useMemo, useState } from "react";
import { Severity, skyClass } from "@/lib/severity";

interface Props {
  severity: Severity;
}

interface Cloud {
  id: number;
  top: string;
  width: number;
  height: number;
  duration: number;
  delay: number;
}

interface Star {
  id: number;
  top: string;
  left: string;
  delay: number;
}

interface Drop {
  id: number;
  left: string;
  height: number;
  duration: number;
  delay: number;
}

function useStable<T>(factory: () => T, deps: unknown[]): T {
  // Recompute only when deps change, not on every render - keeps the
  // procedurally generated cloud/star/rain layouts from jittering.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(factory, deps);
}

export default function WeatherBackground({ severity }: Props) {
  const [flashKey, setFlashKey] = useState(0);

  useEffect(() => {
    if (severity === "critical") setFlashKey((k) => k + 1);
  }, [severity]);

  const clouds = useStable<Cloud[]>(
    () =>
      Array.from({ length: severity === "informational" ? 4 : 7 }, (_, i) => ({
        id: i,
        top: `${8 + i * 11}%`,
        width: 180 + ((i * 47) % 160),
        height: 50 + ((i * 23) % 40),
        duration: 38 + ((i * 13) % 30),
        delay: -(i * 7),
      })),
    [severity]
  );

  const stars = useStable<Star[]>(
    () =>
      Array.from({ length: 60 }, (_, i) => ({
        id: i,
        top: `${(i * 37) % 70}%`,
        left: `${(i * 53) % 100}%`,
        delay: (i % 10) * 0.35,
      })),
    []
  );

  const showStars = severity === "informational" || severity === "neutral";
  const showSun = severity === "low";
  const showRain =
    severity === "moderate" || severity === "high" || severity === "critical";
  const heavyRain = severity === "high" || severity === "critical";

  const auroraColors: Record<Severity, [string, string, string]> = {
    informational: ["#3b82f6", "#6366f1", "#0ea5e9"],
    low: ["#10b981", "#0ea5a4", "#22d3ee"],
    moderate: ["#eab308", "#f59e0b", "#a855f7"],
    high: ["#f97316", "#ea580c", "#dc2626"],
    critical: ["#e11d48", "#7c3aed", "#0f172a"],
    neutral: ["#334155", "#1e293b", "#0f172a"],
  };
  const [c1, c2, c3] = auroraColors[severity];

  const drops = useStable<Drop[]>(
    () =>
      Array.from({ length: heavyRain ? 90 : 45 }, (_, i) => ({
        id: i,
        left: `${(i * 7.3) % 100}%`,
        height: 14 + ((i * 11) % 30),
        duration: heavyRain ? 0.5 + (i % 5) * 0.08 : 0.9 + (i % 5) * 0.12,
        delay: (i % 20) * 0.1,
      })),
    [heavyRain]
  );

  return (
    <>
      <div className={`sky ${skyClass(severity)}`} aria-hidden>
        <span
          className="aurora"
          style={{
            top: "-10%",
            left: "-8%",
            width: 520,
            height: 520,
            background: c1,
          }}
        />
        <span
          className="aurora"
          style={{
            top: "20%",
            right: "-10%",
            width: 460,
            height: 460,
            background: c2,
            animationDelay: "-8s",
          }}
        />
        <span
          className="aurora"
          style={{
            bottom: "-15%",
            left: "30%",
            width: 560,
            height: 560,
            background: c3,
            animationDelay: "-16s",
            opacity: 0.35,
          }}
        />

        {showStars &&
          stars.map((s) => (
            <span
              key={s.id}
              className="star"
              style={{ top: s.top, left: s.left, animationDelay: `${s.delay}s` }}
            />
          ))}

        {showSun && <div className="sun" />}

        {clouds.map((c) => (
          <span
            key={c.id}
            className="cloud"
            style={{
              top: c.top,
              width: c.width,
              height: c.height,
              animationDuration: `${c.duration}s`,
              animationDelay: `${c.delay}s`,
              opacity: severity === "critical" ? 0.9 : 0.5,
            }}
          />
        ))}

        {showRain &&
          drops.map((d) => (
            <span
              key={d.id}
              className="rain"
              style={{
                left: d.left,
                height: d.height,
                animationDuration: `${d.duration}s`,
                animationDelay: `${d.delay}s`,
              }}
            />
          ))}
      </div>
      <div key={flashKey} className={`lightning-flash ${flashKey ? "active" : ""}`} />
    </>
  );
}
