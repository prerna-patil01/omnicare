import { useCallback, useEffect, useState } from "react";
import { Calendar, Car, MapPin, Video } from "lucide-react";
import { toast } from "sonner";
import * as market from "@/services/marketplaceService";
import {
  Badge, Button, Card, EmptyNote, ErrorNote, Eyebrow, PageHeading, PageSkeleton, rupees,
} from "@/components/ui";

const TABS = [
  { key: "upcoming", label: "Upcoming" },
  { key: "past", label: "Past" },
];

export default function Appointments() {
  const [data, setData] = useState({ upcoming: [], past: [] });
  const [tab, setTab] = useState("upcoming");
  const [rides, setRides] = useState({});     // appointmentId -> ride options
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setError("");
    market
      .fetchAppointments()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function handleCancel(id) {
    setBusy(id);
    try {
      await market.cancelAppointment(id);
      toast.success("Appointment cancelled");
      load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(null);
    }
  }

  async function handleRides(id) {
    if (rides[id]) {
      setRides((prev) => ({ ...prev, [id]: null }));
      return;
    }
    setBusy(id);
    try {
      const options = await market.fetchRideOptions(id);
      setRides((prev) => ({ ...prev, [id]: options }));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(null);
    }
  }

  const list = data[tab] || [];

  return (
    <div>
      <PageHeading
        eyebrow="Your care"
        title="Appointments"
        subtitle="Everything you've booked, and how to get there."
      />

      <div className="mb-6 flex gap-2">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            className="rounded-full px-4 py-2 text-sm font-semibold transition-colors"
            style={{
              backgroundColor: tab === item.key ? "var(--primary)" : "var(--surface-2)",
              color: tab === item.key ? "var(--primary-fg)" : "var(--ink-muted)",
              border: "1px solid var(--border)",
            }}
          >
            {item.label}
            <span className="num ml-2 opacity-70">{(data[item.key] || []).length}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <PageSkeleton rows={2} />
      ) : error ? (
        <ErrorNote message={error} onRetry={load} />
      ) : list.length === 0 ? (
        <EmptyNote>
          {tab === "upcoming"
            ? "No upcoming appointments. Book one from Find Doctors."
            : "Nothing in your history yet."}
        </EmptyNote>
      ) : (
        <div className="flex flex-col gap-4">
          {list.map((appt) => (
            <Card key={appt.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-[220px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-lg font-bold">{appt.doctor?.name}</h3>
                    <Badge tone={appt.status === "cancelled" ? "rose" : "sage"}>{appt.status}</Badge>
                    {appt.mode === "video" && (
                      <Badge tone="primary">
                        <Video size={11} /> Video
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-sm" style={{ color: "var(--primary)" }}>
                    {appt.doctor?.specialty}
                  </p>
                  <p className="mt-2 flex items-center gap-1.5 text-sm" style={{ color: "var(--ink-muted)" }}>
                    <MapPin size={13} aria-hidden="true" /> {appt.location}
                  </p>
                  <p className="num mt-1 flex items-center gap-1.5 text-sm" style={{ color: "var(--ink-muted)" }}>
                    <Calendar size={13} aria-hidden="true" />
                    {new Date(appt.scheduledFor).toLocaleString("en-IN", {
                      weekday: "short", day: "numeric", month: "short",
                      hour: "numeric", minute: "2-digit",
                    })}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {tab === "upcoming" && appt.status !== "cancelled" && (
                    <>
                      {appt.mode !== "video" && appt.location && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy === appt.id}
                          onClick={() => handleRides(appt.id)}
                        >
                          <Car size={14} /> {rides[appt.id] ? "Hide rides" : "Book a ride"}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={busy === appt.id}
                        style={{ color: "var(--rose)" }}
                        onClick={() => handleCancel(appt.id)}
                      >
                        Cancel
                      </Button>
                    </>
                  )}
                  {tab === "past" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        toast("Rebooking", { description: "Pick a slot from Find Doctors." })
                      }
                    >
                      Book again
                    </Button>
                  )}
                </div>
              </div>

              {rides[appt.id] && (
                <div className="mt-5 rise" style={{ borderTop: "1px solid var(--border)", paddingTop: "1.25rem" }}>
                  <Eyebrow>
                    Rides to {rides[appt.id].destination} · {rides[appt.id].distanceKm} km
                  </Eyebrow>
                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    {rides[appt.id].options.map((option) => (
                      <button
                        key={option.key}
                        type="button"
                        onClick={() =>
                          toast.success(`${option.label} booked`, {
                            description: `Arriving in ${option.eta} · ${rupees(option.fare)}`,
                          })
                        }
                        className="rounded-2xl p-4 text-left transition-shadow hover:shadow-[var(--shadow-soft)]"
                        style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold">{option.label}</span>
                          <span className="num font-bold">{rupees(option.fare)}</span>
                        </div>
                        <p className="num mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
                          {option.eta} away · {option.seats} seats
                        </p>
                        {option.note && (
                          <p className="mt-1.5 text-xs" style={{ color: "var(--sage)" }}>
                            {option.note}
                          </p>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
