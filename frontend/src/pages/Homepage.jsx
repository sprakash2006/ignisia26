import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import "./Homepage.css";

/* ── Scroll reveal ── */
function useScrollReveal() {
  useEffect(() => {
    const els = document.querySelectorAll(".reveal,.reveal-left,.reveal-right");
    const io = new IntersectionObserver(
      (entries) => entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add("visible"); io.unobserve(e.target); }
      }),
      { threshold: 0.1 }
    );
    els.forEach(el => io.observe(el));
    return () => io.disconnect();
  }, []);
}

/* ── Nav shadow on scroll ── */
function useNavScroll() {
  useEffect(() => {
    const nav = document.querySelector(".home-nav");
    const fn = () => window.scrollY > 10 ? nav?.classList.add("scrolled") : nav?.classList.remove("scrolled");
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);
}

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}

/* ── Mini chart ── */
function MiniChart() {
  return (
    <div className="mini-chart">
      <svg viewBox="0 0 240 54" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="ciq-cg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00b478" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#00b478" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d="M0 50 C30 46 50 40 80 32 C110 24 130 18 160 11 C190 4 210 6 240 2" fill="none" stroke="#00b478" strokeWidth="2" strokeLinecap="round" />
        <path d="M0 50 C30 46 50 40 80 32 C110 24 130 18 160 11 C190 4 210 6 240 2 L240 54 L0 54 Z" fill="url(#ciq-cg)" />
      </svg>
    </div>
  );
}

function LogoMark() {
  return (
    <div className="nav-logo-mark">
      <svg viewBox="0 0 17 17" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8.5" cy="8.5" r="5" stroke="white" strokeWidth="1.8" />
        <path d="M8.5 3.5 L8.5 13.5 M3.5 8.5 L13.5 8.5" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    </div>
  );
}

/* ── Data ── */
const FEATURES = [
  { icon: "🔍", title: "Multi-Format Retrieval", desc: "Ingest PDFs, Excel sheets, emails, and more. The agent unifies every format into a single semantic index." },
  { icon: "💬", title: "Natural Language Q&A", desc: "Employees ask anything in plain language and get precise, cited answers grounded in your actual company data." },
  { icon: "🔒", title: "Role-Based Access", desc: "Directors see everything. Managers see their team's docs. Employees see shared + their own. Enforced at database level." },
  { icon: "⚡", title: "Conflict Resolution", desc: "When two documents contradict, the agent surfaces the conflict, picks the latest source, and explains why." },
  { icon: "📧", title: "Email Integration", desc: "Connect your IMAP mailbox. New emails are automatically ingested and searchable within minutes." },
  { icon: "📊", title: "Audit & Analytics", desc: "Track every query, upload, and action. Full transparency for compliance and knowledge ops." },
];

const HOW_STEPS = [
  { num: "01", title: "Upload your company data", desc: "Drag in PDFs, Excel files, Word docs, and email exports. The agent indexes everything with vector embeddings." },
  { num: "02", title: "Agent builds context", desc: "The RAG pipeline chunks, embeds, and stores your data in Supabase with pgvector so every query searches all sources." },
  { num: "03", title: "Employees get cited answers", desc: "Every response links back to the exact document, row, or email paragraph — with conflict detection built in." },
];

const FOOTER_COLS = [
  { title: "Solutions", links: ["Small Business", "Freelancers", "Enterprise", "Integrations"] },
  { title: "Company",   links: ["About", "Careers", "Contact"] },
  { title: "Learn",     links: ["Blog", "Docs", "Guides", "Templates"] },
];

