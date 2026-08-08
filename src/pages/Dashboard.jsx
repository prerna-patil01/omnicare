import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import * as authService from "@/services/authService";

/**
 * Deliberately re-fetches /auth/me rather than rendering the user object held
 * in context. It proves the authenticated request path works on a cold load,
 * which is the thing that actually breaks when tokens aren't attached.
 */
export default function Dashboard() {
  const { user: cachedUser, signOut } = useAuth();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    authService
      .fetchCurrentUser()
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const shown = profile || cachedUser;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <div className="hero-panel p-8">
        <p className="label-eyebrow" style={{ color: "var(--hero-fg-muted)" }}>
          Signed in
        </p>
        <h1 className="mt-2 text-3xl" style={{ color: "var(--hero-fg)" }}>
          {shown ? shown.fullName : "Loading…"}
        </h1>
        <p className="mt-1" style={{ color: "var(--hero-fg-muted)" }}>
          {shown?.email}
        </p>
      </div>

      <section className="card-lux mt-6 p-8">
        <h2 className="text-xl">Account</h2>

        {loading && (
          <p className="mt-4" style={{ color: "var(--ink-faint)" }}>
            Fetching your profile from the server…
          </p>
        )}

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-xl px-4 py-3 text-sm"
            style={{ backgroundColor: "var(--rose-bg)", color: "var(--rose)" }}
          >
            {error}
          </div>
        )}

        {profile && (
          <dl className="mt-4 flex flex-col gap-3">
            <Row label="Account ID" value={profile.id} mono />
            <Row label="Full name" value={profile.fullName} />
            <Row label="Email" value={profile.email} />
            <Row label="Phone" value={profile.phone || "Not provided"} />
            <Row
              label="Member since"
              value={new Date(profile.createdAt).toLocaleDateString()}
            />
          </dl>
        )}

        <button
          type="button"
          onClick={signOut}
          className="mt-8 rounded-xl px-4 py-2.5 font-semibold"
          style={{
            backgroundColor: "var(--surface-2)",
            color: "var(--ink)",
            border: "1px solid var(--border-strong)",
          }}
        >
          Sign out
        </button>
      </section>
    </main>
  );
}

function Row({ label, value, mono = false }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="label-eyebrow">{label}</dt>
      <dd
        className={mono ? "num text-sm" : "text-sm"}
        style={{ color: "var(--ink)", fontFamily: mono ? "monospace" : undefined }}
      >
        {value}
      </dd>
    </div>
  );
}
