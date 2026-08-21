import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ArrowDownRight, ArrowUpRight, Bookmark, Heart, Moon, Wind } from "lucide-react";
import { toast } from "sonner";
import * as health from "@/services/healthService";
import {
  Badge, Button, Card, Emphasised, ErrorNote, Eyebrow, NeedsData, PageSkeleton,
} from "@/components/ui";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    health
      .fetchDashboard()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  if (loading) return <PageSkeleton />;
  if (error) return <ErrorNote message={error} onRetry={load} />;
  if (!data) return null;

  const { greeting, finding, vitals, outbreak, twin, hasReadings, readingCount, readingsNeeded } = data;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Eyebrow>
          {greeting.weekday} · {greeting.region}
        </Eyebrow>
        <h1 className="mt-1.5 text-[2.1rem]">Good to see you, {greeting.firstName}.</h1>
      </div>

      {finding ? (
        <HeroPanel finding={finding} />
      ) : (
        <NeedsData
          title="No assessment yet"
          body="Omni will not tell you anything about your health until you have given it something real to read. Log a few readings and an assessment appears here, showing the measurements it came from."
          have={readingCount}
          need={readingsNeeded}
        />
      )}

      {hasReadings && (
        <section>
          <Eyebrow className="mb-3">Latest readings</Eyebrow>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <VitalCard icon={Heart} label="Heart rate" vital={vitals.heartRate} />
            <VitalCard icon={Activity} label="HRV" vital={vitals.hrv} />
            <VitalCard icon={Wind} label="SpO₂" vital={vitals.spo2} />
            <VitalCard icon={Moon} label="Sleep" vital={vitals.sleep} />
          </div>
        </section>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {outbreak && <OutbreakCard outbreak={outbreak} />}
        {twin && <TwinPreviewCard twin={twin} />}
      </div>
    </div>
  );
}

