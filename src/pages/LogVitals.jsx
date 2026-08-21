import { useCallback, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import * as health from "@/services/healthService";
import {
  Button, Card, EmptyNote, ErrorNote, Eyebrow, PageHeading, PageSkeleton,
} from "@/components/ui";

/**
 * The only place clinical numbers enter OmniCare. Everything the dashboard,
 * twin, insights, and Omni show is computed from what is entered here — so an
 * empty form means empty pages, by design.
 */
const FIELDS = [
  { key: "heartRate", label: "Resting heart rate", unit: "bpm", placeholder: "68", step: "1",
    hint: "Measured after sitting still for five minutes." },
  { key: "hrv", label: "HRV", unit: "ms", placeholder: "45", step: "1",
    hint: "From a wearable or a measuring app, if you have one." },
  { key: "spo2", label: "Blood oxygen", unit: "%", placeholder: "98", step: "1",
    hint: "From a pulse oximeter." },
  { key: "sleepHours", label: "Sleep", unit: "h", placeholder: "7.5", step: "0.1",
    hint: "Total hours slept last night." },
  { key: "stress", label: "Stress", unit: "/100", placeholder: "35", step: "1",
    hint: "Your own rating, 0 calm to 100 overwhelmed." },
  { key: "hydrationMl", label: "Water", unit: "ml", placeholder: "2200", step: "50",
    hint: "Total drunk across the day." },
];

const today = () => new Date().toISOString().slice(0, 10);

export default function LogVitals() {
  const [readings, setReadings] = useState([]);
  const [form, setForm] = useState({ date: today() });
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setError("");
    health
      .fetchVitals()
      .then((data) => setReadings(data.readings))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const update = (key) => (event) => {
    const { value } = event.target;
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => (prev[key] ? { ...prev, [key]: undefined } : prev));
  };

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setFieldErrors({});
    try {
      const { created } = await health.logVitals(form);
      toast.success(created ? "Reading logged" : "Reading updated for that date");
      setForm({ date: today() });
      load();
    } catch (err) {
      if (err.errors) setFieldErrors(err.errors);
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(date) {
    try {
      await health.deleteVitals(date);
      setReadings((prev) => prev.filter((r) => r.date !== date));
      toast.success("Reading removed");
    } catch (err) {
      toast.error(err.message);
    }
  }

  return (
    <div>
      <PageHeading
        eyebrow="Your data"
        title="Log a reading"
        subtitle="Enter what you measured. Fill in only the fields you have — nothing is required, and nothing is estimated for you."
      />

      <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        <Card className="p-6">
          <form onSubmit={handleSubmit} noValidate>
            <div className="mb-5">
              <label htmlFor="date" className="label-eyebrow">
                Date
              </label>
              <input
                id="date"
                type="date"
                max={today()}
                value={form.date || ""}
                onChange={update("date")}
                className="mt-1.5 w-full rounded-xl px-3.5 py-2.5 outline-none sm:w-auto"
                style={{
                  backgroundColor: "var(--surface-2)",
                  border: `1px solid ${fieldErrors.date ? "var(--rose)" : "var(--border)"}`,
                }}
              />
              {fieldErrors.date && (
                <p className="mt-1 text-sm" style={{ color: "var(--rose)" }}>
                  {fieldErrors.date}
                </p>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {FIELDS.map((field) => (
                <div key={field.key} className="flex flex-col gap-1.5">
                  <label htmlFor={field.key} className="label-eyebrow">
                    {field.label} <span style={{ textTransform: "none" }}>({field.unit})</span>
                  </label>
                  <input
                    id={field.key}
                    type="number"
                    inputMode="decimal"
                    step={field.step}
                    placeholder={field.placeholder}
                    value={form[field.key] ?? ""}
                    onChange={update(field.key)}
                    aria-invalid={fieldErrors[field.key] ? "true" : undefined}
                    className="rounded-xl px-3.5 py-2.5 outline-none"
                    style={{
                      backgroundColor: "var(--surface-2)",
                      border: `1px solid ${fieldErrors[field.key] ? "var(--rose)" : "var(--border)"}`,
                    }}
                  />
                  <p
                    className="text-xs"
                    style={{ color: fieldErrors[field.key] ? "var(--rose)" : "var(--ink-faint)" }}
                  >
                    {fieldErrors[field.key] || field.hint}
                  </p>
                </div>
              ))}
            </div>

            {fieldErrors._ && (
              <p className="mt-4 text-sm" style={{ color: "var(--rose)" }}>
                {fieldErrors._}
              </p>
            )}

            <Button type="submit" disabled={saving} className="mt-6">
              {saving ? "Saving…" : "Save reading"}
            </Button>
            <p className="mt-3 text-sm" style={{ color: "var(--ink-faint)" }}>
              Logging the same date twice updates that day rather than adding a duplicate.
            </p>
          </form>
        </Card>

        <Card className="p-6">
          <div className="flex items-baseline justify-between gap-3">
            <Eyebrow>Your readings</Eyebrow>
            <span className="num text-sm" style={{ color: "var(--ink-faint)" }}>
              {readings.length} logged
            </span>
          </div>

          {loading ? (
            <PageSkeleton rows={1} />
          ) : error ? (
            <ErrorNote message={error} onRetry={load} />
          ) : readings.length === 0 ? (
            <EmptyNote>
              Nothing logged yet. Your first reading unlocks the trend charts; seven unlock the
              digital twin.
            </EmptyNote>
          ) : (
            <div className="mt-4 max-h-[560px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ color: "var(--ink-faint)" }}>
                    <th className="pb-2 text-left font-semibold">Date</th>
                    <th className="pb-2 text-right font-semibold">HR</th>
                    <th className="pb-2 text-right font-semibold">Sleep</th>
                    <th className="pb-2 text-right font-semibold">Water</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {readings.map((reading) => (
                    <tr key={reading.date} style={{ borderTop: "1px solid var(--border)" }}>
                      <td className="num py-2.5">
                        {new Date(reading.date).toLocaleDateString("en-IN", {
                          day: "numeric", month: "short",
                        })}
                      </td>
                      <td className="num py-2.5 text-right">{reading.heartRate || "—"}</td>
                      <td className="num py-2.5 text-right">{reading.sleepHours || "—"}</td>
                      <td className="num py-2.5 text-right">{reading.hydrationMl || "—"}</td>
                      <td className="py-2.5 text-right">
                        <button
                          type="button"
                          onClick={() => handleDelete(reading.date)}
                          aria-label={`Delete reading for ${reading.date}`}
                          style={{ color: "var(--ink-faint)" }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
