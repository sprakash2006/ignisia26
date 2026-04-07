import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import { api } from "../lib/api";
import "./RaiseTicketPage.css";

const CATEGORIES = ["general", "billing", "technical", "access", "other"];
const PRIORITIES = ["low", "medium", "high", "urgent"];

export default function RaiseTicketPage() {
  const { user } = useAuth();
  const [form, setForm] = useState({
    customer_name: user?.full_name || "",
    customer_email: user?.email || "",
    customer_phone: "",
    subject: "",
    query: "",
    category: "general",
    priority: "medium",
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.customer_email || !form.subject || !form.query) return;
    setSubmitting(true);
    setResult(null);
    try {
      const data = await api.post("/tickets/raise", form);
      setResult({ success: true, ticketId: data.ticket_id || data.id });
    } catch (err) {
      setResult({ success: false, message: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  function LogoMark() {
    return (
      <div className="rt-logo-mark">
        <svg viewBox="0 0 17 17" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="8.5" cy="8.5" r="5" stroke="white" strokeWidth="1.8" />
          <path d="M8.5 3.5 L8.5 13.5 M3.5 8.5 L13.5 8.5" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </div>
    );
  }

  if (result?.success) {
    return (
      <div className="rt-page">
        <nav className="rt-nav">
          <Link to="/" className="rt-nav-logo"><LogoMark />PaperTrail</Link>
          <Link to="/" className="rt-nav-back">← Back to home</Link>
        </nav>
        <div className="rt-center">
          <div className="rt-success-card animate-fade-up">
            <div className="rt-success-icon"></div>
            <h2 className="rt-success-title">Ticket Submitted!</h2>
            <p className="rt-success-id">Your ticket ID is <strong>#{result.ticketId}</strong></p>
            <p className="rt-success-msg">We've received your query and will get back to you shortly at <strong>{form.customer_email}</strong>.</p>
            <div className="rt-success-actions">
              <button className="rt-btn-primary" onClick={() => { setResult(null); setForm({ customer_name: user?.full_name || "", customer_email: user?.email || "", customer_phone: "", subject: "", query: "", category: "general", priority: "medium" }); }}>Raise Another Ticket</button>
              <Link to="/" className="rt-btn-ghost">Go Home</Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rt-page">
      <nav className="rt-nav">
        <Link to="/" className="rt-nav-logo"><LogoMark />PaperTrail</Link>
        <Link to="/" className="rt-nav-back">← Back to home</Link>
      </nav>

      <div className="rt-center">
        <div className="rt-card animate-fade-up">
          <div className="rt-header">
            <div className="rt-header-icon"></div>
            <h1 className="rt-title">Raise a Support Ticket</h1>
            <p className="rt-subtitle">Describe your issue and our team will get back to you as soon as possible.</p>
          </div>

          <form className="rt-form" onSubmit={handleSubmit}>
            <div className="rt-form-row">
              <div className="rt-field">
                <label>Full Name</label>
                <input type="text" placeholder="Your name" value={form.customer_name} onChange={(e) => update("customer_name", e.target.value)} />
              </div>
              <div className="rt-field">
                <label>Email <span className="rt-req">*</span></label>
                <input type="email" placeholder="you@example.com" required value={form.customer_email} onChange={(e) => update("customer_email", e.target.value)} />
              </div>
            </div>

            <div className="rt-form-row">
              <div className="rt-field">
                <label>Phone</label>
                <input type="tel" placeholder="+91 98765 43210" value={form.customer_phone} onChange={(e) => update("customer_phone", e.target.value)} />
              </div>
              <div className="rt-field">
                <label>Category</label>
                <select value={form.category} onChange={(e) => update("category", e.target.value)}>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
              </div>
            </div>

            <div className="rt-form-row">
              <div className="rt-field">
                <label>Subject <span className="rt-req">*</span></label>
                <input type="text" placeholder="Brief summary of your issue" required value={form.subject} onChange={(e) => update("subject", e.target.value)} />
              </div>
              <div className="rt-field">
                <label>Priority</label>
                <select value={form.priority} onChange={(e) => update("priority", e.target.value)}>
                  {PRIORITIES.map((p) => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
                </select>
              </div>
            </div>

            <div className="rt-field">
              <label>Describe your issue <span className="rt-req">*</span></label>
              <textarea placeholder="Please provide as much detail as possible about your issue..." required rows={5} value={form.query} onChange={(e) => update("query", e.target.value)} />
            </div>

            {result?.success === false && (
              <div className="rt-error">{result.message}</div>
            )}

            <button className="rt-btn-primary rt-submit" type="submit" disabled={submitting}>
              {submitting ? "Submitting..." : "Submit Ticket"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