function HeroPanel({ finding }) {
  const bandTone =
    finding.severity === "critical" ? "rose" : finding.severity === "watch" ? "amber" : "sage";

  return (
    <section className="hero-panel p-6 sm:p-8">
      <div className="grid gap-8 lg:grid-cols-[1.6fr_1fr]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Eyebrow style={{ color: "var(--hero-fg-muted)" }}>Omni · clinical finding</Eyebrow>
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.66rem] font-bold uppercase tracking-[0.12em]"
              style={{ backgroundColor: "var(--hero-inset)", color: "var(--hero-fg)" }}
            >
              <span
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: "var(--accent)" }}
              />
              Live
            </span>
          </div>

          <h2 className="mt-3 text-[1.85rem] sm:text-[2.15rem]" style={{ color: "var(--hero-fg)" }}>
            <Emphasised text={finding.headline} />
          </h2>
          <p className="mt-2 text-lg" style={{ color: "var(--hero-fg-muted)" }}>
            Lead system: {finding.leadSystem}
          </p>

          <ul className="mt-5 flex flex-col gap-2.5">
            {finding.reasoning.map((reason, i) => (
              <li key={i} className="flex gap-3 text-[0.95rem]" style={{ color: "var(--hero-fg-muted)" }}>
                <span
                  className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: "var(--accent)" }}
                />
                {reason}
              </li>
            ))}
          </ul>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link to="/doctors">
              <Button variant="accent">Find a specialist</Button>
            </Link>
            <Link to="/omni">
              <Button variant="onHero">Discuss with Omni</Button>
            </Link>
            <span
              className="num inline-flex items-center gap-1.5 text-sm"
              style={{ color: "var(--hero-fg-muted)" }}
            >
              <Bookmark size={15} />
              From {finding.basedOnReadings} of your readings
            </span>
          </div>
        </div>

        <div
          className="rounded-3xl p-6"
          style={{ backgroundColor: "var(--hero-inset)", border: "1px solid var(--hero-border)" }}
        >
          <Eyebrow style={{ color: "var(--hero-fg-muted)" }}>Risk score</Eyebrow>
          <p className="num mt-2 text-[3.4rem] leading-none font-bold" style={{ color: "var(--hero-fg)" }}>
            {finding.riskScore}
            <span className="text-2xl" style={{ color: "var(--hero-fg-muted)" }}>
              /10
            </span>
          </p>
          <div className="mt-3">
            <Badge tone={bandTone}>{finding.riskBand}</Badge>
          </div>

          <p className="label-eyebrow mt-6" style={{ color: "var(--hero-fg-muted)" }}>
            Suggested next
          </p>
          <ul className="mt-2 flex flex-col gap-1.5">
            {finding.suggestedNext.map((item) => (
              <li key={item} className="text-sm" style={{ color: "var(--hero-fg)" }}>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function VitalCard({ icon: Icon, label, vital }) {
  if (!vital) return null;
  const unknown = vital.trend === null || vital.trend === undefined;
  const rising = vital.trend > 0;
  const flat = vital.trend === 0;

  return (
    <Card className="p-4 transition-shadow hover:shadow-[var(--shadow-lift)]">
      <div className="flex items-center gap-2">
        <Icon size={15} style={{ color: "var(--ink-faint)" }} aria-hidden="true" />
        <Eyebrow>{label}</Eyebrow>
      </div>
      <p className="num mt-2.5 text-[1.9rem] font-bold leading-none">
        {vital.value}
        <span className="ml-1 text-sm font-normal" style={{ color: "var(--ink-faint)" }}>
          {vital.unit}
        </span>
      </p>
      <p
        className="num mt-2 flex items-center gap-1 text-xs"
        style={{
          color: unknown || flat ? "var(--ink-faint)" : rising ? "var(--amber)" : "var(--sage)",
        }}
      >
        {!unknown && !flat &&
          (rising ? <ArrowUpRight size={13} aria-hidden="true" /> : <ArrowDownRight size={13} aria-hidden="true" />)}
        {unknown ? "No earlier reading" : flat ? "No change" : `${rising ? "+" : ""}${vital.trend} vs previous`}
      </p>
    </Card>
  );
}

function OutbreakCard({ outbreak }) {
  return (
    <Card className="p-6">
      <Eyebrow>Regional disease intelligence</Eyebrow>
      <h3 className="mt-2 text-xl">{outbreak.condition}</h3>
      <div className="mt-4 flex flex-wrap gap-6">
        <Figure label="Change" value={`+${outbreak.changePct}%`} tone="var(--rose)" />
        <Figure label="Cases" value={outbreak.caseCount.toLocaleString("en-IN")} />
        <Figure label="Radius" value={`${outbreak.radiusKm} km`} />
        <Figure label="AQI" value={outbreak.airQualityIndex} tone="var(--amber)" />
      </div>
      <p className="mt-4 text-sm" style={{ color: "var(--ink-muted)" }}>
        {outbreak.airQualityNote}
      </p>
    </Card>
  );
}

function TwinPreviewCard({ twin }) {
  return (
    <Card className="flex flex-col p-6">
      <Eyebrow>Digital Twin</Eyebrow>
      <h3 className="mt-2 text-xl">
        <Emphasised text="*Your live model*" />
      </h3>
      <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
        A continuously updated model of your physiology, built from your vitals, reports, and
        history — six body systems scored independently.
      </p>
      <div className="mt-5 flex flex-wrap gap-6">
        <Figure label="Health score" value={`${twin.healthScore}/100`} />
        <Figure label="Systems scored" value={`${twin.measuredSystems}/${twin.totalSystems}`} />
        <Figure label="From readings" value={twin.basedOnReadings} />
      </div>
      <p className="mt-3 text-sm" style={{ color: "var(--ink-muted)" }}>
        {twin.measuredSystems} of {twin.totalSystems} systems can be scored from what you have
        logged. The rest need bloodwork.
      </p>
      <Link
        to="/twin"
        className="mt-auto pt-5 text-sm font-semibold"
        style={{ color: "var(--primary)" }}
      >
        Open the full model →
      </Link>
    </Card>
  );
}

function Figure({ label, value, tone }) {
  return (
    <div>
      <Eyebrow>{label}</Eyebrow>
      <p className="num mt-1 text-xl font-bold" style={{ color: tone || "var(--ink)" }}>
        {value}
      </p>
    </div>
  );
}
