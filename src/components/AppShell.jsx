import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, Menu, Moon, Search, Sun, X } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { resolveTheme, toggleTheme } from "@/lib/theme";
import { Avatar, Badge, Button } from "@/components/ui";

const SECTIONS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/log", label: "Log Reading" },
  { to: "/omni", label: "Ask Omni" },
  { to: "/twin", label: "Digital Twin" },
  { to: "/doctors", label: "Find Doctors" },
  { to: "/care", label: "Care Services" },
  { to: "/appointments", label: "Appointments" },
  { to: "/pharmacy", label: "Pharmacy" },
  { to: "/reports", label: "Reports" },
  { to: "/insights", label: "Health Insights" },
];

// Search maps a free-text query onto a section. Kept in the shell because it
// is navigation, not data — nothing here fabricates results.
const SEARCH_MAP = [
  { to: "/doctors", terms: ["doctor", "cardio", "specialist", "consult", "physician", "book"] },
  { to: "/pharmacy", terms: ["medicine", "pharmacy", "tablet", "drug", "order", "cart"] },
  { to: "/reports", terms: ["report", "lab", "blood", "biomarker", "upload", "scan"] },
  { to: "/twin", terms: ["twin", "risk", "prone", "model", "biological age"] },
  { to: "/omni", terms: ["ask", "omni", "symptom", "why", "pain", "feel"] },
  { to: "/appointments", terms: ["appointment", "booking", "ride", "cancel", "visit"] },
  { to: "/care", terms: ["nurse", "asha", "physio", "dietician", "home", "sample"] },
  { to: "/insights", terms: ["sleep", "stress", "hydration", "trend", "insight", "air"] },
  { to: "/log", terms: ["log", "enter", "record", "add reading", "vitals", "heart rate"] },
  { to: "/consent", terms: ["consent", "privacy", "permission", "data", "share"] },
];

