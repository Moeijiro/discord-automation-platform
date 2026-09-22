import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui/Feedback";
import { Dashboard } from "@/pages/Dashboard";
import { Login } from "@/pages/Login";
import { NotFound } from "@/pages/NotFound";
import { ServerDetail } from "@/pages/ServerDetail";
import { ServerLogs } from "@/pages/ServerLogs";
import { Settings } from "@/pages/Settings";

/** Gate for everything behind a session; the API enforces it again server side. */
function RequireAuth() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Checking session" />;
  return user ? <AppShell /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<RequireAuth />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/server/:guildId" element={<ServerDetail />} />
          <Route path="/dashboard/server/:guildId/logs" element={<ServerLogs />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AuthProvider>
  );
}
