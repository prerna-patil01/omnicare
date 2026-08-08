/**
 * One labelled input with its inline error. Shared by the auth forms so field
 * errors coming back from Flask render identically everywhere.
 */
export default function FormField({
  id,
  label,
  type = "text",
  value,
  onChange,
  error,
  autoComplete,
  placeholder,
  required = false,
  hint,
}) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="label-eyebrow">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        placeholder={placeholder}
        required={required}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={describedBy}
        className="rounded-xl px-3.5 py-2.5 outline-none transition-colors"
        style={{
          backgroundColor: "var(--surface-2)",
          border: `1px solid ${error ? "var(--rose)" : "var(--border)"}`,
          color: "var(--ink)",
        }}
      />
      {error ? (
        <p id={`${id}-error`} className="text-sm" style={{ color: "var(--rose)" }}>
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-sm" style={{ color: "var(--ink-faint)" }}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
