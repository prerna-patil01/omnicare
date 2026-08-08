import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setSessionExpiredHandler, tokenStore } from "@/lib/api";
import * as authService from "@/services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // `initialising` guards the first paint: without it, a refresh on a
  // protected route bounces to /login before /auth/me has had a chance to
  // answer, which looks exactly like being logged out.
  const [initialising, setInitialising] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (!tokenStore.getAccess()) {
        setInitialising(false);
        return;
      }
      try {
        const currentUser = await authService.fetchCurrentUser();
        if (!cancelled) setUser(currentUser);
      } catch {
        // Token is stale or the backend rejected it — start clean.
        tokenStore.clear();
      } finally {
        if (!cancelled) setInitialising(false);
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const signOut = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  // Lets the Axios refresh-failure path clear React state, not just storage.
  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    return () => setSessionExpiredHandler(() => {});
  }, []);

  const signIn = useCallback(async (credentials) => {
    setUser(await authService.login(credentials));
  }, []);

  const signUp = useCallback(async (details) => {
    setUser(await authService.register(details));
  }, []);

  const value = useMemo(
    // setUser lets the profile page push its saved result into the shell
    // (avatar, greeting) without a refetch.
    () => ({ user, setUser, initialising, signIn, signUp, signOut, isAuthenticated: !!user }),
    [user, initialising, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside an <AuthProvider>.");
  return context;
}
