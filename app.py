import os
import time
import streamlit as st
from dotenv import load_dotenv
from rag_ingestor import FileIngestor
from rag_retriever import RAGRetriever
from email_fetcher import EmailFetcher

load_dotenv()

UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="Knowledge Retrieval System", page_icon="🧠", layout="wide")
st.title("📧 Multi-Format Knowledge Retrieval System")
st.caption("Upload Excel, PDF, DOCX, CSV, TXT, or EML files — ask questions across all your documents & emails")

# --- Init ---
@st.cache_resource
def get_retriever():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY not found in .env file.")
        st.stop()
    return RAGRetriever(api_key=api_key)

@st.cache_resource
def get_email_fetcher():
    return EmailFetcher()

rag = get_retriever()
ingestor = FileIngestor()
fetcher = get_email_fetcher()

# Session state init
if "ingested_files" not in st.session_state:
    st.session_state.ingested_files = set()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "email_log" not in st.session_state:
    st.session_state.email_log = []
if "email_connected" not in st.session_state:
    st.session_state.email_connected = False


# ── Helper: ingest a single uploaded file ─────────────────────────
def _ingest_file(file_path, display_name=None):
    """Ingest a file into the RAG store. Returns (success, num_chunks)."""
    fname = display_name or os.path.basename(file_path)
    if fname in st.session_state.ingested_files:
        return False, 0

    chunks, filename = ingestor.process_file(file_path)
    if chunks:
        rag.add_documents(filename=fname, chunks=chunks)
        st.session_state.ingested_files.add(fname)
        return True, len(chunks)
    return False, 0


# ── IMAP email polling ────────────────────────────────────────────
def _poll_emails():
    """Fetch new emails from IMAP and ingest them."""
    if not fetcher.is_configured():
        return 0

    new_emails = fetcher.fetch_new_emails()
    new_count = 0

    for em in new_emails:
        fname = em["filename"]
        if fname in st.session_state.ingested_files:
            continue

        chunks = em["chunks"]
        if chunks:
            rag.add_documents(filename=fname, chunks=chunks)
            st.session_state.ingested_files.add(fname)
            new_count += 1

            timestamp = time.strftime("%H:%M:%S")
            st.session_state.email_log.append(
                f"**{timestamp}** — 📨 *{em['subject']}* from `{em['from']}` "
                f"({em['date']}) — {len(chunks)} chunks"
            )

    if new_count > 0:
        st.toast(f"📨 {new_count} new email(s) fetched and ingested!", icon="📬")

    return new_count


