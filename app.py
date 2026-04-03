import os
import streamlit as st
from dotenv import load_dotenv
from rag_ingestor import FileIngestor
from rag_retriever import RAGRetriever

load_dotenv()

st.set_page_config(page_title="Knowledge Retrieval System", page_icon="🧠", layout="wide")
st.title("🧠 Multi-Format Knowledge Retrieval System")
st.caption("Upload Excel, PDF, DOCX, CSV, or TXT files — ask questions across all your documents")

# --- Init ---
@st.cache_resource
def get_retriever():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY not found in .env file.")
        st.stop()
    return RAGRetriever(api_key=api_key)

rag = get_retriever()
ingestor = FileIngestor()

# --- Sidebar: Upload & Manage Documents ---
with st.sidebar:
    st.header("📁 Documents")

    uploaded_files = st.file_uploader(
        "Upload files (PDF, DOCX, XLSX, CSV, TXT)",
        type=["pdf", "docx", "xlsx", "csv", "txt"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = os.path.join("uploaded_docs", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            chunks, filename = ingestor.process_file(file_path)

            if chunks:
                rag.add_documents(filename=uploaded_file.name, chunks=chunks)
                st.success(f"✅ {uploaded_file.name} — {len(chunks)} chunks indexed")
            else:
                st.warning(f"⚠️ No content extracted from {uploaded_file.name}")

    st.divider()
    st.subheader("Indexed Documents")
    sources = rag.list_sources()
    if sources:
        for src in sources:
            ext = os.path.splitext(src)[1].lower()
            icon = {".xlsx": "📊", ".csv": "📊", ".pdf": "📄", ".docx": "📝", ".txt": "📃"}.get(ext, "📎")
            st.write(f"{icon} {src}")
        st.caption(f"Total chunks: {rag.get_doc_count()}")
    else:
        st.info("No documents uploaded yet.")

    st.divider()
    if st.button("🗑️ Clear All Data", type="secondary"):
        rag.clear_database()
        for f_name in os.listdir("uploaded_docs"):
            os.remove(os.path.join("uploaded_docs", f_name))
        st.success("Database cleared!")
        st.rerun()


# --- Helper functions (defined before use) ---
def _render_sources(sources_list):
    """Display source references."""
    with st.expander("🧾 Source References"):
        for src in sources_list:
            section_str = f", Section: {src['section']}" if src.get("section") else ""
            line_label = "Row" if src.get("section") in ("CSV",) or str(src.get("document", "")).endswith((".xlsx", ".csv")) else "Line"
            info = f"— **{src['document']}** (Page {src['page']}, {line_label} {src.get('line', '?')}{section_str})"
            if src.get("similarity") is not None:
                info += f" | Relevance: {src['similarity']:.2%}"
            st.markdown(info)


def _render_conflicts(conflicts_list):
    """Display conflict alerts with trusted/untrusted source info."""
    for c in conflicts_list:
        # Only render LLM-detected conflicts (they have 'resolution' key)
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
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("conflicts"):
            _render_conflicts(msg["conflicts"])
        if msg.get("sources"):
            _render_sources(msg["sources"])

# Chat input
if question := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    if rag.get_doc_count() == 0:
        answer = "Please upload some documents first using the sidebar."
        query_sources = []
        query_conflicts = []
    else:
        with st.spinner("Searching across all documents..."):
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