export default function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  useScrollReveal();
  useNavScroll();

  const goAuth = () => user ? navigate("/dashboard") : navigate("/auth");
  const goRegister = () => user ? navigate("/dashboard") : navigate("/auth?mode=register");

  return (
    <div className="home-page">

      {/* ── NAV ── */}
      <nav className="home-nav">
        <div className="home-nav-logo"><LogoMark />ContextIQ</div>
        <div className="home-nav-links">
          <button className="nav-link-btn" onClick={() => scrollTo("features")}>Product</button>
          <button className="nav-link-btn" onClick={() => scrollTo("how")}>How it works</button>
          <button className="nav-link-btn" onClick={() => scrollTo("pricing")}>Pricing</button>
          <button className="nav-link-btn" onClick={() => navigate("/raise-ticket")}>Raise a Ticket</button>
          <button className="nav-btn-ghost" onClick={goAuth}>{user ? "Dashboard" : "Log in"}</button>
          {!user && <button className="nav-btn-solid" onClick={goRegister}>Get started</button>}
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="home-hero">
        <div className="hero-left">
          <div className="hero-badge reveal">
            <span className="hero-badge-dot" />
            AI Agent · SME-01 · Ignisia
          </div>
          <h1 className="hero-title reveal delay-1">
            Your employees,<br />backed by <em>every</em><br />document you own.
          </h1>
          <p className="hero-sub reveal delay-2">
            ContextIQ reads your PDFs, spreadsheets, and emails — so any employee can ask anything and get an instant, cited answer from your actual data.
          </p>
          <div className="hero-input-row reveal delay-3">
            <input className="hero-email-input" placeholder="your@company.com" type="email" />
            <button className="hero-start-btn" onClick={goRegister}>Try free ↗</button>
          </div>
          <div className="hero-logos reveal delay-4">
            <span className="hero-logos-label">Powered by</span>
            {["Supabase", "pgvector", "GPT-4o", "FastAPI"].map(l => <span className="hero-logo-pill" key={l}>{l}</span>)}
          </div>
        </div>

        <div className="hero-right reveal-right delay-2">
          <div className="hero-float-badge">
            <span className="badge-dot-em" />
            <div><div className="badge-text">Agent Online</div><div className="badge-sub">Searching 847 docs</div></div>
          </div>

          <div className="hero-mockup">
            <div className="mockup-topbar">
              <div className="mockup-dots"><div className="mockup-dot" /><div className="mockup-dot" /><div className="mockup-dot" /></div>
              <div className="mockup-topbar-title">ContextIQ Agent</div>
              <div className="mockup-agent-badge">● LIVE</div>
            </div>
            <div className="mockup-chat">
              <div className="chat-msg user">
                <div className="chat-avatar user">👤</div>
                <div className="chat-bubble user">What's our refund policy for bulk orders to Acme Corp last month?</div>
              </div>
              <div className="chat-msg">
                <div className="chat-avatar agent">AI</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  <div className="chat-sources">
                    <span className="chat-source-chip">📄 Refund_Policy_v3.pdf</span>
                    <span className="chat-source-chip">📊 Acme_Q3_Quote.xlsx</span>
                    <span className="chat-source-chip">✉️ email_thread.eml</span>
                  </div>
                  <div className="chat-bubble agent">
                    Bulk orders over ₹50,000 are eligible for a{" "}
                    <strong style={{ color: "#00b478" }}>15-day full refund</strong> — initiated within 5 business days.
                    <div className="cite-pill">📄 Refund_Policy_v3.pdf · Section 4.2</div>
                    <div className="cite-pill">📊 Acme_Q3_Quote.xlsx · Row 14</div>
                  </div>
                </div>
              </div>
              <div className="chat-msg user">
                <div className="chat-avatar user">👤</div>
                <div className="chat-bubble user">Any conflicts with the old policy?</div>
              </div>
              <div className="chat-msg">
                <div className="chat-avatar agent">AI</div>
                <div className="chat-typing"><span /><span /><span /></div>
              </div>
            </div>
            <div className="mockup-input-bar">
              <div className="mockup-fake-input">Ask anything about your company data…</div>
              <div className="mockup-send-btn">↑</div>
            </div>
          </div>

          <div className="hero-float-badge-2">
            <span style={{ fontSize: 16 }}>✅</span>
            <div><div className="badge-text">Conflict detected & resolved</div><div className="badge-sub">v3 takes priority over v1</div></div>
          </div>
        </div>
      </section>

      {/* ── TRUSTED BY ── */}
      <div className="home-trusted">
        <hr className="trusted-divider" />
        <div className="trusted-label reveal">Powering knowledge ops at teams using</div>
        <div className="trusted-logos reveal delay-1">
          {["Zoho", "Razorpay", "Freshworks", "Postman", "Chargebee", "Clevertap"].map(l => (
            <span className="trusted-logo" key={l}>{l}</span>
          ))}
        </div>
      </div>

      {/* ── FEATURES STRIP ── */}
      <section className="home-features-strip" id="features">
        <div className="features-strip-inner">
          <div className="reveal-left">
            <div className="section-tag">Company Intelligence</div>
            <h2 className="strip-heading">The agent that knows<br />your <em>entire</em> business.</h2>
            <p className="strip-sub">Build a live knowledge layer over your PDFs, spreadsheets, and email threads. Every employee gets an AI co-worker with full context.</p>
            <div className="strip-features">
              {[
                { icon: "🗂️", title: "Cross-format indexing", desc: "PDFs, Excel, CSV, Word, TXT, and EML — unified into one semantic index with pgvector." },
                { icon: "🔗", title: "Source-linked answers", desc: "Every response cites the exact document, section, and row. Zero hallucinations." },
                { icon: "🧠", title: "Conflict-aware reasoning", desc: "When docs contradict, the agent flags it, picks the most recent, and explains the resolution." },
              ].map(f => (
                <div className="strip-feature" key={f.title}>
                  <div className="strip-feature-icon">{f.icon}</div>
                  <div><h4>{f.title}</h4><p>{f.desc}</p></div>
                </div>
              ))}
            </div>
          </div>

          <div className="strip-right reveal-right">
            <div className="stat-card em">
              <div className="stat-value">3k+</div>
              <div className="stat-label">SMEs running on ContextIQ agents</div>
            </div>
            <div className="stat-card">
              <div className="transfer-row">
                <div className="transfer-node a">📄</div>
                <div className="transfer-line" />
                <div className="transfer-node b">🤖</div>
              </div>
              <div className="stat-label" style={{ marginTop: 8 }}>Instant retrieval on every query</div>
            </div>
            <div className="stat-card wide">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ciq-ash)", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 4 }}>
                    Knowledge coverage · 6 months
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 900, color: "var(--ciq-ink)", letterSpacing: "-1.5px", lineHeight: 1 }}>
                    ₹1,87,65,800
                  </div>
                </div>
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--ciq-emerald)", background: "var(--ciq-emerald-dim)", border: "1px solid var(--ciq-border-em)", borderRadius: 4, padding: "3px 8px" }}>
                  +24%
                </span>
              </div>
              <MiniChart />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
                {["Jan", "Feb", "Mar", "Apr", "May", "Jun"].map(m => (
                  <span key={m} style={{ fontSize: 10, color: "var(--ciq-mist)" }}>{m}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── WHY ── */}
      <section className="home-why" id="why">
        <div className="section-tag reveal" style={{ margin: "0 auto 12px" }}>Why ContextIQ</div>
        <h2 className="section-heading-center reveal delay-1">Why teams prefer our <em>agents</em></h2>
        <p className="section-sub-center reveal delay-2">
          Purpose-built for SMEs who can't afford enterprise knowledge tools but pay the same cost of siloed data.
        </p>
        <div className="why-grid">
          {FEATURES.map((f, i) => (
            <div className={`why-card reveal delay-${(i % 3) + 1}`} key={f.title}>
              <div className="why-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="home-how" id="how">
        <div className="home-how-inner">
          <div className="section-tag reveal">How it works</div>
          <h2 className="strip-heading reveal delay-1" style={{ maxWidth: 520 }}>
            From raw documents to<br /><em>agent-ready context</em> in minutes.
          </h2>
          <div className="how-steps">
            {HOW_STEPS.map((s, i) => (
              <div className={`how-step reveal delay-${i + 1}`} key={s.num}>
                <div className="step-num">{s.num}</div>
                <div className="step-body"><h4>{s.title}</h4><p>{s.desc}</p></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── STATS ── */}
      <section className="home-stats">
        <div className="stats-header">
          <div className="section-tag reveal" style={{ margin: "0 auto 12px" }}>Our impact</div>
          <h2 className="section-heading-center reveal delay-1">We've helped innovative companies</h2>
          <p className="section-sub-center reveal delay-2">Hundreds of SMEs have transformed how their teams access information.</p>
        </div>
        <div className="stats-row">
          {[
            { val: "24", unit: "%", label: "Average revenue uplift" },
            { val: "180", unit: "K", label: "Queries answered monthly" },
            { val: "10", unit: "+", label: "Months of runway saved per team" },
          ].map((s, i) => (
            <div className={`stat-item reveal delay-${i + 1}`} key={s.label}>
              <div className="stat-big">{s.val}<span>{s.unit}</span></div>
              <div className="stat-desc">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── PRICING ── */}
      <section className="home-pricing" id="pricing">
        <div className="home-pricing-inner">
          <div className="section-tag reveal" style={{ margin: "0 auto 12px" }}>Choose plan</div>
          <h2 className="pricing-heading reveal delay-1">Simple, honest pricing</h2>
          <p className="pricing-sub reveal delay-2">No hidden fees. No lock-in. Cancel any time.</p>
          <div className="pricing-cards">
            <div className="pricing-card reveal delay-2">
              <div className="pricing-card-label">Plus</div>
              <div className="pricing-price">₹249 <sub>/month</sub></div>
              <div style={{ fontSize: 12, color: "var(--ciq-ash)", marginTop: 12, lineHeight: 1.6 }}>
                Up to 5 users · 500 MB data · Email support
              </div>
              <div className="pricing-cta-link" onClick={goRegister}>Get started ↗</div>
            </div>
            <div className="pricing-card featured reveal delay-3">
              <div className="pricing-card-label">Premium</div>
              <div className="pricing-price">₹599 <sub>/month</sub></div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", marginTop: 12, lineHeight: 1.6 }}>
                Unlimited users · 10 GB data · Priority support · Email integration
              </div>
              <div className="pricing-cta-link" onClick={goRegister}>Get started ↗</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ── */}
      <section className="home-cta-banner">
        <h2 className="cta-heading reveal">
          Ready to give every employee<br />an <em>AI that knows your business?</em>
        </h2>
        <p className="reveal delay-1">Set up in minutes. No engineering required. Your company's knowledge, always within reach.</p>
        <div className="cta-btn-row reveal delay-2">
          <button className="cta-primary" onClick={goRegister}>Start for free</button>
          <button className="cta-secondary" onClick={() => navigate("/raise-ticket")}>Raise a Ticket</button>
          <button className="cta-secondary" onClick={goAuth}>See a demo ↗</button>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="home-footer">
        <div className="footer-top">
          <div>
            <div className="footer-logo"><LogoMark />ContextIQ</div>
            <p className="footer-brand-desc">AI-powered knowledge retrieval for SMEs. Think. Build. Evolve.</p>
          </div>
          {FOOTER_COLS.map(col => (
            <div key={col.title}>
              <div className="footer-col-title">{col.title}</div>
              {col.links.map(l => (
                <button key={l} className="footer-col-link">{l}</button>
              ))}
            </div>
          ))}
        </div>
        <div className="footer-bottom">
          <p>© 2026 ContextIQ · Built for Ignisia AI Hackathon, MIT-WPU Pune</p>
          <div className="footer-socials">
            {["𝕏", "in", "f"].map(s => <div className="footer-social" key={s}>{s}</div>)}
          </div>
        </div>
      </footer>

    </div>
  );
}
