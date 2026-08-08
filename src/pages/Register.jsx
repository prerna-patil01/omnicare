import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/api";
import FormField from "@/components/FormField";

const EMPTY = { fullName: "", email: "", password: "", phone: "" };

export default function Register() {
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState(EMPTY);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const update = (key) => (value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    // Clear the field's error as soon as they start correcting it.
    setFieldErrors((prev) => (prev[key] ? { ...prev, [key]: undefined } : prev));
  };

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setFormError("");
    setFieldErrors({});

    try {
      await signUp(form);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        // Flask returns per-field messages for 400/409 — surface them on the
        // inputs rather than collapsing everything into one banner.
        if (error.errors) setFieldErrors(error.errors);
        setFormError(error.message);
      } else {
        setFormError("Unable to create your account. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <div className="card-lux p-8">
        <p className="label-eyebrow">OmniCare</p>
        <h1 className="mt-2 text-3xl">Create your account</h1>
        <p className="mt-2" style={{ color: "var(--ink-muted)" }}>
          Your health identity, consent-first from day one.
        </p>

        {formError && (
          <div
            role="alert"
            className="mt-6 rounded-xl px-4 py-3 text-sm"
            style={{ backgroundColor: "var(--rose-bg)", color: "var(--rose)" }}
          >
            {formError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4" noValidate>
          <FormField
            id="fullName"
            label="Full name"
            value={form.fullName}
            onChange={update("fullName")}
            error={fieldErrors.fullName}
            autoComplete="name"
            required
          />
          <FormField
            id="email"
            label="Email"
            type="email"
            value={form.email}
            onChange={update("email")}
            error={fieldErrors.email}
            autoComplete="email"
            required
          />
          <FormField
            id="phone"
            label="Phone (optional)"
            type="tel"
            value={form.phone}
            onChange={update("phone")}
            error={fieldErrors.phone}
            autoComplete="tel"
          />
          <FormField
            id="password"
            label="Password"
            type="password"
            value={form.password}
            onChange={update("password")}
            error={fieldErrors.password}
            autoComplete="new-password"
            hint="At least 10 characters."
            required
          />

          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-xl px-4 py-3 font-semibold transition-opacity disabled:opacity-60"
            style={{ backgroundColor: "var(--primary)", color: "var(--primary-fg)" }}
          >
            {submitting ? "Creating your account…" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-sm" style={{ color: "var(--ink-muted)" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "var(--primary)", fontWeight: 600 }}>
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
