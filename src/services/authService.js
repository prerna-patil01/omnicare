import { api, unwrap, tokenStore } from "@/lib/api";

/**
 * Auth calls against Flask. Components never touch `api` directly — they call
 * these, so the request/response contract with the backend lives in one file.
 */

export async function register({ fullName, email, password, phone }) {
  const data = await unwrap(
    api.post("/auth/register", { fullName, email, password, phone }),
  );
  tokenStore.set(data);
  return data.user;
}

export async function login({ email, password }) {
  const data = await unwrap(api.post("/auth/login", { email, password }));
  tokenStore.set(data);
  return data.user;
}

export async function fetchCurrentUser() {
  const data = await unwrap(api.get("/auth/me"));
  return data.user;
}

export function logout() {
  // JWTs are stateless, so signing out is a client-side token discard. A
  // server-side denylist is the follow-up if we need revocation before expiry.
  tokenStore.clear();
}
