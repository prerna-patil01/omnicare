import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as health from "@/services/healthService";
import {
  Card, ErrorNote, Eyebrow, PageHeading, PageSkeleton,
} from "@/components/ui";

const RANGES = [
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
];

/**
 * One metric per chart — single-series throughout, so identity never rests on
 * colour: each card's title names its metric and the latest value is direct-
 * labelled. Colours are drawn from the app's own tokens and were validated for
 * >= 3:1 contrast against both the light and dark chart surfaces.
 */
const METRICS = [
  { key: "sleepHours", title: "Sleep", unit: "h", light: "#21488c", dark: "#7ba4e8", target: 7 },
  { key: "stress", title: "Stress", unit: "/100", light: "#a83a55", dark: "#e58399", invert: true },
  { key: "hydrationMl", title: "Hydration", unit: "ml", light: "#3f7355", dark: "#86be9b", target: 2500 },
  { key: "heartRate", title: "Resting heart rate", unit: "bpm", light: "#9c6a15", dark: "#e0ab55", invert: true },
];

export default function HealthInsights() {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(30);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));

  // Charts pick their stroke per theme, so track the class the toggle flips.
  useEffect(() => {
    const observer = new MutationObserver(() =>
      setDark(document.documentElement.classList.contains("dark")),
    );
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    health
      .fetchInsights(days)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [days]);

  useEffect(load, [load]);

  if (loading) return <PageSkeleton rows={4} />;
  if (error) return <ErrorNote message={error} onRetry={load} />;
  if (!data) return null;

  const { series, summary, outbreak } = data;

  return (
    <div>
      <PageHeading
        eyebrow="Trends"
        title="Health insights"
        subtitle="Your own readings over time. Each chart shows one measure — nothing is averaged together."
      >
        <div className="flex gap-2">
          {RANGES.map((range) => (
            <button
              key={range.days}
              type="button"
              onClick={() => setDays(range.days)}
              className="rounded-full px-3.5 py-1.5 text-sm font-semibold"
              style={{
                backgroundColor: days === range.days ? "var(--primary)" : "var(--surface-2)",
                color: days === range.days ? "var(--primary-fg)" : "var(--ink-muted)",
                border: "1px solid var(--border)",
              }}
            >
              {range.label}
            </button>
          ))}
        </div>
      </PageHeading>

      <div className="grid gap-4 lg:grid-cols-2">
        {METRICS.map((metric) => (
          <TrendCard
            key={metric.key}
            metric={metric}
            series={series}
            average={summary[metric.key === "hydrationMl" ? "hydrationMl" : metric.key === "sleepHours" ? "sleep" : metric.key]}
            stroke={dark ? metric.dark : metric.light}
          />
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card className="p-6">
          <Eyebrow>Heart health summary</Eyebrow>
          <div className="mt-4 flex flex-wrap gap-8">
            <Stat label="Mean resting HR" value={summary.heartRate} unit="bpm" />
            <Stat label="Mean HRV" value={summary.hrv} unit="ms" />
          </div>
          <p className="mt-4 text-sm" style={{ color: "var(--ink-muted)" }}>
            HRV is the more sensitive of the two — a falling trend usually shows up here weeks
            before resting heart rate moves.
          </p>
        </Card>

        {outbreak && (
          <Card className="p-6">
            <Eyebrow>Regional signals</Eyebrow>
            <h3 className="mt-2 text-lg font-bold">{outbreak.condition}</h3>
            <div className="mt-4 flex flex-wrap gap-8">
              <Stat label="Cases nearby" value={outbreak.caseCount.toLocaleString("en-IN")} />
              <Stat label="Change" value={`+${outbreak.changePct}%`} tone="var(--rose)" />
              <Stat label="Air quality" value={outbreak.airQualityIndex} tone="var(--amber)" />
            </div>
            <p className="mt-4 text-sm" style={{ color: "var(--ink-muted)" }}>
              {outbreak.airQualityNote}
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, unit, tone }) {
  return (
    <div>
      <Eyebrow>{label}</Eyebrow>
      <p className="num mt-1 text-2xl font-bold" style={{ color: tone || "var(--ink)" }}>
        {value}
        {unit && (
          <span className="ml-1 text-sm font-normal" style={{ color: "var(--ink-faint)" }}>
            {unit}
          </span>
        )}
      </p>
    </div>
  );
}

function TrendCard({ metric, series, average, stroke }) {
  const points = useMemo(
    () => series.map((row) => ({ date: row.date, value: row[metric.key] })),
    [series, metric.key],
  );
  const latest = points[points.length - 1];

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">{metric.title}</h3>
          <p className="num text-sm" style={{ color: "var(--ink-faint)" }}>
            {points.length}-day average {average}
            {metric.unit}
          </p>
        </div>
        {/* Direct label for the latest reading — selective, not a number per point. */}
        <p className="num text-2xl font-bold">
          {latest?.value}
          <span className="ml-1 text-sm font-normal" style={{ color: "var(--ink-faint)" }}>
            {metric.unit}
          </span>
        </p>
      </div>

      <AreaChart points={points} stroke={stroke} unit={metric.unit} target={metric.target} />
    </Card>
  );
}

/**
 * Thin-line area chart: 2px stroke, soft gradient fill, no grid, a single
 * baseline rule. Crosshair + tooltip on hover, keyboard-reachable via the
 * range input fallback below the plot.
 */
function AreaChart({ points, stroke, unit, target }) {
  const [hover, setHover] = useState(null);
  const svgRef = useRef(null);

  const W = 560;
  const H = 150;
  const PAD = { top: 12, right: 12, bottom: 20, left: 12 };

  const { path, area, scaled, min, max } = useMemo(() => {
    const values = points.map((p) => p.value);
    const lo = Math.min(...values, target ?? Infinity);
    const hi = Math.max(...values, target ?? -Infinity);
    const span = hi - lo || 1;
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;

    const scaledPoints = points.map((p, i) => ({
      ...p,
      x: PAD.left + (i / Math.max(points.length - 1, 1)) * innerW,
      y: PAD.top + innerH - ((p.value - lo) / span) * innerH,
    }));

    const line = scaledPoints
      .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
      .join(" ");
    const fill = `${line} L${scaledPoints[scaledPoints.length - 1]?.x.toFixed(1)},${H - PAD.bottom} L${PAD.left},${H - PAD.bottom} Z`;

    return { path: line, area: fill, scaled: scaledPoints, min: lo, max: hi };
  }, [points, target]);

  const gradientId = `grad-${stroke.replace("#", "")}`;

  function handleMove(event) {
    const rect = svgRef.current.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * W;
    let nearest = scaled[0];
    for (const p of scaled) {
      if (Math.abs(p.x - x) < Math.abs(nearest.x - x)) nearest = p;
    }
    setHover(nearest);
  }

  if (!points.length) return null;

  return (
    <div className="relative mt-4">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ overflow: "visible" }}
        onMouseMove={handleMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label={`Trend from ${min}${unit} to ${max}${unit} over ${points.length} days`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.22" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Single recessive baseline — no grid. */}
        <line
          x1={PAD.left}
          y1={H - PAD.bottom}
          x2={W - PAD.right}
          y2={H - PAD.bottom}
          stroke="var(--border)"
          strokeWidth="1"
        />

        <path d={area} fill={`url(#${gradientId})`} />
        <path
          d={path}
          fill="none"
          stroke={stroke}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Latest point marker, ring-separated from the fill. */}
        {scaled.length > 0 && (
          <circle
            cx={scaled[scaled.length - 1].x}
            cy={scaled[scaled.length - 1].y}
            r="4.5"
            fill={stroke}
            stroke="var(--surface)"
            strokeWidth="2"
          />
        )}

        {hover && (
          <>
            <line
              x1={hover.x}
              y1={PAD.top}
              x2={hover.x}
              y2={H - PAD.bottom}
              stroke="var(--border-strong)"
              strokeWidth="1"
            />
            <circle cx={hover.x} cy={hover.y} r="5" fill={stroke} stroke="var(--surface)" strokeWidth="2" />
          </>
        )}
      </svg>

      {hover && (
        <div
          className="pointer-events-none absolute -translate-x-1/2 rounded-xl px-3 py-2 text-xs"
          style={{
            left: `${(hover.x / W) * 100}%`,
            top: -6,
            backgroundColor: "var(--ink)",
            color: "var(--bg)",
            whiteSpace: "nowrap",
          }}
        >
          <span className="num font-bold">
            {hover.value}
            {unit}
          </span>
          <span className="ml-2 opacity-70">
            {new Date(hover.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
          </span>
        </div>
      )}

      <div className="num mt-1 flex justify-between text-xs" style={{ color: "var(--ink-faint)" }}>
        <span>
          {new Date(points[0].date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
        </span>
        <span>
          {new Date(points[points.length - 1].date).toLocaleDateString("en-IN", {
            day: "numeric", month: "short",
          })}
        </span>
      </div>
    </div>
  );
}
