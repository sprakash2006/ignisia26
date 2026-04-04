"""
RAG service — handles document ingestion, vector search, and LLM query.
Replaces rag_retriever.py with Supabase (pgvector) as the vector store.
"""

import logging
from datetime import datetime, timezone
from collections import defaultdict
from openai import OpenAI

from config import settings
from services.supabase_client import get_admin_client
from services.embedding_service import embed_text, embed_batch

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.gpt = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Import here to reuse existing conflict_detector.py
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
        from conflict_detector import ConflictDetector
        self.conflict_detector = ConflictDetector(self.gpt)

    # ── Document Ingestion ───────────────────────────────────────

    async def ingest_document(
        self,
        org_id: str,
        owner_id: str | None,
        filename: str,
        file_type: str,
        file_size: int,
        chunks: list[dict],
        visibility: str = "shared",
        source_type: str = "upload",
        storage_path: str | None = None,
    ) -> dict:
        """Store document metadata and chunks with embeddings in Supabase."""
        sb = get_admin_client()

        # 1. Create document record
        doc_data = {
            "org_id": org_id,
            "owner_id": owner_id,
            "filename": filename,
            "file_type": file_type,
            "file_size_bytes": file_size,
            "visibility": visibility,
            "source_type": source_type,
            "storage_path": storage_path,
            "chunk_count": len(chunks),
            "status": "processing",
        }
        doc_result = sb.table("documents").insert(doc_data).execute()
        document_id = doc_result.data[0]["id"]

        try:
            # 2. Generate embeddings for all chunks
            texts = [c["text"] for c in chunks]
            embeddings = embed_batch(texts)

            # 3. Insert chunks with embeddings
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            chunk_rows = []
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                chunk_rows.append({
                    "document_id": document_id,
                    "org_id": org_id,
                    "content": chunk["text"],
                    "embedding": emb,
                    "page_number": chunk.get("page", 1),
                    "line_number": chunk.get("line", 1),
                    "section": chunk.get("section", ""),
                    "date_added": chunk.get("source_date") or today,
                    "token_count": len(chunk["text"].split()),
                    "chunk_index": i,
                })

            # Insert in batches of 100
            for batch_start in range(0, len(chunk_rows), 100):
                batch = chunk_rows[batch_start:batch_start + 100]
                sb.table("chunks").insert(batch).execute()

            # 4. Mark document as ready
            sb.table("documents").update({"status": "ready"}).eq("id", document_id).execute()

            return {"document_id": document_id, "chunk_count": len(chunks), "status": "ready"}

        except Exception as e:
            logger.error(f"Ingestion failed for {filename}: {e}")
            sb.table("documents").update({
                "status": "failed",
                "error_message": str(e),
            }).eq("id", document_id).execute()
            raise

    # ── Semantic Search (via Supabase RPC) ───────────────────────

    async def search_chunks(
        self,
        query: str,
        org_id: str,
        user_id: str,
        top_k: int = None,
    ) -> list[dict]:
        """Vector similarity search with access control via the match_chunks function."""
        sb = get_admin_client()
        query_embedding = embed_text(query)

        result = sb.rpc("match_chunks", {
            "query_embedding": query_embedding,
            "match_count": top_k or settings.TOP_K,
            "match_threshold": settings.MATCH_THRESHOLD,
            "p_org_id": org_id,
            "p_user_id": user_id,
        }).execute()

        return result.data or []

    # ── Duplicate & Conflict Detection ───────────────────────────

    def _detect_duplicates_and_conflicts(self, chunks: list[dict]) -> dict:
        """Analyze retrieved chunks for duplicates and heuristic conflicts."""
        analysis = {"duplicates": [], "conflicts": [], "unique_sources": set()}

        content_map = defaultdict(list)
        for c in chunks:
            normalized = c["content"].strip().lower()
            source_label = f"{c['filename']} (Page {c['page_number']}, Line {c['line_number']})"
            content_map[normalized].append(source_label)
            analysis["unique_sources"].add(c["filename"])

        for content, locations in content_map.items():
            if len(locations) > 1:
                analysis["duplicates"].append({
                    "text_preview": content[:120] + "..." if len(content) > 120 else content,
                    "found_in": locations,
                })

        # Heuristic key-value conflict detection
        kv_map = defaultdict(list)
        for c in chunks:
            source_label = f"{c['filename']} (Page {c['page_number']}, Line {c['line_number']})"
            for segment in c["content"].split("|"):
                segment = segment.strip()
                if ":" in segment and not segment.startswith("["):
                    key, _, val = segment.partition(":")
                    key, val = key.strip().lower(), val.strip()
                    if key and val:
                        kv_map[key].append({"value": val, "source": source_label})

        for key, entries in kv_map.items():
            unique_values = set(e["value"].lower() for e in entries)
            if len(unique_values) > 1:
                analysis["conflicts"].append({"field": key, "values": entries})

        return analysis

    # ── Full RAG Query ───────────────────────────────────────────

    async def query(
        self,
        question: str,
        org_id: str,
        user_id: str,
        conversation_id: str | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        """Full RAG pipeline: search → detect conflicts → LLM answer."""
        try:
            # 1. Vector search with access control
            chunks = await self.search_chunks(question, org_id, user_id)

            if not chunks:
                return {
                    "content": "Value not available in the source documents.",
                    "sources": [],
                    "analysis": {"duplicates": [], "conflicts": [], "unique_sources": []},
                }

            # 2. Duplicate + heuristic conflict detection
            analysis = self._detect_duplicates_and_conflicts(chunks)

            # 3. Build sources list
            sources = []
            for c in chunks:
                sources.append({
                    "document": c["filename"],
                    "page": c["page_number"],
                    "line": c["line_number"],
                    "section": c.get("section", ""),
                    "date_added": str(c.get("date_added", "")),
                    "chunk": c["content"],
                    "similarity": round(c.get("similarity", 0), 4),
                    "owner_id": c.get("owner_id"),
                    "visibility": c.get("visibility", "shared"),
                })

            # 4. LLM-powered conflict detection (cross-source)
            llm_conflicts = []
            if len(analysis["unique_sources"]) > 1:
                llm_conflicts = self.conflict_detector.detect_conflicts(sources)

            heuristic_fields = {c["field"].lower() for c in analysis["conflicts"]}
            for lc in llm_conflicts:
                if lc["field"].lower() not in heuristic_fields:
                    analysis["conflicts"].append(lc)

            # 5. Get user profile for context
            sb = get_admin_client()
            profile = sb.table("profiles").select("full_name, role").eq("id", user_id).single().execute()
            user_name = profile.data["full_name"]
            user_role = profile.data["role"]

            # 6. Build context and system prompt
            context_parts = []
            for c in chunks:
                section_str = f", Section: {c.get('section', '')}" if c.get("section") else ""
                context_parts.append(
                    f"[Source: {c['filename']}, Page: {c['page_number']}, "
                    f"Line/Row: {c['line_number']}{section_str}, Date: {c.get('date_added', 'N/A')}]\n"
                    f"{c['content']}"
                )
            context = "\n\n---\n\n".join(context_parts)

            # Build analysis advisory
            analysis_advisory = ""
            if analysis["duplicates"]:
                dup_details = "; ".join(
                    f"'{d['text_preview']}' found in {', '.join(d['found_in'])}"
                    for d in analysis["duplicates"]
                )
                analysis_advisory += f"\n⚠️ DUPLICATE DATA DETECTED: {dup_details}\n"
            if analysis["conflicts"]:
                conflict_details = []
                for c in analysis["conflicts"]:
                    vals = ", ".join(f"'{v['value']}' from {v['source']}" for v in c.get("values", []))
                    resolution = c.get("resolution", "")
                    if resolution:
                        conflict_details.append(f"Field '{c['field']}': {vals}. RESOLUTION: {resolution}")
                    else:
                        conflict_details.append(f"Field '{c['field']}' has different values: {vals}")
                analysis_advisory += f"\n⚠️ CONFLICTING DATA DETECTED: {'; '.join(conflict_details)}\n"

            system_prompt = f"""You are a reliable enterprise knowledge agent. You answer questions ONLY from the provided document context.

## Current User
Name: {user_name}, Role: {user_role.title()}
You are answering on behalf of this user. Only documents they are authorized to see are included below.

## STRICT RULES — FOLLOW EXACTLY

### Answer Structure (MANDATORY for every response)
Your response MUST contain ALL of these sections in order:

1. **✅ Final Answer** — The direct answer to the question.
2. **⚠️ Data Quality Notes** — Report ANY of the following that apply:
   - **Missing values**: If data needed to fully answer is not in the context, state: "Value not available in the source documents"
   - **Conflicting values**: If different sources give different values for the same field, list all values, their sources, and state which you chose and why.
   - **Duplicate entries**: If the same data appears in multiple sources, note the redundancy.
   - If none apply, write: "No data quality issues detected."
3. **🧾 Source References** — For each piece of data used, cite: file name, page/row, section.
4. **🧠 Reasoning** — Explain: what was found, what was missing, how conflicts were resolved.

### Grounding Rules
- Answer based ONLY on the provided context. NEVER guess or use external knowledge.
- If the answer is not in the context at all, respond: "Value not available in the source documents"
- If only partial data is available, answer with what exists and explicitly note what is missing.
- When values conflict across sources, present ALL conflicting values transparently and select one with clear justification.

### Data Quality Detection
{analysis_advisory if analysis_advisory else "No duplicates or conflicts were pre-detected in the retrieved data."}

## Document Context
{context}
"""

            # 7. Build messages
            messages = [{"role": "system", "content": system_prompt}]
            chat_history = (history or [])[-10:]
            for msg in chat_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": question})

            # 8. Call LLM
            response = self.gpt.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
            )

            answer = response.choices[0].message.content.strip()

            # 9. Store messages in DB if conversation exists
            if conversation_id:
                sb.table("messages").insert({
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": question,
                }).execute()
                sb.table("messages").insert({
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "analysis": {
                        "duplicates": analysis["duplicates"],
                        "conflicts": analysis["conflicts"],
                        "unique_sources": list(analysis["unique_sources"]),
                    },
                }).execute()

            # Convert set to list for JSON serialization
            analysis["unique_sources"] = list(analysis["unique_sources"])

            return {
                "content": answer,
                "sources": sources,
                "analysis": analysis,
            }

        except Exception as e:
            logger.error(f"RAG query failed: {e}", exc_info=True)
            return {
                "content": f"Error: {e}",
                "sources": [],
                "analysis": {"duplicates": [], "conflicts": [], "unique_sources": []},
            }

    # ── Document Management ──────────────────────────────────────

    async def list_documents(self, org_id: str, user_id: str) -> list[dict]:
        """List documents visible to the user (RLS handles access control)."""
        sb = get_admin_client()
        # We use the match logic on the documents table
        # For simplicity, fetch all docs in org and let Python filter
        # (In production, the RLS policies handle this automatically with user client)
        profile = sb.table("profiles").select("role").eq("id", user_id).single().execute()
        user_role = profile.data["role"]

        query = sb.table("documents").select("*").eq("org_id", org_id).eq("status", "ready")

        if user_role == "director":
            pass  # see everything
        elif user_role == "manager":
            # Get subordinate IDs
            subs = sb.rpc("get_all_subordinates", {"manager_id": user_id}).execute()
            allowed_ids = [user_id] + [s for s in (subs.data or [])]
            result = query.execute()
            docs = [d for d in result.data if d["visibility"] == "shared" or d["owner_id"] in allowed_ids]
            return docs
        else:
            # Employee: shared + own
            result = query.execute()
            docs = [d for d in result.data if d["visibility"] == "shared" or d["owner_id"] == user_id]
            return docs

        return query.execute().data

    async def delete_document(self, document_id: str) -> None:
        """Delete a document and its chunks (CASCADE handles chunks)."""
        sb = get_admin_client()
        sb.table("documents").delete().eq("id", document_id).execute()


# Singleton
_rag_service = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