# --- Sidebar ---
with st.sidebar:
    st.header("📂 Documents")

    # ── File uploader ──
    uploaded_files = st.file_uploader(
        "Upload files (PDF, DOCX, XLSX, CSV, TXT, EML)",
        type=["pdf", "docx", "xlsx", "csv", "txt", "eml"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            success, n_chunks = _ingest_file(file_path, display_name=uploaded_file.name)
            if success:
                st.success(f"✅ {uploaded_file.name} — {n_chunks} chunks indexed")
            elif uploaded_file.name in st.session_state.ingested_files:
                st.info(f"ℹ️ {uploaded_file.name} already indexed")
            else:
                st.warning(f"⚠️ No content extracted from {uploaded_file.name}")

    # ── Email connection section ──
    st.divider()
    st.subheader("📬 Email Integration")

    if fetcher.is_configured():
        # Test connection on first load
        if not st.session_state.email_connected:
            ok, msg = fetcher.test_connection()
            st.session_state.email_connected = ok
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")
        else:
            st.success(f"✅ Connected to `{fetcher.email_addr}`")

        if st.button("📥 Refresh Emails"):
            with st.spinner("Checking mailbox..."):
                n = _poll_emails()
            if n == 0:
                st.info("No new emails found.")
            else:
                st.rerun()
    else:
        st.info(
            "📧 **Email not configured.** Add these to your `.env` file:\n\n"
            "```\n"
            "EMAIL_IMAP_SERVER=imap.gmail.com\n"
            "EMAIL_ADDRESS=you@gmail.com\n"
            "EMAIL_PASSWORD=your_app_password\n"
            "EMAIL_FOLDER=INBOX\n"
            "```\n\n"
            "For Gmail, use an [App Password](https://myaccount.google.com/apppasswords)."
        )

    # Live email feed
    if st.session_state.email_log:
        st.divider()
        st.subheader("📨 Email Feed")
        for entry in reversed(st.session_state.email_log[-10:]):
            st.markdown(entry)

    # ── Indexed documents list ──
    st.divider()
    st.subheader("📑 Indexed Documents")
    sources = rag.list_sources()
    if sources:
        for src in sources:
            ext = os.path.splitext(src)[1].lower()
            icon = {
                ".xlsx": "📊", ".csv": "📊", ".pdf": "📄",
                ".docx": "📝", ".txt": "📃", ".eml": "📧",
            }.get(ext, "📎")
            st.write(f"{icon} {src}")
        st.caption(f"Total chunks: {rag.get_doc_count()}")
    else:
        st.info("No documents uploaded yet.")

    st.divider()
    if st.button("🗑️ Clear All Data", type="secondary"):
        rag.clear_database()
        st.session_state.ingested_files.clear()
        st.session_state.email_log.clear()
        for f_name in os.listdir(UPLOAD_DIR):
            os.remove(os.path.join(UPLOAD_DIR, f_name))
        st.success("Database cleared!")
        st.rerun()


# --- Helper functions ---
def _render_sources(sources_list):
    """Display source references."""
    with st.expander("🧾 Source References"):
        for src in sources_list:
            section_str = f", Section: {src['section']}" if src.get("section") else ""
            doc_name = str(src.get("document", ""))
            if doc_name.endswith(".eml"):
                line_label = "Part"
            elif src.get("section") in ("CSV",) or doc_name.endswith((".xlsx", ".csv")):
                line_label = "Row"
            else:
                line_label = "Line"
            info = f"— **{doc_name}** (Page {src['page']}, {line_label} {src.get('line', '?')}{section_str})"
            if src.get("similarity") is not None:
                info += f" | Relevance: {src['similarity']:.2%}"
            st.markdown(info)


def _render_conflicts(conflicts_list):
    """Display conflict alerts with trusted/untrusted source info."""
    for c in conflicts_list:
        if "resolution" not in c:
            continue
        st.warning(
            f"**⚠️ Conflict detected** — *{c.get('field', 'data')}*\n\n"
            f"{c.get('summary', 'Conflicting information found across sources.')}\n\n"
            f"✅ **Trusted:** {c['trusted_source']} ({c['trusted_detail']}, "
            f"dated {c.get('trusted_date', 'N/A')})\n\n"
            f"❌ **Overridden:** {c['untrusted_source']} ({c['untrusted_detail']}, "
            f"dated {c.get('untrusted_date', 'N/A')})\n\n"
            f"**Resolution:** {c['resolution']}"
        )


# --- Chat ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("conflicts"):
            _render_conflicts(msg["conflicts"])
        if msg.get("sources"):
            _render_sources(msg["sources"])

if question := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    if rag.get_doc_count() == 0:
        answer = "Please upload some documents first using the sidebar."
        query_sources = []
        query_conflicts = []
    else:
        with st.spinner("Searching across all documents & emails..."):
            result = rag.query(question, history=st.session_state.messages)
            answer = result["content"]
            query_sources = result["sources"]
            query_conflicts = result.get("analysis", {}).get("conflicts", [])

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": query_sources,
        "conflicts": query_conflicts,
    })
    with st.chat_message("assistant"):
        st.markdown(answer)
        if query_conflicts:
            _render_conflicts(query_conflicts)
        if query_sources:
            _render_sources(query_sources)
