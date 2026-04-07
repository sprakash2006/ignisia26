import { useState, useEffect, useRef } from "react";
import { useAuth } from "../lib/AuthContext";
import { api } from "../lib/api";
import Sidebar from "../components/Sidebar";
import Loader from "../components/Loader";
import "./Dashboardpage.css";

const QUICK_ACTIONS = [
  { icon: "", title: "Ask a question",  desc: "Query your company knowledge base instantly" },
  { icon: "", title: "Browse documents", desc: "Explore uploaded resources by topic" },
  { icon: "", title: "Recent answers",   desc: "Review your last cited responses" },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [search, setSearch] = useState("");
  const [expandedSources, setExpandedSources] = useState({});
  const [pageLoading, setPageLoading] = useState(true);
  const [msgsLoading, setMsgsLoading] = useState(false);
  const chatEndRef = useRef(null);

  const toggleSources = (idx) => setExpandedSources(prev => ({ ...prev, [idx]: !prev[idx] }));

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function loadConversations() {
    try {
      const data = await api.get("/chat/conversations");
      setConversations(data);
    } catch {  } finally {
      setPageLoading(false);
    }
  }

  async function createConversation(title) {
    try {
      const conv = await api.post("/chat/conversations", { title });
      setActiveConvId(conv.id);
      setConversations(prev => [conv, ...prev]);
      return conv.id;
    } catch { return null; }
  }

  async function loadMessages(convId) {
    setMsgsLoading(true);
    try {
      const msgs = await api.get(`/chat/conversations/${convId}/messages`);
      setMessages(msgs.map(m => ({
        role: m.role,
        content: m.content,
        sources: m.sources || [],
        analysis: m.analysis || {},
      })));
      setActiveConvId(convId);
    } catch {  } finally {
      setMsgsLoading(false);
    }
  }

  async function handleAsk() {
    if (!query.trim() || loading) return;
    const q = query;
    setQuery("");
    setLoading(true);

    
    setMessages(prev => [...prev, { role: "user", content: q }]);

    try {
      let convId = activeConvId;
      if (!convId) {
        convId = await createConversation(q.slice(0, 40));
      }

      const result = await api.post("/chat/query", {
        question: q,
        conversation_id: convId,
      });

      setMessages(prev => [...prev, {
        role: "assistant",
        content: result.content,
        sources: result.sources || [],
        analysis: result.analysis || {},
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: ` Error: ${e.message}. Make sure the backend is running on port 8000.`,
        sources: [],
        analysis: {},
      }]);
    }

    setLoading(false);
  }

  function newChat() {
    setMessages([]);
    setActiveConvId(null);
  }

  const firstName = user?.full_name?.split(" ")[0] || "there";
  const hasAnswer = messages.length > 0;
  const filtered = conversations.filter(c => c.title.toLowerCase().includes(search.toLowerCase()));

  if (pageLoading) {
    return (
      <div className="dash-page">
        <Sidebar />
        <main className="dash-center">
          <Loader text="Loading your workspace..." />
        </main>
        <aside className="dash-history">
          <Loader text="Loading chats..." />
        </aside>
      </div>
    );
  }

  return (
    <div className="dash-page">
      <Sidebar />

      {}
      <main className="dash-center">
        <div className="dash-center-inner">
          {msgsLoading && (
            <Loader text="Loading conversation..." />
          )}
          {!msgsLoading && !hasAnswer && (
            <div className="center-welcome">
              <div className="center-agent-icon"></div>
              <h1 className="center-title">Hi {firstName}, what do<br />you need to know?</h1>
              <p className="center-sub">Ask anything — the agent searches all your company documents.</p>
              <div className="center-docs-badge">
                <span className="badge-dot-live" />
                Agent ready · Role: {user?.role}
              </div>
            </div>
          )}

          {!msgsLoading && !hasAnswer && (
            <div className="quick-actions">
              {QUICK_ACTIONS.map(a => (
                <button key={a.title} className="qa-card"
                  onClick={() => a.title === "Ask a question" && document.getElementById("query-input")?.focus()}>
                  <span className="qa-icon">{a.icon}</span>
                  <div className="qa-title">{a.title}</div>
                  <div className="qa-desc">{a.desc}</div>
                </button>
              ))}
            </div>
          )}

          {}
          {!msgsLoading && hasAnswer && (
            <div className="chat-messages">
              {messages.map((msg, i) => (
                <div key={i} className={`msg-row ${msg.role}`}>
                  <div className={`msg-avatar ${msg.role}`}>
                    {msg.role === "user" ? (user?.full_name?.[0] || "U") : "AI"}
                  </div>
                  <div className="msg-content">
                    <div className={`msg-bubble ${msg.role}`}>
                      {msg.content}
                    </div>
                    {msg.sources?.length > 0 && (
                      <div className={`msg-sources ${expandedSources[i] ? "expanded" : ""}`}>
                        <button className="sources-toggle" onClick={() => toggleSources(i)}>
                          <span className="sources-label">Sources ({msg.sources.length})</span>
                          <span className={`sources-arrow ${expandedSources[i] ? "open" : ""}`}>▶</span>
                        </button>
                        {expandedSources[i] && (
                          <div className="sources-chips">
                            {msg.sources.map((s, j) => {
                              const ext = s.document?.split(".").pop() || "";
                              const icon = { pdf: "", xlsx: "", csv: "", docx: "", eml: "", txt: "" }[ext] || "";
                              return (
                                <span key={j} className="source-chip">
                                  {icon} {s.document} · p.{s.page} · {s.similarity ? `${(s.similarity * 100).toFixed(0)}%` : ""}
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                    {msg.analysis?.conflicts?.length > 0 && (
                      <div className="msg-conflicts">
                        {msg.analysis.conflicts.map((c, j) => (
                          <div key={j} className="conflict-alert">
                            <strong> Conflict: {c.field}</strong>
                            {c.resolution && <p>{c.resolution}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="msg-row assistant">
                  <div className="msg-avatar assistant">AI</div>
                  <div className="msg-content">
                    <div className="msg-typing"><span /><span /><span /></div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {}
        <div className="query-bar-wrapper">
          <div className="query-bar">
            <div className="query-agent-icon"></div>
            <input
              id="query-input"
              className="query-input"
              type="text"
              placeholder="Ask anything from your company's knowledge base…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleAsk()}
            />
            <button
              className={`qbar-send ${loading ? "loading" : ""}`}
              onClick={handleAsk}
              disabled={loading || !query.trim()}
            >
              {loading ? <span className="mini-spinner" /> : "↑"}
            </button>
          </div>
        </div>
      </main>

      {}
      <aside className="dash-history">
        <div className="history-header">
          <h3>Chat history</h3>
        </div>
        <div className="history-search">
          <span className="hsearch-icon"></span>
          <input type="text" placeholder="Search chats…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="history-list">
          {filtered.map(c => (
            <div
              className={`history-item ${c.id === activeConvId ? "active" : ""}`}
              key={c.id}
              onClick={() => loadMessages(c.id)}
            >
              <div className="history-item-title">{c.title}</div>
              <div className="history-item-time">
                {new Date(c.updated_at).toLocaleDateString()}
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="history-empty">No conversations yet</div>
          )}
        </div>
        <button className="new-chat-btn" onClick={newChat}>
          + New chat
        </button>
      </aside>
    </div>
  );
}
