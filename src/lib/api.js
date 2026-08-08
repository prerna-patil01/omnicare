import axios from "axios";

/**
 * Single Axios instance for the whole app. Every call to Flask goes through
 * here so token attachment, refresh, and error normalisation exist in exactly
 * one place.
 */

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000/api";

const ACCESS_TOKEN_KEY = "omnicare.accessToken";
const REFRESH_TOKEN_KEY = "omnicare.refreshToken";

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  set: ({ accessToken, refreshToken }) => {
    if (accessToken) localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = config._useRefreshToken
    ? tokenStore.getRefresh()
    : tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/**
 * Turn any failure — HTTP error, network drop, timeout — into a consistent
 * shape. Without this, a Flask 400 and a connection-refused surface as
 * completely different objects and every call site re-invents the check.
 */
export class ApiError extends Error {
  constructor(message, { status = null, errors = null, code = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
    this.code = code;
  }
}

function toApiError(error) {
  if (error.response) {
    const { status, data } = error.response;
    return new ApiError(
      data?.message || `Request failed (${status}).`,
      { status, errors: data?.errors || null, code: data?.code || null },
    );
  }
  if (error.code === "ECONNABORTED") {
    return new ApiError("The server took too long to respond.", { code: "timeout" });
  }
  // No response at all: Flask is down, or CORS blocked the request before it
  // ever reached the handler.
  return new ApiError(
    "Cannot reach the OmniCare server. Check that the backend is running.",
    { code: "network" },
  );
}

// --- refresh handling -------------------------------------------------------
// A burst of parallel 401s must trigger exactly one refresh, not one per call.
let refreshPromise = null;
let onSessionExpired = () => {};

export function setSessionExpiredHandler(fn) {
  onSessionExpired = fn;
}

async function refreshAccessToken() {
  if (!tokenStore.getRefresh()) throw new ApiError("No refresh token.", { status: 401 });
  if (!refreshPromise) {
    refreshPromise = api
      .post("/auth/refresh", null, { _useRefreshToken: true, _skipRetry: true })
      .then((res) => {
        const accessToken = res.data?.data?.accessToken;
        tokenStore.set({ accessToken });
        return accessToken;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;
    const code = error.response?.data?.code;

    const isExpiredAccessToken =
      status === 401 && code === "token_expired" && !original._skipRetry && !original._retried;

    if (isExpiredAccessToken) {
      original._retried = true;
      try {
        await refreshAccessToken();
        return api(original);
      } catch {
        tokenStore.clear();
        onSessionExpired();
        return Promise.reject(
          new ApiError("Your session has expired. Please sign in again.", {
            status: 401,
            code: "session_expired",
          }),
        );
      }
    }

    return Promise.reject(toApiError(error));
  },
);

/** Unwraps the {"data": ...} envelope the Flask API always returns. */
export async function unwrap(promise) {
  const response = await promise;
  return response.data?.data;
}
