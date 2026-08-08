import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import AppShell from "@/components/AppShell";
import ProtectedRoute from "@/components/ProtectedRoute";
import Appointments from "@/pages/Appointments";
import AskOmni from "@/pages/AskOmni";
import CareServices from "@/pages/CareServices";
import Consent from "@/pages/Consent";
import Dashboard from "@/pages/Dashboard";
import DigitalTwin from "@/pages/DigitalTwin";
import FindDoctors from "@/pages/FindDoctors";
import HealthInsights from "@/pages/HealthInsights";
import Login from "@/pages/Login";
import Pharmacy from "@/pages/Pharmacy";
import Profile from "@/pages/Profile";
import Register from "@/pages/Register";
import Reports from "@/pages/Reports";

export default function App() {
  const { isAuthenticated, initialising } = useAuth();

  return (
    <Routes>
      <Route
        path="/"
        element={
          initialising ? null : (
            <Navigate to={isAuthenticated ? "/dashboard" : "/register"} replace />
          )
        }
      />

      {/* Already-signed-in users have no business on the auth screens. */}
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Register />}
      />
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />}
      />

      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/omni" element={<AskOmni />} />
        <Route path="/twin" element={<DigitalTwin />} />
        <Route path="/doctors" element={<FindDoctors />} />
        <Route path="/care" element={<CareServices />} />
        <Route path="/appointments" element={<Appointments />} />
        <Route path="/pharmacy" element={<Pharmacy />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/insights" element={<HealthInsights />} />
        <Route path="/consent" element={<Consent />} />
        <Route path="/profile" element={<Profile />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
