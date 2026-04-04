import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Sidebar from "../components/Sidebar";
import Loader from "../components/Loader";
import "./TicketsPage.css";

const STATUS_TABS = ["all", "open", "in_progress", "resolved", "closed"];
const STATUS_COLORS = { open: "amber", in_progress: "blue", resolved: "green", closed: "gray" };
const PRIORITY_COLORS = { low: "gray", medium: "amber", high: "orange", urgent: "red" };

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

const PER_PAGE = 10;

export default function TicketsPage() {
  const navigate = useNavigate();
  const [pageLoading, setPageLoading] = useState(true);
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({ total: 0, open: 0, in_progress: 0, resolved: 0, closed: 0 });
  const [activeTab, setActiveTab] = useState("all");
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTickets, setTotalTickets] = useState(0);
  const [listLoading, setListLoading] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    loadTickets();
  }, [currentPage, activeTab]);

  async function loadStats() {
    try {
      const statsData = await api.get("/tickets/stats");
      setStats(statsData);
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }

  async function loadTickets() {
    setListLoading(true);
    try {
      const statusParam = activeTab !== "all" ? `&status=${activeTab}` : "";
      const data = await api.get(`/tickets/?page=${currentPage}&per_page=${PER_PAGE}${statusParam}`);
      setTickets(data.tickets || []);
      setTotalPages(data.total_pages || 1);
      setTotalTickets(data.total || 0);
    } catch (err) {
      console.error("Failed to load tickets:", err);
    } finally {
      setListLoading(false);
      setPageLoading(false);
    }
  }

  function handleTabChange(tab) {
    setActiveTab(tab);
    setCurrentPage(1);
  }

  const filtered = tickets.filter((t) => {
    if (search) {
      const q = search.toLowerCase();
      return (
        (t.subject || "").toLowerCase().includes(q) ||
        (t.customer_email || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="tk-page">
      <Sidebar />
      <main className="tk-main">
        {pageLoading ? (
          <Loader text="Loading tickets..." fullPage />
        ) : (
          <div className="tk-inner animate-fade-up">
            <div className="tk-header">
              <h1 className="tk-title">Support Tickets</h1>
              <p className="tk-sub">Manage and resolve customer support queries</p>
            </div>

            {/* Stats */}
            <div className="tk-stats">
              {[
                { label: "Total", value: stats.total, cls: "total" },
                { label: "Open", value: stats.open, cls: "open" },
                { label: "In Progress", value: stats.in_progress, cls: "in-progress" },
                { label: "Resolved", value: stats.resolved, cls: "resolved" },
                { label: "Closed", value: stats.closed, cls: "closed" },
              ].map((s) => (
                <div className={`tk-stat-card tk-stat-${s.cls}`} key={s.label}>
                  <div className="tk-stat-value">{s.value}</div>
                  <div className="tk-stat-label">{s.label}</div>
                </div>
              ))}
            </div>

            {/* Filters */}
            <div className="tk-filters">
              <div className="tk-tabs">
                {STATUS_TABS.map((tab) => (
                  <button
                    key={tab}
                    className={`tk-tab ${activeTab === tab ? "active" : ""}`}
                    onClick={() => handleTabChange(tab)}
                  >
                    {tab === "in_progress" ? "In Progress" : tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>
              <input
                className="tk-search"
                type="text"
                placeholder="Search by subject or email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {/* Ticket List */}
            {listLoading ? (
              <Loader text="Loading tickets..." />
            ) : filtered.length === 0 ? (
              <div className="tk-empty">
                <div className="tk-empty-icon">🎫</div>
                <p>No tickets found{activeTab !== "all" ? ` with status "${activeTab}"` : ""}.</p>
              </div>
            ) : (
              <>
                <div className="tk-list">
                  {filtered.map((ticket) => (
                    <div
                      className="tk-ticket-card"
                      key={ticket.id}
                      onClick={() => navigate(`/tickets/${ticket.id}`)}
                    >
                      <div className="tk-ticket-top">
                        <span className="tk-ticket-subject">{ticket.subject}</span>
                        <span className="tk-ticket-time">{timeAgo(ticket.created_at)}</span>
                      </div>
                      <div className="tk-ticket-meta">
                        <span className="tk-ticket-email">{ticket.customer_email}</span>
                        <span className={`tk-badge tk-cat`}>{ticket.category || "general"}</span>
                        <span className={`tk-badge tk-priority-${PRIORITY_COLORS[ticket.priority] || "gray"}`}>{ticket.priority || "medium"}</span>
                        <span className={`tk-badge tk-status-${STATUS_COLORS[ticket.status] || "gray"}`}>
                          {ticket.status === "in_progress" ? "In Progress" : (ticket.status || "open").charAt(0).toUpperCase() + (ticket.status || "open").slice(1)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="tk-pagination">
                    <button
                      className="tk-page-btn"
                      disabled={currentPage <= 1}
                      onClick={() => setCurrentPage(p => p - 1)}
                    >
                      ← Prev
                    </button>

                    <div className="tk-page-numbers">
                      {Array.from({ length: totalPages }, (_, i) => i + 1)
                        .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2)
                        .reduce((acc, p, i, arr) => {
                          if (i > 0 && p - arr[i - 1] > 1) acc.push("...");
                          acc.push(p);
                          return acc;
                        }, [])
                        .map((item, i) =>
                          item === "..." ? (
                            <span key={`dots-${i}`} className="tk-page-dots">...</span>
                          ) : (
                            <button
                              key={item}
                              className={`tk-page-num ${currentPage === item ? "active" : ""}`}
                              onClick={() => setCurrentPage(item)}
                            >
                              {item}
                            </button>
                          )
                        )}
                    </div>

                    <button
                      className="tk-page-btn"
                      disabled={currentPage >= totalPages}
                      onClick={() => setCurrentPage(p => p + 1)}
                    >
                      Next →
                    </button>

                    <span className="tk-page-info">
                      {totalTickets} ticket{totalTickets !== 1 ? "s" : ""} · Page {currentPage} of {totalPages}
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
