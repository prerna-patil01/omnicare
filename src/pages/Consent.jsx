import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import * as health from "@/services/healthService";
import { Card, ErrorNote, Eyebrow, PageHeading, PageSkeleton } from "@/components/ui";

export default function Consent() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    health
      .fetchConsent()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function handleToggle(scope) {
    setBusy(scope.key);
    try {
      // The server returns the whole set, so the summary panel and every switch
      // stay consistent without a second fetch.
      setData(await health.setConsentScope(scope.key, !scope.granted));
      toast.success(scope.granted ? `${scope.title} revoked` : `${scope.title} granted`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <PageSkeleton rows={3} />;
  if (error) return <ErrorNote message={error} onRetry={load} />;
  if (!data) return null;

  return (
    <div>
      <PageHeading
        eyebrow="Privacy"
        title="Consent & privacy"
        subtitle="Omni can only read what you allow. Revoking a scope takes effect on the next question you ask — nothing is cached behind your back."
      />

      <Card
        className="mb-6 flex flex-wrap items-center justify-between gap-4 p-6"
        style={{ backgroundColor: "var(--primary-wash)", borderColor: "var(--primary)" }}
      >
        <div>
          <Eyebrow>Currently shared</Eyebrow>
          <p className="num mt-1 text-3xl font-bold" style={{ color: "var(--primary)" }}>
            {data.grantedCount} of {data.totalCount}
          </p>
        </div>
        <div className="flex gap-1.5">
          {data.scopes.map((scope) => (
            <span
              key={scope.key}
              title={scope.title}
              className="h-9 w-2.5 rounded-full"
              style={{
                backgroundColor: scope.granted ? "var(--primary)" : "var(--surface-2)",
                border: "1px solid var(--border)",
              }}
            />
          ))}
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {data.scopes.map((scope) => (
          <Card key={scope.key} className="flex items-start justify-between gap-5 p-6">
            <div className="min-w-0">
              <h3 className="text-lg font-bold">{scope.title}</h3>
              <p className="mt-1.5 text-sm" style={{ color: "var(--ink-muted)" }}>
                {scope.description}
              </p>
            </div>

            <button
              type="button"
              role="switch"
              aria-checked={scope.granted}
              aria-label={`${scope.granted ? "Revoke" : "Grant"} ${scope.title}`}
              disabled={busy === scope.key}
              onClick={() => handleToggle(scope)}
              className="relative mt-1 h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-60"
              style={{
                backgroundColor: scope.granted ? "var(--sage)" : "var(--surface-2)",
                border: "1px solid var(--border-strong)",
              }}
            >
              <span
                className="absolute top-1/2 h-5 w-5 -translate-y-1/2 rounded-full shadow-sm transition-all"
                style={{
                  left: scope.granted ? "calc(100% - 1.4rem)" : "0.15rem",
                  backgroundColor: "var(--surface)",
                }}
              />
            </button>
          </Card>
        ))}
      </div>

      <p className="mt-8 max-w-2xl text-sm" style={{ color: "var(--ink-faint)" }}>
        Consent is enforced at the data boundary, not in the interface — when a scope is off, the
        records behind it are never loaded into Omni's context in the first place, and the
        specialists that depend on them abstain rather than guess.
      </p>
    </div>
  );
}
