import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import "./Authpage.css";

function LogoMark() {
  return (
    <div className="auth-logo-mark">
      <svg viewBox="0 0 17 17" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8.5" cy="8.5" r="5" stroke="white" strokeWidth="1.8" />
        <path d="M8.5 3.5 L8.5 13.5 M3.5 8.5 L13.5 8.5" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    </div>
  );
}

// Default demo org ID (created in seed migration)
const DEMO_ORG_ID = "a0000000-0000-0000-0000-000000000001";

export default function AuthPage() {
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState("login");
  const navigate = useNavigate();
  const { signIn, signUp, user } = useAuth();

  useEffect(() => {
    if (searchParams.get("mode") === "register") setMode("register");
  }, [searchParams]);

const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "", role: "employee" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async () => {
    setError("");
    if (mode === "login") {
      if (!form.email || !form.password) return setError("Please fill in all fields.");
      setLoading(true);
      try {
        await signIn({ email: form.email, password: form.password });
        navigate("/dashboard", { replace: true });
      } catch (e) {
        setError(e.message || "Login failed");
      } finally {
        setLoading(false);
      }
    } else {
      if (!form.name || !form.email || !form.password) return setError("Please fill in all fields.");
      if (form.password !== form.confirm) return setError("Passwords do not match.");
      if (form.password.length < 6) return setError("Password must be at least 6 characters.");
      setLoading(true);
      try {
        await signUp({
          email: form.email,
          password: form.password,
          fullName: form.name,
          orgId: DEMO_ORG_ID,
          role: form.role,
        });
        navigate("/dashboard", { replace: true });
      } catch (e) {
        setError(e.message || "Signup failed");
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-wrapper">

        {/* LEFT */}
        <div className="auth-branding">
          <div className="auth-brand-logo">
            <LogoMark />
            ContextIQ
          </div>
          <div className="auth-brand-center">
            <div className="auth-agent-visual">🤖</div>
            <h2>AI knowledge,<br /><em>for your whole team.</em></h2>
            <p>Ask questions. Get cited answers.<br />From your company's own PDFs, spreadsheets, and emails.</p>
          </div>
          <div className="auth-brand-pills">
            {["Instant document retrieval", "Source citations on every answer", "Role-based access control", "Conflict detection & resolution"].map(label => (
              <span className="auth-pill" key={label}>
                <span className="auth-pill-dot" />
                {label}
              </span>
            ))}
          </div>
        </div>

        {/* RIGHT */}
        <div className="auth-form-panel">
          <div className="auth-form-top">
            <div className="auth-form-eyebrow">{mode === "login" ? "Welcome back" : "Get started free"}</div>
            <div className="auth-form-title">
              {mode === "login" ? "Sign in to your workspace" : "Create your account"}
            </div>
          </div>

          <div className="auth-tabs">
            <button className={`auth-tab ${mode === "login" ? "active" : ""}`} onClick={() => setMode("login")}>
              Sign In
            </button>
            <button className={`auth-tab ${mode === "register" ? "active" : ""}`} onClick={() => setMode("register")}>
              Register
            </button>
          </div>

          <div className="auth-form-body" onKeyDown={e => e.key === "Enter" && handleSubmit()}>
            {mode === "register" && (
              <>
                <div className="form-field">
                  <label>Full name</label>
                  <input type="text" placeholder="Priya Sharma" value={form.name} onChange={e => update("name", e.target.value)} />
                </div>
                <div className="form-field">
                  <label>Role</label>
                  <select value={form.role} onChange={e => update("role", e.target.value)} className="auth-select">
                    <option value="employee">Employee</option>
                    <option value="manager">Manager</option>
                    <option value="director">Director</option>
                  </select>
                </div>
              </>
            )}

            <div className="form-field">
              <label>Email address</label>
              <input type="email" placeholder="you@company.com" value={form.email} onChange={e => update("email", e.target.value)} />
            </div>

            <div className="form-field">
              <label>Password</label>
              <input type="password" placeholder="••••••••" value={form.password} onChange={e => update("password", e.target.value)} />
            </div>

            {mode === "register" && (
              <div className="form-field">
                <label>Confirm password</label>
                <input type="password" placeholder="••••••••" value={form.confirm} onChange={e => update("confirm", e.target.value)} />
              </div>
            )}

            {error && <div className="auth-error">⚠ {error}</div>}

            <button className={`auth-submit ${loading ? "loading" : ""}`} onClick={handleSubmit} disabled={loading}>
              {loading ? "Setting up…" : mode === "login" ? "Sign in →" : "Create account →"}
            </button>

            <p className="auth-switch">
              {mode === "login"
                ? <> Don't have an account? <span onClick={() => setMode("register")}>Register here</span></>
                : <> Already have an account? <span onClick={() => setMode("login")}>Sign in</span></>
              }
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
