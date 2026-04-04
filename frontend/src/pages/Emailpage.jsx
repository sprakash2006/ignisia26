import { useState, useEffect } from "react";
import { api } from "../lib/api";
import Sidebar from "../components/Sidebar";
import Loader from "../components/Loader";
import "./Emailpage.css";

export default function EmailPage() {
  const [config, setConfig] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [form, setForm] = useState({ imap_server: "", email_address: "", password: "", folder: "INBOX" });
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [polling, setPolling] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [pollResult, setPollResult] = useState(null);

  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    try {
      const data = await api.get("/emails/config");
      if (data) {
        setConfig(data);
        setForm(f => ({ ...f, imap_server: data.imap_server, email_address: data.email_address, folder: data.folder }));
      }
    } catch { /* empty */ } finally {
      setPageLoading(false);
    }
  }

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }));

  async function handleSave() {
    setSaving(true);
    try {
      await api.post("/emails/config", form);
      await loadConfig();
      setTestResult({ success: true, message: "Configuration saved!" });
    } catch (e) {
      setTestResult({ success: false, message: e.message });
    }
    setSaving(false);
  }

  async function handleTest() {
    setTestResult(null);
    setTesting(true);
    try {
      const result = await api.post("/emails/test-connection", form);
      setTestResult(result);
    } catch (e) {
      setTestResult({ success: false, message: e.message });
    } finally {
      setTesting(false);
    }
  }

  async function handlePoll() {
    setPolling(true);
    setPollResult(null);
    try {
      const result = await api.post("/emails/poll");
      setPollResult(result);
    } catch (e) {
      setPollResult({ message: e.message, count: 0 });
    }
    setPolling(false);
  }

  if (pageLoading) {
    return (
      <div className="email-page">
        <Sidebar />
        <main className="email-main">
          <Loader text="Loading email config..." />
        </main>
      </div>
    );
  }

  return (
    <div className="email-page">
      <Sidebar />

      <main className="email-main">
        <div className="email-inner">
          <div className="em-header animate-fade-up">
            <h1 className="em-title">Email Integration</h1>
            <p className="em-sub">Connect your IMAP mailbox to automatically ingest emails into the knowledge base.</p>
          </div>

          {/* Config form */}
          <div className="em-card animate-fade-up delay-1">
            <h2 className="em-card-title">IMAP Configuration</h2>

            <div className="em-form">
              <div className="em-form-row">
                <div className="em-field">
                  <label>IMAP Server</label>
                  <input type="text" placeholder="imap.gmail.com" value={form.imap_server} onChange={e => update("imap_server", e.target.value)} />
                </div>
                <div className="em-field">
                  <label>Folder</label>
                  <input type="text" placeholder="INBOX" value={form.folder} onChange={e => update("folder", e.target.value)} />
                </div>
              </div>
              <div className="em-field">
                <label>Email Address</label>
                <input type="email" placeholder="you@company.com" value={form.email_address} onChange={e => update("email_address", e.target.value)} />
              </div>
              <div className="em-field">
                <label>App Password</label>
                <input type="password" placeholder="••••••••" value={form.password} onChange={e => update("password", e.target.value)} />
                <span className="em-field-hint">For Gmail, use an App Password — not your main password.</span>
              </div>
            </div>

            <div className="em-actions">
              <button className="em-btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? "Saving…" : "Save Configuration"}
              </button>
              <button className="em-btn-secondary" onClick={handleTest} disabled={testing}>
                {testing ? "Testing..." : "Test Connection"}
              </button>
            </div>

            {testResult && (
              <div className={`em-result ${testResult.success ? "success" : "error"}`}>
                {testResult.success ? "✅" : "❌"} {testResult.message}
              </div>
            )}
          </div>

          {/* Poll section */}
          {config && (
            <div className="em-card animate-fade-up delay-2">
              <h2 className="em-card-title">Fetch Emails</h2>
              <p className="em-card-desc">
                Connected to <strong>{config.email_address}</strong> on {config.imap_server}
                {config.last_polled_at && <> · Last polled: {new Date(config.last_polled_at).toLocaleString()}</>}
              </p>

              <button className="em-btn-primary" onClick={handlePoll} disabled={polling}>
                {polling ? "Checking mailbox…" : "📥 Fetch New Emails"}
              </button>

              {pollResult && (
                <div className="em-result success">
                  {pollResult.message}
                  {pollResult.emails?.map((em, i) => (
                    <div key={i} className="em-email-item">
                      📧 <strong>{em.subject}</strong> from {em.from} — {em.chunk_count} chunks
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Help */}
          <div className="em-tips animate-fade-up delay-3">
            <div className="em-tip-icon">📧</div>
            <div>
              <strong>Email setup guide</strong>
              <p>Emails are ingested as <strong>private documents</strong> under your account. They follow role-based access — only you and your managers can see them.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
