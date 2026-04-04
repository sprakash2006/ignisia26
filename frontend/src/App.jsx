import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./lib/AuthContext";
import HomePage from "./pages/Homepage";
import AuthPage from "./pages/Authpage";
import DashboardPage from "./pages/Dashboardpage";
import UploadPage from "./pages/Uploadpage";
import EmailPage from "./pages/Emailpage";
import RaiseTicketPage from "./pages/RaiseTicketPage";
import TicketsPage from "./pages/TicketsPage";
import ResolveTicketPage from "./pages/ResolveTicketPage";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "var(--ciq-bg)" }}>
        <div style={{ width: 32, height: 32, border: "3px solid var(--ciq-border)", borderTopColor: "var(--ciq-emerald)", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
      </div>
    );
  }
  return user ? children : <Navigate to="/auth" replace />;
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/dashboard" replace /> : children;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/auth" element={<PublicRoute><AuthPage /></PublicRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
      <Route path="/emails" element={<ProtectedRoute><EmailPage /></ProtectedRoute>} />
      <Route path="/raise-ticket" element={<RaiseTicketPage />} />
      <Route path="/tickets" element={<ProtectedRoute><TicketsPage /></ProtectedRoute>} />
      <Route path="/tickets/:id" element={<ProtectedRoute><ResolveTicketPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
