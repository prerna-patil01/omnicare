import { useCallback, useEffect, useState } from "react";
import { MapPin, Search, Star, Video } from "lucide-react";
import { toast } from "sonner";
import * as market from "@/services/marketplaceService";
import {
  Avatar, Badge, Button, Card, EmptyNote, ErrorNote, Eyebrow, PageHeading, PageSkeleton, rupees,
} from "@/components/ui";

const SORTS = [
  { value: "rating", label: "Highest rated" },
  { value: "fee", label: "Lowest fee" },
  { value: "distance", label: "Nearest" },
  { value: "experience", label: "Most experienced" },
];

export default function FindDoctors() {
  const [doctors, setDoctors] = useState([]);
  const [specialties, setSpecialties] = useState(["All"]);
  const [query, setQuery] = useState("");
  const [specialty, setSpecialty] = useState("All");
  const [sort, setSort] = useState("rating");
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setError("");
    market
      .fetchDoctors({ q: query, specialty, sort })
      .then((data) => {
        setDoctors(data.doctors);
        setSpecialties(data.specialties);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [query, specialty, sort]);

  // Debounce so typing doesn't fire a request per keystroke.
  useEffect(() => {
    const id = setTimeout(load, 220);
    return () => clearTimeout(id);
  }, [load]);

  async function handleBook(doctor, mode) {
    setBooking(`${doctor.id}:${mode}`);
    try {
      const { appointment } = await market.bookAppointment(doctor.id, mode);
      toast.success(`Booked with ${doctor.name}`, {
        description: new Date(appointment.scheduledFor).toLocaleString("en-IN", {
          weekday: "long", hour: "numeric", minute: "2-digit",
        }),
      });
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBooking(null);
    }
  }

  return (
    <div>
      <PageHeading
        eyebrow="Marketplace"
        title="Find doctors"
        subtitle="Verified specialists near you, with live consultation fees and next available slots."
      />

      <div className="mb-6 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[240px] flex-1">
            <Search
              size={16}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2"
              style={{ color: "var(--ink-faint)" }}
              aria-hidden="true"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, specialty, or hospital"
              aria-label="Search doctors"
              className="w-full rounded-full py-2.5 pl-11 pr-4 text-sm outline-none"
              style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
            />
          </div>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            aria-label="Sort doctors"
            className="rounded-full px-4 py-2.5 text-sm outline-none"
            style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
          >
            {SORTS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap gap-2">
          {specialties.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setSpecialty(item)}
              className="rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors"
              style={{
                backgroundColor: item === specialty ? "var(--primary)" : "var(--surface-2)",
                color: item === specialty ? "var(--primary-fg)" : "var(--ink-muted)",
                border: "1px solid var(--border)",
              }}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <PageSkeleton rows={4} />
      ) : error ? (
        <ErrorNote message={error} onRetry={load} />
      ) : doctors.length === 0 ? (
        <EmptyNote>No doctors match that search. Try a different specialty.</EmptyNote>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {doctors.map((doctor) => (
            <Card key={doctor.id} className="flex flex-col p-5 transition-shadow hover:shadow-[var(--shadow-lift)]">
              <div className="flex items-start gap-3">
                <Avatar name={doctor.name.replace("Dr. ", "")} size={46} />
                <div className="min-w-0">
                  <h3 className="truncate text-lg font-bold">{doctor.name}</h3>
                  <p className="text-sm" style={{ color: "var(--primary)" }}>
                    {doctor.specialty}
                  </p>
                </div>
              </div>

              <p className="mt-3 text-sm" style={{ color: "var(--ink-muted)" }}>
                {doctor.hospital}
              </p>

              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm">
                <span className="num flex items-center gap-1" style={{ color: "var(--amber)" }}>
                  <Star size={13} fill="currentColor" aria-hidden="true" /> {doctor.rating}
                  <span style={{ color: "var(--ink-faint)" }}>({doctor.reviews})</span>
                </span>
                <span className="num flex items-center gap-1" style={{ color: "var(--ink-muted)" }}>
                  <MapPin size={13} aria-hidden="true" /> {doctor.distanceKm} km
                </span>
                <span className="num font-bold">{rupees(doctor.fee)}</span>
              </div>

              <div className="mt-3">
                <Badge tone="sage">Next: {doctor.nextSlot}</Badge>
              </div>

              <div className="mt-5 flex gap-2 pt-1" style={{ marginTop: "auto" }}>
                <Button
                  className="flex-1"
                  size="sm"
                  disabled={booking === `${doctor.id}:in_person`}
                  onClick={() => handleBook(doctor, "in_person")}
                >
                  {booking === `${doctor.id}:in_person` ? "Booking…" : "Book"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  disabled={!doctor.supportsVideo || booking === `${doctor.id}:video`}
                  onClick={() => handleBook(doctor, "video")}
                >
                  <Video size={14} /> Video
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
