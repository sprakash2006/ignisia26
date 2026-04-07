import { useState, useRef, useEffect } from "react";
import { api } from "../lib/api";
import Sidebar from "../components/Sidebar";
import Loader from "../components/Loader";
import "./Uploadpage.css";

const FILE_ICONS = { pdf: "", docx: "", xlsx: "", csv: "", txt: "", eml: "" };

export default function UploadPage() {
  const [docs, setDocs] = useState([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedName, setUploadedName] = useState("");
  const [visibility, setVisibility] = useState("shared");
  const [search, setSearch] = useState("");
  const fileRef = useRef();

  useEffect(() => {
    loadDocs();
  }, []);

  async function loadDocs() {
    try {
      const data = await api.get("/documents/");
      setDocs(data);
    } catch {  } finally {
      setPageLoading(false);
    }
  }

  async function handleFiles(files) {
    const file = files[0];
    if (!file) return;
    setUploadedName(file.name);
    setUploading(true);
    setUploadProgress(0);

    
    let p = 0;
    const interval = setInterval(() => {
      p += Math.random() * 12 + 3;
      setUploadProgress(Math.min(Math.round(p), 90));
    }, 150);

    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("visibility", visibility);

      const result = await api.post("/documents/upload", fd);
      clearInterval(interval);
      setUploadProgress(100);

      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
        setUploadedName("");
        loadDocs();
      }, 500);
    } catch (e) {
      clearInterval(interval);
      setUploading(false);
      setUploadProgress(0);
      alert(`Upload failed: ${e.message}`);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this document?")) return;
    setDeleting(id);
    try {
      await api.delete(`/documents/${id}`);
      setDocs(prev => prev.filter(d => d.id !== id));
    } catch (e) {
      alert(`Delete failed: ${e.message}`);
    } finally {
      setDeleting(null);
    }
  }

  const filtered = docs.filter(d => d.filename.toLowerCase().includes(search.toLowerCase()));

  if (pageLoading) {
    return (
      <div className="upload-page">
        <Sidebar />
        <main className="upload-main">
          <Loader text="Loading documents..." />
        </main>
      </div>
    );
  }

  return (
    <div className="upload-page">
      <Sidebar />

      <main className="upload-main">
        <div className="upload-inner">
          {}
          <div className="up-header animate-fade-up">
            <div>
              <h1 className="up-title">Knowledge Resources</h1>
              <p className="up-sub">Upload documents, PDFs, and spreadsheets. The AI indexes them for instant retrieval.</p>
            </div>
            <div className="up-stats">
              <div className="up-stat-card">
                <div className="up-stat-num">{docs.length}</div>
                <div className="up-stat-label">Documents</div>
              </div>
              <div className="up-stat-card">
                <div className="up-stat-num">{docs.filter(d => d.status === "ready").length}</div>
                <div className="up-stat-label">Indexed</div>
              </div>
            </div>
          </div>

          {}
          <div className="vis-toggle animate-fade-up delay-1">
            <button className={`vis-btn ${visibility === "shared" ? "active" : ""}`} onClick={() => setVisibility("shared")}>
               Shared (org-wide)
            </button>
            <button className={`vis-btn ${visibility === "private" ? "active" : ""}`} onClick={() => setVisibility("private")}>
               Private (my docs)
            </button>
          </div>

          {}
          <div
            className={`up-drop-zone animate-fade-up delay-1 ${dragOver ? "drag-active" : ""}`}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
            onClick={() => fileRef.current.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt,.xlsx,.csv,.eml"
              style={{ display: "none" }}
              onChange={e => handleFiles(e.target.files)}
            />

            {uploading ? (
              <div className="up-progress">
                <div className="up-progress-name">{uploadedName}</div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: uploadProgress + "%" }} />
                </div>
                <div className="progress-pct">{uploadProgress}%</div>
              </div>
            ) : (
              <>
                <div className="up-drop-icon"></div>
                <div className="up-drop-title">Drop files here or click to browse</div>
                <div className="up-drop-sub">Supports PDF, DOCX, XLSX, CSV, TXT, EML · Max 50 MB</div>
                <div className="up-drop-btn">Choose file</div>
              </>
            )}
          </div>

          {}
          <div className="up-docs-section animate-fade-up delay-2">
            <div className="up-docs-toolbar">
              <h2 className="up-docs-heading">Uploaded Documents</h2>
              <div className="up-docs-search">
                <span></span>
                <input type="text" placeholder="Search documents..." value={search} onChange={e => setSearch(e.target.value)} />
              </div>
            </div>

            {filtered.length === 0 && (
              <div className="up-docs-empty">No documents found. Upload your first document above.</div>
            )}

            <div className="up-docs-list">
              {filtered.map((doc, i) => {
                const ext = doc.file_type || doc.filename?.split(".").pop() || "";
                return (
                  <div className="up-doc-row" key={doc.id}>
                    <div className="up-doc-icon">{FILE_ICONS[ext] || ""}</div>
                    <div className="up-doc-info">
                      <div className="up-doc-name">{doc.filename}</div>
                      <div className="up-doc-meta">
                        {ext.toUpperCase()} · {doc.chunk_count || 0} chunks · {doc.visibility === "private" ? " Private" : " Shared"}
                      </div>
                    </div>
                    <div className="up-doc-right">
                      <span className={`up-doc-status ${doc.status}`}>
                        {doc.status === "ready" ? " Indexed" : doc.status === "failed" ? " Failed" : "⏳ Processing"}
                      </span>
                      <button className={`up-doc-delete ${deleting === doc.id ? "deleting" : ""}`} onClick={() => handleDelete(doc.id)} disabled={deleting === doc.id} title="Delete">
                        {deleting === doc.id ? <span className="mini-spinner" /> : ""}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {}
          <div className="up-tips animate-fade-up delay-3">
            <div className="up-tip-icon"></div>
            <div>
              <strong>Upload tips</strong>
              <p>Structured PDFs with clear headings give the best AI retrieval results. Excel files with header rows are parsed row-by-row.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
