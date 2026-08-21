import { api, unwrap } from "@/lib/api";

/** Dashboard, digital twin, insights, reports, and consent. */

export const fetchDashboard = () => unwrap(api.get("/dashboard"));

export const toggleSavedFinding = (findingId) =>
  unwrap(api.post(`/dashboard/finding/${findingId}/save`));

export const fetchTwin = () => unwrap(api.get("/twin"));

export const fetchInsights = (days = 30) =>
  unwrap(api.get("/insights", { params: { days } }));

export const fetchReports = () => unwrap(api.get("/reports"));

export function uploadReport(file) {
  const form = new FormData();
  form.append("file", file);
  // Let the browser set the multipart boundary — overriding Content-Type here
  // produces a boundary-less header that Flask cannot parse.
  return unwrap(api.post("/reports", form, { headers: { "Content-Type": undefined } }));
}

export const deleteReport = (reportId) => unwrap(api.delete(`/reports/${reportId}`));

export const fetchReportExtraction = (reportId) =>
  unwrap(api.get(`/reports/${reportId}/extraction`));

export const fetchConsent = () => unwrap(api.get("/consent"));

export const setConsentScope = (key, granted) =>
  unwrap(api.patch(`/consent/${key}`, { granted }));

export const updateProfile = (details) => unwrap(api.patch("/profile", details));

// --- vitals: the only route by which clinical numbers enter the system ------

export const fetchVitals = () => unwrap(api.get("/vitals"));

export const logVitals = (reading) => unwrap(api.post("/vitals", reading));

export const deleteVitals = (date) => unwrap(api.delete(`/vitals/${date}`));

export const addBiomarker = (reportId, label, value) =>
  unwrap(api.post(`/reports/${reportId}/biomarkers`, { label, value }));
