import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import * as health from "@/services/healthService";
import {
  Badge, Button, Card, EmptyNote, ErrorNote, Eyebrow, PageHeading, PageSkeleton, statusTone,
} from "@/components/ui";

// Must match BIOMARKER_RANGES on the server.
const MARKERS = [
  "Haemoglobin", "Fasting glucose", "Total cholesterol", "HDL",
  "Triglycerides", "Serum creatinine", "Vitamin D", "TSH",
];

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const inputRef = useRef(null);

  const load = useCallback(() => {
    setError("");
    health
      .fetchReports()
      .then((data) => setReports(data.reports))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function handleFiles(files) {
    const file = files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const { report } = await health.uploadReport(file);
      setReports((prev) => [report, ...prev]);
      if (report.biomarkers.length) {
        toast.success("Report read", {
          description: `${report.biomarkers.length} values found in the file.`,
        });
      } else {
        toast("Nothing could be read automatically", {
          description: "Enter the values from the report yourself — nothing is guessed for you.",
        });
      }
    } catch (err) {
      if (err.code === "consent_required") {
        toast.error("Report analysis is off", {
          description: "Turn on 'Report image analysis' in Consent & Privacy.",
        });
      } else {
        toast.error(err.message);
      }
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    try {
      await health.deleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
      toast.success("Report deleted");
    } catch (err) {
      toast.error(err.message);
    }
  }

  return (
    <div>
      <PageHeading
        eyebrow="Your records"
        title="Reports"
        subtitle="Upload a lab report and Omni extracts the biomarkers, flags what's outside range, and tells you what it means."
      />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        className="flex cursor-pointer flex-col items-center justify-center rounded-3xl px-6 py-14 text-center transition-colors"
        style={{
          border: `2px dashed ${dragging ? "var(--accent)" : "var(--border-strong)"}`,
          backgroundColor: dragging ? "var(--accent-wash)" : "var(--surface)",
        }}
      >
        <span
          className="flex h-14 w-14 items-center justify-center rounded-2xl"
          style={{ backgroundColor: "var(--primary-wash)", color: "var(--primary)" }}
        >
          <Upload size={24} aria-hidden="true" />
        </span>
        <p className="mt-4 text-lg font-semibold">
          {uploading ? "Analysing your report…" : "Drop a report here, or click to browse"}
        </p>
        <p className="mt-1.5 text-sm" style={{ color: "var(--ink-muted)" }}>
          PDF, PNG, JPEG, or text · up to 10 MB
        </p>
        <input
          ref={inputRef}
          type="file"
          hidden
          accept=".pdf,.png,.jpg,.jpeg,.webp,.txt"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div className="mt-8">
        {loading ? (
          <PageSkeleton rows={2} />
        ) : error ? (
          <ErrorNote message={error} onRetry={load} />
        ) : reports.length === 0 ? (
          <EmptyNote>No reports uploaded yet.</EmptyNote>
        ) : (
          <div className="flex flex-col gap-5">
            {reports.map((report) => (
              <Card key={report.id} className="p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <span
                      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
                      style={{ backgroundColor: "var(--surface-2)", color: "var(--ink-muted)" }}
                    >
                      <FileText size={20} aria-hidden="true" />
                    </span>
                    <div>
                      <h3 className="font-bold">{report.filename}</h3>
                      <p className="num text-sm" style={{ color: "var(--ink-faint)" }}>
                        {(report.sizeBytes / 1024).toFixed(0)} KB ·{" "}
                        {new Date(report.uploadedAt).toLocaleDateString("en-IN", {
                          day: "numeric", month: "short", year: "numeric",
                        })}
                      </p>
                      {report.extraction && (
                        <p className="mt-1 text-xs" style={{ color: "var(--ink-faint)" }}>
                          {report.extraction.status === "completed"
                            ? `Extraction complete · ${report.extraction.pageCount} page${report.extraction.pageCount === 1 ? "" : "s"} processed`
                            : report.extraction.status === "needs_ocr"
                              ? "Extraction requires OCR"
                              : report.extraction.status === "failed"
                                ? `Extraction failed · ${report.extraction.error}`
                                : "Extracting report…"}
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(report.id)}
                    aria-label={`Delete ${report.filename}`}
                    className="rounded-lg p-2"
                    style={{ color: "var(--ink-faint)" }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <Eyebrow className="mt-6">Biomarkers</Eyebrow>
                {report.biomarkers.length === 0 && (
                  <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
                    No values could be read out of this file. Automatic extraction only works on
                    text reports right now — add the values below and they will be flagged against
                    reference ranges. Nothing is filled in for you.
                  </p>
                )}
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full min-w-[520px] text-sm">
                    <thead>
                      <tr style={{ color: "var(--ink-faint)" }}>
                        <th className="pb-2 text-left font-semibold">Marker</th>
                        <th className="pb-2 text-right font-semibold">Value</th>
                        <th className="pb-2 text-right font-semibold">Reference</th>
                        <th className="pb-2 text-right font-semibold">Flag</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.biomarkers.map((marker) => (
                        <tr key={marker.id} style={{ borderTop: "1px solid var(--border)" }}>
                          <td className="py-2.5">{marker.label}</td>
                          <td className="num py-2.5 text-right font-semibold">
                            {marker.value} {marker.unit}
                          </td>
                          <td className="num py-2.5 text-right" style={{ color: "var(--ink-faint)" }}>
                            {marker.referenceRange}
                          </td>
                          <td className="py-2.5 text-right">
                            <span className="inline-flex items-center gap-1.5">
                              {marker.source === "manual" && (
                                <span className="text-xs" style={{ color: "var(--ink-faint)" }}>
                                  entered
                                </span>
                              )}
                              <Badge tone={statusTone(marker.flag)}>{marker.flag}</Badge>
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <BiomarkerEntry
                  reportId={report.id}
                  onSaved={(updated) =>
                    setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
                  }
                />

                {report.observation && (
                  <div className="mt-5 rounded-2xl p-4" style={{ backgroundColor: "var(--surface-2)" }}>
                    <Eyebrow>Omni's observation</Eyebrow>
                    <p className="mt-1.5 text-sm">{report.observation}</p>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function BiomarkerEntry({ reportId, onSaved }) {
  const [label, setLabel] = useState(MARKERS[0]);
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleAdd(event) {
    event.preventDefault();
    if (!value.trim()) return;
    setSaving(true);
    try {
      const { report } = await health.addBiomarker(reportId, label, value);
      onSaved(report);
      setValue("");
      toast.success(`${label} recorded`);
    } catch (err) {
      toast.error(err.errors?.value || err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleAdd} className="mt-4 flex flex-wrap items-end gap-2">
      <div className="min-w-[170px] flex-1">
        <label htmlFor={`marker-${reportId}`} className="label-eyebrow">
          Add a value from the report
        </label>
        <select
          id={`marker-${reportId}`}
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="mt-1.5 w-full rounded-xl px-3.5 py-2.5 text-sm outline-none"
          style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
        >
          {MARKERS.map((marker) => (
            <option key={marker} value={marker}>
              {marker}
            </option>
          ))}
        </select>
      </div>
      <input
        type="number"
        step="0.1"
        inputMode="decimal"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Value"
        aria-label={`${label} value`}
        className="w-28 rounded-xl px-3.5 py-2.5 text-sm outline-none"
        style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
      />
      <Button type="submit" size="sm" disabled={saving || !value.trim()}>
        {saving ? "Saving…" : "Add"}
      </Button>
    </form>
  );
}