export default function AppShell() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [dark, setDark] = useState(() => resolveTheme() === "dark");
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");
  const searchRef = useRef(null);

  // Close the mobile sheet on any successful navigation.
  useEffect(() => {
    if (!menuOpen) return;
    const close = () => setMenuOpen(false);
    window.addEventListener("popstate", close);
    return () => window.removeEventListener("popstate", close);
  }, [menuOpen]);

  function handleSearch(event) {
    event.preventDefault();
    const q = query.trim().toLowerCase();
    if (!q) return;
    const hit = SEARCH_MAP.find((entry) => entry.terms.some((t) => q.includes(t)));
    if (hit) {
      navigate(hit.to);
      setQuery("");
    } else {
      toast("Nothing matched that", {
        description: "Try a section name — doctors, pharmacy, reports, insights.",
      });
    }
  }

  return (
    <div className="min-h-screen">
      <header
        className="sticky top-0 z-40 backdrop-blur"
        style={{
          backgroundColor: "color-mix(in oklab, var(--bg) 88%, transparent)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 sm:px-6">
          <NavLink to="/dashboard" className="flex shrink-0 items-center gap-2">
            <span className="text-xl font-bold tracking-tight">OmniCare</span>
            <Badge tone="accent">AI</Badge>
          </NavLink>

          <form onSubmit={handleSearch} className="relative mx-auto hidden w-full max-w-md md:block">
            <Search
              size={16}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2"
              style={{ color: "var(--ink-faint)" }}
              aria-hidden="true"
            />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search doctors, medicines, reports…"
              aria-label="Search OmniCare"
              className="w-full rounded-full py-2 pl-11 pr-4 text-sm outline-none"
              style={{
                backgroundColor: "var(--surface-2)",
                border: "1px solid var(--border)",
                boxShadow: "inset 0 1px 3px rgb(0 0 0 / 0.06)",
              }}
            />
          </form>

          <div className="ml-auto flex items-center gap-1.5 md:ml-0">
            <IconButton label="Notifications" onClick={() =>
              toast("You're all caught up", { description: "No new alerts right now." })
            }>
              <Bell size={18} />
            </IconButton>

            <IconButton
              label={dark ? "Switch to light theme" : "Switch to dark theme"}
              onClick={() => setDark(toggleTheme() === "dark")}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </IconButton>

            <NavLink to="/profile" aria-label="Your profile" className="mx-1">
              <Avatar name={user?.fullName} size={34} />
            </NavLink>

            <Button
              variant="accent"
              size="sm"
              onClick={() =>
                toast.error("Emergency services", {
                  description:
                    "Call 108 for an ambulance. If you can, have someone stay with you.",
                  duration: 10000,
                })
              }
            >
              SOS
            </Button>

            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              className="ml-1 rounded-full p-2 lg:hidden"
              style={{ border: "1px solid var(--border)" }}
            >
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {/* Desktop section tabs */}
        <nav
          aria-label="Sections"
          className="mx-auto hidden max-w-7xl gap-1 overflow-x-auto px-4 pb-1 sm:px-6 lg:flex"
        >
          {SECTIONS.map((section) => (
            <TabLink key={section.to} to={section.to}>
              {section.label}
            </TabLink>
          ))}
        </nav>
      </header>

      {/* Mobile bottom-sheet menu */}
      {menuOpen && (
        <div
          className="fixed inset-0 z-50 flex flex-col justify-end lg:hidden"
          style={{ backgroundColor: "rgb(0 0 0 / 0.42)" }}
          onClick={() => setMenuOpen(false)}
        >
          <nav
            aria-label="Sections"
            onClick={(e) => e.stopPropagation()}
            className="rise max-h-[80vh] overflow-y-auto rounded-t-3xl p-5"
            style={{ backgroundColor: "var(--surface)", borderTop: "1px solid var(--border)" }}
          >
            <div className="mx-auto mb-4 h-1 w-10 rounded-full" style={{ backgroundColor: "var(--border-strong)" }} />
            <div className="flex flex-col gap-1">
              {[...SECTIONS, { to: "/consent", label: "Consent & Privacy" }, { to: "/profile", label: "Profile" }].map(
                (section) => (
                  <NavLink
                    key={section.to}
                    to={section.to}
                    onClick={() => setMenuOpen(false)}
                    className="rounded-2xl px-4 py-3 font-semibold"
                    style={({ isActive }) => ({
                      backgroundColor: isActive ? "var(--primary-wash)" : "transparent",
                      color: isActive ? "var(--primary)" : "var(--ink)",
                    })}
                  >
                    {section.label}
                  </NavLink>
                ),
              )}
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  signOut();
                }}
                className="mt-2 rounded-2xl px-4 py-3 text-left font-semibold"
                style={{ color: "var(--rose)" }}
              >
                Sign out
              </button>
            </div>
          </nav>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>

      <footer
        className="mx-auto max-w-7xl px-4 pb-10 pt-4 text-sm sm:px-6"
        style={{ color: "var(--ink-faint)" }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3" style={{ borderTop: "1px solid var(--border)", paddingTop: "1.25rem" }}>
          <p>OmniCare · consent-first health, built for India.</p>
          <NavLink to="/consent" style={{ color: "var(--primary)", fontWeight: 600 }}>
            Consent &amp; Privacy
          </NavLink>
        </div>
      </footer>
    </div>
  );
}

function IconButton({ label, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="rounded-full p-2 transition-colors"
      style={{ color: "var(--ink-muted)", border: "1px solid transparent" }}
      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--surface-2)")}
      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
    >
      {children}
    </button>
  );
}

function TabLink({ to, children }) {
  return (
    <NavLink
      to={to}
      className="shrink-0 rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors"
      style={({ isActive }) => ({
        backgroundColor: isActive ? "var(--primary-wash)" : "transparent",
        color: isActive ? "var(--primary)" : "var(--ink-muted)",
      })}
    >
      {children}
    </NavLink>
  );
}
