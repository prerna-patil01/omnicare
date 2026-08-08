/**
 * Theme persistence. The inline script in index.html applies the stored theme
 * before first paint; this module is the runtime counterpart that keeps the
 * two in sync. Storage key must match that script.
 */

const STORAGE_KEY = "omnicare.theme";

export function getStoredTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function prefersDark() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme() {
  return getStoredTheme() || (prefersDark() ? "dark" : "light");
}

export function applyTheme(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Private browsing with storage denied — the class is still applied.
  }
}

export function toggleTheme() {
  const next = resolveTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  return next;
}
