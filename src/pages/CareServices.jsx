import { useCallback, useEffect, useState } from "react";
import { Home } from "lucide-react";
import { toast } from "sonner";
import * as market from "@/services/marketplaceService";
import {
  Avatar, Badge, Button, Card, ErrorNote, Eyebrow, PageHeading, PageSkeleton, rupees,
} from "@/components/ui";

export default function CareServices() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    market
      .fetchCareServices()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const book = (name) =>
    toast.success(`Requested ${name}`, {
      description: "They'll confirm within the hour. You'll get a notification.",
    });

  if (loading) return <PageSkeleton rows={4} />;
  if (error) return <ErrorNote message={error} onRetry={load} />;
  if (!data) return null;

  const { groups, homeSampleCollection: sample } = data;

  return (
    <div>
      <PageHeading
        eyebrow="Marketplace"
        title="Care services"
        subtitle="Trained care workers who come to you — nurses, ASHA workers, physiotherapists, lab technicians, and dieticians."
      />

      <Card
        className="mb-8 flex flex-wrap items-center gap-5 p-6"
        style={{ backgroundColor: "var(--accent-wash)", borderColor: "var(--accent)" }}
      >
        <span
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
          style={{ backgroundColor: "var(--accent)", color: "var(--accent-fg)" }}
        >
          <Home size={22} aria-hidden="true" />
        </span>
        <div className="min-w-[240px] flex-1">
          <h2 className="text-lg font-bold">{sample.title}</h2>
          <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
            {sample.description}
          </p>
          <p className="mt-2 text-sm font-semibold" style={{ color: "var(--accent)" }}>
            {sample.eta}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="num text-2xl font-bold">{rupees(sample.price)}</span>
          <Button variant="accent" onClick={() => book("home sample collection")}>
            Book
          </Button>
        </div>
      </Card>

      <div className="flex flex-col gap-8">
        {groups.map((group) => (
          <section key={group.key}>
            <div className="mb-3 flex items-baseline gap-3">
              <h2 className="text-xl">{group.label}</h2>
              <span className="num text-sm" style={{ color: "var(--ink-faint)" }}>
                {group.workers.length} available
              </span>
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              {group.workers.map((worker) => (
                <Card key={worker.id} className="flex flex-wrap items-center gap-4 p-4">
                  <Avatar name={worker.name} size={44} />
                  <div className="min-w-[160px] flex-1">
                    <h3 className="font-bold">{worker.name}</h3>
                    <p className="text-sm" style={{ color: "var(--primary)" }}>
                      {worker.role}
                    </p>
                    <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
                      {worker.experienceNote}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <Badge tone={worker.availability.includes("today") ? "sage" : "amber"}>
                      {worker.availability}
                    </Badge>
                    <p className="num text-sm font-bold">
                      {rupees(worker.ratePerHour)}
                      <span className="font-normal" style={{ color: "var(--ink-faint)" }}>
                        /hr
                      </span>
                    </p>
                    <Button size="sm" onClick={() => book(worker.name)}>
                      Book
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
