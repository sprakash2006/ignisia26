import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import Sidebar from "../components/Sidebar";
import Loader from "../components/Loader";
import "./ResolveTicketPage.css";

const STATUS_COLORS = { open: "amber", in_progress: "blue", resolved: "green", closed: "gray" };
const PRIORITY_COLORS = { low: "gray", medium: "amber", high: "orange", urgent: "red" };

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export default function ResolveTicketPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [pageLoading, setPageLoading] = useState(true);
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState(null);

  
  const [resolving, setResolving] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);
  const [emailBody, setEmailBody] = useState("");

  
  const [assigning, setAssigning] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [sendConfirm, setSendConfirm] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  
  const [notes, setNotes] = useState([]);
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  useEffect(() => {
    loadTicket();
    loadNotes();
  }, [id]);

  async function loadTicket() {
    try {
      const data = await api.get(`/tickets/${id}`);
      setTicket(data);
      if (data.email_body) setEmailBody(data.email_body);
      if (data.ai_response) setAiResponse(data.ai_response);
    } catch (err) {
      setError(err.message);
    } finally {
      setPageLoading(false);
    }
  }

  async function loadNotes() {
    try {
      const data = await api.get(`/tickets/${id}/notes`);
      setNotes(data.notes || data || []);
    } catch {  }
  }

  async function handleAssign() {
    setAssigning(true);
    setActionMsg(null);
    try {
      await api.patch(`/tickets/${id}/assign`);
      await loadTicket();
      setActionMsg({ type: "success", text: "Ticket assigned to you!" });
    } catch (err) {
      setActionMsg({ type: "error", text: err.message });
    } finally {
      setAssigning(false);
    }
  }

  async function handleResolve() {
    setResolving(true);
    setActionMsg(null);
    try {
      const data = await api.post(`/tickets/${id}/resolve`);
      setAiResponse(data.ai_response || data.response);
      setEmailBody(data.email_body || data.email_draft || "");
      await loadTicket();
    } catch (err) {
      setActionMsg({ type: "error", text: err.message });
    } finally {
      setResolving(false);
    }
  }

  async function handleSaveDraft() {
    setSavingDraft(true);
    setActionMsg(null);
    try {
      await api.patch(`/tickets/${id}/email-body`, { email_body: emailBody });
      setActionMsg({ type: "success", text: "Draft saved!" });
    } catch (err) {
      setActionMsg({ type: "error", text: err.message });
    } finally {
      setSavingDraft(false);
    }
  }

  async function handleSendEmail() {
    setSendingEmail(true);
    setActionMsg(null);
    try {
      await api.post(`/tickets/${id}/send-email`);
      setActionMsg({ type: "success", text: `Email sent to ${ticket.customer_email}!` });
      setSendConfirm(false);
      await loadTicket();
    } catch (err) {
      setActionMsg({ type: "error", text: err.message });
    } finally {
      setSendingEmail(false);
    }
  }

  async function handleAddNote() {
    if (!noteText.trim()) return;
    setAddingNote(true);
    try {
      await api.post(`/tickets/${id}/notes`, { content: noteText });
      setNoteText("");
      await loadNotes();
    } catch (err) {
      setActionMsg({ type: "error", text: err.message });
    } finally {
      setAddingNote(false);
    }
  }

  return (
    <div className="rv-page">
      <Sidebar />
      <main className="rv-main">
        {pageLoading ? (
          <Loader text="Loading ticket..." fullPage />
        ) : error ? (
          <div className="rv-inner animate-fade-up">
            <div className="rv-error-card">
              <p>{error}</p>
              <button className="rv-btn-ghost" onClick={() => navigate("/tickets")}>Back to Tickets</button>
            </div>
          </div>
        ) : ticket && (
          <div className="rv-inner animate-fade-up">
            {}
            <button className="rv-back" onClick={() => navigate("/tickets")}>← Back to Tickets</button>

            {}
            <div className="rv-info-card">
              <div className="rv-info-header">
                <h1 className="rv-ticket-subject">{ticket.subject}</h1>
                <div className="rv-info-badges">
                  <span className={`rv-badge rv-status-${STATUS_COLORS[ticket.status] || "gray"}`}>
                    {ticket.status === "in_progress" ? "In Progress" : (ticket.status || "open").charAt(0).toUpperCase() + (ticket.status || "open").slice(1)}
                  </span>
                  <span className={`rv-badge rv-priority-${PRIORITY_COLORS[ticket.priority] || "gray"}`}>
                    {(ticket.priority || "medium").charAt(0).toUpperCase() + (ticket.priority || "medium").slice(1)}
                  </span>
                </div>
              </div>

              <div className="rv-info-grid">
                <div className="rv-info-item">
                  <span className="rv-info-label">Customer</span>
                  <span className="rv-info-value">{ticket.customer_name || "—"}</span>
                </div>
                <div className="rv-info-item">
                  <span className="rv-info-label">Email</span>
                  <span className="rv-info-value">{ticket.customer_email}</span>
                </div>
                <div className="rv-info-item">
                  <span className="rv-info-label">Phone</span>
                  <span className="rv-info-value">{ticket.customer_phone || "—"}</span>
                </div>
                <div className="rv-info-item">
                  <span className="rv-info-label">Category</span>
                  <span className="rv-info-value" style={{ textTransform: "capitalize" }}>{ticket.category || "general"}</span>
                </div>
                <div className="rv-info-item">
                  <span className="rv-info-label">Created</span>
                  <span className="rv-info-value">{formatDate(ticket.created_at)}</span>
                </div>
                <div className="rv-info-item">
                  <span className="rv-info-label">Assigned To</span>
                  <span className="rv-info-value">{ticket.assigned_to_name || ticket.assigned_to || "Unassigned"}</span>
                </div>
              </div>
            </div>

            {}
            <div className="rv-query-card">
              <div className="rv-query-label">Customer Query</div>
              <div className="rv-query-body">{ticket.query || ticket.description}</div>
            </div>

            {}
            {actionMsg && (
              <div className={`rv-action-msg rv-action-${actionMsg.type}`}>{actionMsg.text}</div>
            )}

            {}
            {ticket.email_sent && (
              <div className="rv-closed-banner">
                <span className="rv-closed-icon"></span>
                <div>
                  <strong>Ticket Resolved & Email Sent</strong>
                  <p>Email was sent to <strong>{ticket.customer_email}</strong> on {formatDate(ticket.email_sent_at)}</p>
                </div>
              </div>
            )}

            {}
            {!ticket.email_sent && (
              <div className="rv-actions">
                {!ticket.assigned_to && (
                  <button className="rv-btn-secondary" onClick={handleAssign} disabled={assigning}>
                    {assigning ? "Assigning..." : "Assign to Me"}
                  </button>
                )}
                <button className="rv-btn-primary" onClick={handleResolve} disabled={resolving}>
                  {resolving ? "AI is analyzing documents..." : aiResponse ? "Regenerate AI Response" : "Generate AI Response"}
                </button>
              </div>
            )}

            {}
            {resolving && (
              <div className="rv-ai-loading">
                <Loader text="AI is analyzing documents and generating response..." />
              </div>
            )}

            {aiResponse && !resolving && (
              <div className="rv-ai-card">
                <div className="rv-ai-label">AI Response</div>
                <div className="rv-ai-body">{aiResponse}</div>
              </div>
            )}

            {}
            {emailBody && !resolving && (
              <div className={`rv-email-card ${ticket.email_sent ? "rv-email-sent" : ""}`}>
                <div className="rv-email-label">
                  {ticket.email_sent ? "Sent Email" : "Email Draft to Customer"}
                </div>
                {ticket.email_sent ? (
                  <div className="rv-email-readonly" dangerouslySetInnerHTML={{ __html: emailBody }} />
                ) : (
                  <>
                    <textarea
                      className="rv-email-editor"
                      value={emailBody}
                      onChange={(e) => setEmailBody(e.target.value)}
                      rows={10}
                    />
                    <div className="rv-email-actions">
                      <button className="rv-btn-secondary" onClick={handleSaveDraft} disabled={savingDraft}>
                        {savingDraft ? "Saving..." : "Save Draft"}
                      </button>
                      {!sendConfirm ? (
                        <button className="rv-btn-primary" onClick={() => setSendConfirm(true)}>
                          Send Email
                        </button>
                      ) : (
                        <div className="rv-confirm-row">
                          <span className="rv-confirm-text">Send email to <strong>{ticket.customer_email}</strong>?</span>
                          <button className="rv-btn-primary" onClick={handleSendEmail} disabled={sendingEmail}>
                            {sendingEmail ? "Sending..." : "Confirm Send"}
                          </button>
                          <button className="rv-btn-ghost" onClick={() => setSendConfirm(false)}>Cancel</button>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}

            {}
            <div className="rv-notes-card">
              <div className="rv-notes-label">Internal Notes</div>
              <div className="rv-notes-list">
                {notes.length === 0 ? (
                  <div className="rv-notes-empty">No notes yet.</div>
                ) : (
                  notes.map((note, i) => (
                    <div className="rv-note" key={note.id || i}>
                      <div className="rv-note-header">
                        <span className="rv-note-author">{note.author_name || note.author || "Agent"}</span>
                        <span className="rv-note-time">{formatDate(note.created_at)}</span>
                      </div>
                      <div className="rv-note-body">{note.content}</div>
                    </div>
                  ))
                )}
              </div>
              <div className="rv-note-input-row">
                <input
                  className="rv-note-input"
                  placeholder="Add an internal note..."
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddNote()}
                />
                <button className="rv-btn-primary rv-note-btn" onClick={handleAddNote} disabled={addingNote || !noteText.trim()}>
                  {addingNote ? "..." : "Add"}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
