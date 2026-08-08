import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, initialising } = useAuth();
  const location = useLocation();

  if (initialising) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p style={{ color: "var(--ink-faint)" }}>Loading your account…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // `state.from` lets the login page send them back where they were headed.
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
