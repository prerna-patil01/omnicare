import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/api";
import FormField from "@/components/FormField";

export default function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [form, setForm] = useState({ email: "", password: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Where ProtectedRoute intercepted them, if anywhere.
  const redirectTo = location.state?.from?.pathname || "/dashboard";

  const update = (key) => (value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => (prev[key] ? { ...prev, [key]: undefined } : prev));
  };

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setFormError("");
    setFieldErrors({});

    try {
      await signIn(form);
      navigate(redirectTo, { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.errors) setFieldErrors(error.errors);
        setFormError(error.message);
      } else {
        setFormError("Unable to sign in. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <div className="card-lux p-8">
        <p className="label-eyebrow">OmniCare</p>
        <h1 className="mt-2 text-3xl">Welcome back</h1>

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
            id="password"
            label="Password"
            type="password"
            value={form.password}
            onChange={update("password")}
            error={fieldErrors.password}
            autoComplete="current-password"
            required
          />

          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-xl px-4 py-3 font-semibold transition-opacity disabled:opacity-60"
            style={{ backgroundColor: "var(--primary)", color: "var(--primary-fg)" }}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-sm" style={{ color: "var(--ink-muted)" }}>
          New to OmniCare?{" "}
          <Link to="/register" style={{ color: "var(--primary)", fontWeight: 600 }}>
            Create an account
          </Link>
        </p>
      </div>
    </main>
  );
}
