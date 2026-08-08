import { clsx } from "clsx";

/**
 * Shared primitives. Every colour resolves through the tokens in global.css,
 * so the dark ground is a token swap rather than a second set of components.
 */

export function Card({ className, children, ...rest }) {
  return (
    <div className={clsx("card-lux", className)} {...rest}>
      {children}
    </div>
  );
}

export function Eyebrow({ children, className, style }) {
  return (
    <p className={clsx("label-eyebrow", className)} style={style}>
      {children}
    </p>
  );
}

const BADGE_TONES = {
  neutral: { backgroundColor: "var(--surface-2)", color: "var(--ink-muted)" },
  sage: { backgroundColor: "var(--sage-bg)", color: "var(--sage)" },
  amber: { backgroundColor: "var(--amber-bg)", color: "var(--amber)" },
  rose: { backgroundColor: "var(--rose-bg)", color: "var(--rose)" },
  primary: { backgroundColor: "var(--primary-wash)", color: "var(--primary)" },
  accent: { backgroundColor: "var(--accent-wash)", color: "var(--accent)" },
};

export function Badge({ tone = "neutral", children, className }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-[0.12em]",
        className,
      )}
      style={BADGE_TONES[tone] || BADGE_TONES.neutral}
    >
      {children}
    </span>
  );
}

const BUTTON_VARIANTS = {
  primary: { backgroundColor: "var(--primary)", color: "var(--primary-fg)", border: "1px solid transparent" },
  accent: { backgroundColor: "var(--accent)", color: "var(--accent-fg)", border: "1px solid transparent" },
  outline: { backgroundColor: "transparent", color: "var(--ink)", border: "1px solid var(--border-strong)" },
  ghost: { backgroundColor: "transparent", color: "var(--ink-muted)", border: "1px solid transparent" },
  onHero: { backgroundColor: "transparent", color: "var(--hero-fg)", border: "1px solid var(--hero-border)" },
};

export function Button({ variant = "primary", size = "md", className, style, ...rest }) {
  return (
    <button
      className={clsx(
        // rounded-full pills, per the design language; press feedback via scale
        "inline-flex items-center justify-center gap-2 rounded-full font-semibold",
        "transition-transform duration-100 active:scale-[0.97]",
        "disabled:cursor-not-allowed disabled:opacity-55 disabled:active:scale-100",
        size === "sm" ? "px-3.5 py-1.5 text-sm" : size === "lg" ? "px-6 py-3" : "px-4 py-2.5 text-[0.95rem]",
        className,
      )}
      style={{ ...BUTTON_VARIANTS[variant], ...style }}
      {...rest}
    />
  );
}

export function Skeleton({ className, style }) {
  return (
    <div
      className={clsx("shimmer rounded-xl", className)}
      style={{ backgroundColor: "var(--surface-2)", ...style }}
      aria-hidden="true"
    />
  );
}

/** Page-level loading state shaped like the cards it replaces. */
export function PageSkeleton({ rows = 3 }) {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-40 w-full" />
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    </div>
  );
}

export function ErrorNote({ message, onRetry }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center justify-between gap-3 rounded-2xl px-5 py-4"
      style={{ backgroundColor: "var(--rose-bg)", color: "var(--rose)" }}
    >
      <span className="text-sm">{message}</span>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} style={{ color: "var(--rose)" }}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function EmptyNote({ children }) {
  return (
    <p className="py-10 text-center text-sm" style={{ color: "var(--ink-faint)" }}>
      {children}
    </p>
  );
}

export function PageHeading({ eyebrow, title, subtitle, children }) {
  return (
    <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
        <h1 className="mt-1.5 text-[2rem]">{title}</h1>
        {subtitle && (
          <p className="mt-1.5 max-w-xl" style={{ color: "var(--ink-muted)" }}>
            {subtitle}
          </p>
        )}
      </div>
      {children}
    </header>
  );
}

/**
 * Renders *italic* segments as the design's signature emphasis. Keeps the
 * emphasis in the data rather than hardcoding which words are italic.
 */
export function Emphasised({ text, className, style }) {
  if (!text) return null;
  return (
    <span className={className} style={style}>
      {text.split(/(\*[^*]+\*)/g).map((part, i) =>
        part.startsWith("*") && part.endsWith("*") && part.length > 2 ? (
          <em key={i} style={{ fontStyle: "italic" }}>
            {part.slice(1, -1)}
          </em>
        ) : (
          part
        ),
      )}
    </span>
  );
}

export function Avatar({ name, size = 36 }) {
  const initials = (name || "?")
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full font-bold"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        backgroundColor: "var(--primary-wash)",
        color: "var(--primary)",
        border: "1px solid var(--border)",
      }}
    >
      {initials}
    </span>
  );
}

/** Status → token mapping used by twin nodes, biomarkers, and risk bands. */
export const statusTone = (status) =>
  ({ normal: "sage", caution: "amber", warning: "rose", high: "rose", low: "amber" })[status] ||
  "neutral";

export const statusColor = (status) =>
  ({
    normal: "var(--sage)",
    caution: "var(--amber)",
    warning: "var(--rose)",
    high: "var(--rose)",
    low: "var(--amber)",
  })[status] || "var(--ink-muted)";

export const rupees = (value) =>
  `₹${Number(value ?? 0).toLocaleString("en-IN")}`;
