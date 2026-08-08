import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import * as authService from "@/services/authService";
import * as health from "@/services/healthService";
import {
  Avatar, Button, Card, ErrorNote, Eyebrow, PageHeading, PageSkeleton,
} from "@/components/ui";
import FormField from "@/components/FormField";

export default function Profile() {
  const { signOut, setUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ fullName: "", phone: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    authService
      .fetchCurrentUser()
      .then((user) => {
        if (cancelled) return;
        setProfile(user);
        setForm({ fullName: user.fullName, phone: user.phone || "" });
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const update = (key) => (value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => (prev[key] ? { ...prev, [key]: undefined } : prev));
  };

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setFieldErrors({});
    try {
      const { user } = await health.updateProfile(form);
      setProfile(user);
      setUser?.(user);
      toast.success("Profile updated");
    } catch (err) {
      if (err.errors) setFieldErrors(err.errors);
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <PageSkeleton rows={2} />;
  if (error) return <ErrorNote message={error} />;
  if (!profile) return null;

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeading eyebrow="Account" title="Your profile" />

      <Card className="mb-5 flex flex-wrap items-center gap-5 p-6">
        <Avatar name={profile.fullName} size={64} />
        <div className="min-w-0">
          <h2 className="truncate text-xl font-bold">{profile.fullName}</h2>
          <p className="truncate text-sm" style={{ color: "var(--ink-muted)" }}>
            {profile.email}
          </p>
          <p className="num mt-1 text-xs" style={{ color: "var(--ink-faint)" }}>
            Member since{" "}
            {new Date(profile.createdAt).toLocaleDateString("en-IN", {
              day: "numeric", month: "long", year: "numeric",
            })}
          </p>
        </div>
      </Card>

      <Card className="p-6">
        <Eyebrow>Edit details</Eyebrow>
        <form onSubmit={handleSave} className="mt-4 flex flex-col gap-4" noValidate>
          <FormField
            id="fullName"
            label="Full name"
            value={form.fullName}
            onChange={update("fullName")}
            error={fieldErrors.fullName}
            autoComplete="name"
          />
          <FormField
            id="phone"
            label="Phone"
            type="tel"
            value={form.phone}
            onChange={update("phone")}
            error={fieldErrors.phone}
            autoComplete="tel"
            hint="Used for appointment reminders and delivery updates."
          />
          <div>
            <Eyebrow>Email</Eyebrow>
            <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
              {profile.email} — email changes need verification, which isn't built yet.
            </p>
          </div>

          <Button type="submit" disabled={saving} className="mt-2 self-start">
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </form>
      </Card>

      <Card className="mt-5 flex flex-wrap items-center justify-between gap-4 p-6">
        <div>
          <h3 className="font-bold">Consent & privacy</h3>
          <p className="text-sm" style={{ color: "var(--ink-muted)" }}>
            Control exactly what Omni can read.
          </p>
        </div>
        <Link to="/consent">
          <Button variant="outline">Manage</Button>
        </Link>
      </Card>

      <Button variant="ghost" className="mt-5" style={{ color: "var(--rose)" }} onClick={signOut}>
        Sign out
      </Button>
    </div>
  );
}
