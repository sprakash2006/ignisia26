import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import "./Sidebar.css";

const NAV_ITEMS = [
  { icon: "💬", label: "Ask Agent",    to: "/dashboard" },
  { icon: "📁", label: "Documents",    to: "/upload" },
  { icon: "📧", label: "Emails",       to: "/emails" },
];

export default function Sidebar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate("/");
  };

  const roleBadge = { director: "🟣", manager: "🔵", employee: "🟢" };

  return (
    <aside className="sb">
      <div className="sb-logo" onClick={() => navigate("/")}>
        <div className="sb-logo-mark">C</div>
        ContextIQ
      </div>

      <div className="sb-section-title">Workspace</div>
      <nav className="sb-nav">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.label}
            to={item.to}
            className={({ isActive }) => `sb-link ${isActive ? "active" : ""}`}
          >
            <span className="sb-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sb-bottom">
        <div className="sb-user">
          <div className="sb-avatar">{(user?.full_name?.[0] || "U").toUpperCase()}</div>
          <div className="sb-user-info">
            <div className="sb-user-name">{user?.full_name || "User"}</div>
            <div className="sb-user-role">
              {roleBadge[user?.role] || "⚪"} {user?.role || "employee"}
            </div>
          </div>
        </div>
        <button className="sb-logout" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </aside>
  );
}
