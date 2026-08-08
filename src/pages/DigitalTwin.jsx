import { useCallback, useEffect, useState } from "react";
import * as health from "@/services/healthService";
import {
  Badge, Card, Emphasised, ErrorNote, Eyebrow, PageHeading, PageSkeleton, statusColor, statusTone,
} from "@/components/ui";

export default function DigitalTwin() {
  const [data, setData] = useState(null);
  const [activeKey, setActiveKey] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  // Gate the risk-bar animation until after first paint so the bars grow from
  // zero rather than appearing at full width.
  const [revealed, setRevealed] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    health
      .fetchTwin()
      .then((result) => {
        setData(result);
        setActiveKey(result.nodes[0]?.key ?? null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  useEffect(() => {
    if (!data) return;
    const id = requestAnimationFrame(() => setRevealed(true));
    return () => cancelAnimationFrame(id);
  }, [data]);

  if (loading) return <PageSkeleton />;
  if (error) return <ErrorNote message={error} onRetry={load} />;
  if (!data) return null;

  const { summary, nodes, predispositions } = data;
  const active = nodes.find((n) => n.key === activeKey);
  const drift = summary ? (summary.biologicalAge - summary.actualAge).toFixed(1) : 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeading
        eyebrow="Digital Twin"
        title={<Emphasised text="*Your live model*" />}
        subtitle="Six body systems, scored from your own readings. Tap a node to read its detail."
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <Figure nodes={nodes} activeKey={activeKey} onSelect={setActiveKey} />

        <div className="flex flex-col gap-4">
          {summary && (
            <Card className="p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <Eyebrow>Model</Eyebrow>
                <div className="flex items-center gap-2">
                  <Badge tone="sage">Live model</Badge>
                  <span className="num text-xs" style={{ color: "var(--ink-faint)" }}>
                    {summary.modelVersion}
                  </span>
                </div>
              </div>

              <p className="num mt-4 text-[3.2rem] font-bold leading-none">
                {summary.healthScore}
                <span className="text-2xl" style={{ color: "var(--ink-faint)" }}>
                  /100
                </span>
              </p>
              <Eyebrow className="mt-1">Health score</Eyebrow>

              <div className="mt-6 flex items-end gap-8">
                <div>
                  <Eyebrow>Biological age</Eyebrow>
                  <p
                    className="num mt-1 text-2xl font-bold"
                    style={{ color: drift > 0 ? "var(--amber)" : "var(--sage)" }}
                  >
                    {summary.biologicalAge}
                  </p>
                </div>
                <div>
                  <Eyebrow>Actual age</Eyebrow>
                  <p className="num mt-1 text-2xl font-bold">{summary.actualAge}</p>
                </div>
                <p className="pb-1 text-sm" style={{ color: "var(--ink-muted)" }}>
                  {Math.abs(drift)} years {drift > 0 ? "older" : "younger"}
                </p>
              </div>
            </Card>
          )}

          <Card className="p-6">
            <Eyebrow>System risk</Eyebrow>
            <div className="mt-4 flex flex-col gap-3.5">
              {nodes.map((node) => (
                <button
                  key={node.key}
                  type="button"
                  onClick={() => setActiveKey(node.key)}
                  className="text-left"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span
                      className="text-sm font-semibold"
                      style={{ color: node.key === activeKey ? "var(--primary)" : "var(--ink)" }}
                    >
                      {node.label}
                    </span>
                    <span className="num text-sm" style={{ color: statusColor(node.status) }}>
                      {node.riskPct}%
                    </span>
                  </div>
                  <div
                    className="mt-1.5 h-1.5 overflow-hidden rounded-full"
                    style={{ backgroundColor: "var(--surface-2)" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: revealed ? `${node.riskPct}%` : "0%",
                        backgroundColor: statusColor(node.status),
                        transition: "width 900ms cubic-bezier(0.22, 1, 0.36, 1)",
                      }}
                    />
                  </div>
                </button>
              ))}
            </div>
          </Card>

          {active && (
            <Card className="p-6">
              <div className="flex items-center justify-between gap-3">
                <Eyebrow>Active node</Eyebrow>
                <Badge tone={statusTone(active.status)}>{active.status}</Badge>
              </div>
              <h3 className="mt-2 text-xl">{active.label}</h3>
              <p className="num mt-1 text-3xl font-bold" style={{ color: statusColor(active.status) }}>
                {active.riskPct}%
              </p>
              <p className="mt-3 text-sm" style={{ color: "var(--ink-muted)" }}>
                {active.note}
              </p>
            </Card>
          )}
        </div>
      </div>

      <section>
        <h2 className="mb-3.5 text-xl">
          <Emphasised text="*What you're prone to*" />
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          {predispositions.map((item) => (
            <Card key={item.id} className="flex flex-col p-6">
              <h3 className="text-lg">{item.condition}</h3>
              <p className="num mt-2 text-[2.6rem] font-bold leading-none" style={{ color: "var(--accent)" }}>
                {item.probabilityPct}%
              </p>
              <Eyebrow className="mt-1">10-year probability</Eyebrow>

              <Eyebrow className="mt-5">Drivers</Eyebrow>
              <ul className="mt-1.5 flex flex-col gap-1">
                {item.drivers.map((driver) => (
                  <li key={driver} className="text-sm" style={{ color: "var(--ink-muted)" }}>
                    {driver}
                  </li>
                ))}
              </ul>

              <div
                className="mt-auto rounded-2xl p-4"
                style={{ backgroundColor: "var(--accent-wash)", marginTop: "1.5rem" }}
              >
                <Eyebrow style={{ color: "var(--accent)" }}>The lever you control</Eyebrow>
                <p className="mt-1.5 text-sm" style={{ color: "var(--ink)" }}>
                  {item.lever}
                </p>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

/**
 * Abstract silhouette — deliberately non-anatomical: soft gradients and light
 * lines, with the six system nodes positioned over it. Inline SVG so the
 * node colours can resolve through the same tokens as the rest of the app.
 */
function Figure({ nodes, activeKey, onSelect }) {
  return (
    <Card
      className="relative flex items-center justify-center overflow-hidden p-6"
      style={{
        minHeight: 460,
        background:
          "radial-gradient(120% 90% at 50% 12%, var(--primary-wash), transparent 62%), var(--surface)",
      }}
    >
      <div className="relative" style={{ width: 220, height: 400 }}>
        <svg viewBox="0 0 220 400" className="absolute inset-0 h-full w-full" aria-hidden="true">
          <defs>
            <linearGradient id="twinBody" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.30" />
              <stop offset="55%" stopColor="var(--primary)" stopOpacity="0.16" />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.06" />
            </linearGradient>
            <filter id="twinBlur">
              <feGaussianBlur stdDeviation="7" />
            </filter>
          </defs>

          {/* Soft glow behind the silhouette */}
          <ellipse cx="110" cy="190" rx="66" ry="150" fill="var(--primary)" opacity="0.13" filter="url(#twinBlur)" />

          {/* Silhouette: head, torso, limbs — rounded, abstract */}
          <circle cx="110" cy="46" r="27" fill="url(#twinBody)" stroke="var(--primary)" strokeOpacity="0.32" />
          <path
            d="M110 80 C 74 84, 62 108, 62 140 L 62 208 C 62 232, 72 244, 78 268 L 86 340 C 88 356, 96 366, 96 380
               L 124 380 C 124 366, 132 356, 134 340 L 142 268 C 148 244, 158 232, 158 208 L 158 140
               C 158 108, 146 84, 110 80 Z"
            fill="url(#twinBody)"
            stroke="var(--primary)"
            strokeOpacity="0.32"
          />
          <path d="M64 132 C 44 146, 38 176, 40 214" fill="none" stroke="var(--primary)" strokeOpacity="0.26" strokeWidth="9" strokeLinecap="round" />
          <path d="M156 132 C 176 146, 182 176, 180 214" fill="none" stroke="var(--primary)" strokeOpacity="0.26" strokeWidth="9" strokeLinecap="round" />

          {/* Light lines suggesting circulation */}
          <path d="M110 96 L110 250" stroke="var(--primary)" strokeOpacity="0.2" strokeWidth="1" strokeDasharray="4 7" />
          <path d="M84 150 L136 150" stroke="var(--primary)" strokeOpacity="0.16" strokeWidth="1" strokeDasharray="4 7" />
        </svg>

        {nodes.map((node) => {
          const isActive = node.key === activeKey;
          const colour = statusColor(node.status);
          return (
            <button
              key={node.key}
              type="button"
              onClick={() => onSelect(node.key)}
              aria-label={`${node.label} — ${node.riskPct}% risk`}
              aria-pressed={isActive}
              className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full"
              style={{
                left: `${node.x}%`,
                top: `${node.y}%`,
                width: isActive ? 30 : 22,
                height: isActive ? 30 : 22,
                backgroundColor: colour,
                opacity: isActive ? 1 : 0.62,
                boxShadow: `0 0 ${isActive ? 26 : 14}px ${colour}`,
                transition: "all 260ms ease",
                animation: "twinPulse 2.8s ease-in-out infinite",
                animationDelay: `${node.y * 12}ms`,
              }}
            />
          );
        })}
      </div>

      <style>{`
        @keyframes twinPulse {
          0%, 100% { transform: translate(-50%, -50%) scale(1); }
          50%      { transform: translate(-50%, -50%) scale(1.16); }
        }
        @media (prefers-reduced-motion: reduce) {
          @keyframes twinPulse { 0%, 100% { transform: translate(-50%, -50%) scale(1); } }
        }
      `}</style>
    </Card>
  );
}
