import logging
import chromadb
from datetime import datetime, timezone
from collections import defaultdict
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from conflict_detector import ConflictDetector
from org_model import User, visible_owners


class RAGRetriever:
    def __init__(self, api_key: str, persist_dir="rag_store", top_k=5):
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="deva_docs",
            metadata={"hnsw:space": "cosine"}
        )
        self.top_k = top_k
        self.gpt = OpenAI(api_key=api_key)
        self.conflict_detector = ConflictDetector(self.gpt)

    def _detect_duplicates_and_conflicts(self, retrieved_docs, metadatas):
        """Analyze retrieved chunks for duplicate and conflicting data."""
        analysis = {"duplicates": [], "conflicts": [], "unique_sources": set()}

        # Group chunks by normalized content to find exact/near duplicates
        content_map = defaultdict(list)
        for doc, meta in zip(retrieved_docs, metadatas):
            normalized = doc.strip().lower()
            source_label = f"{meta.get('source', '?')} (Page {meta.get('page', '?')}, Line {meta.get('line', '?')})"
            content_map[normalized].append(source_label)
            analysis["unique_sources"].add(meta.get("source", "Unknown"))

        for content, locations in content_map.items():
            if len(locations) > 1:
                analysis["duplicates"].append({
                    "text_preview": content[:120] + "..." if len(content) > 120 else content,
                    "found_in": locations,
                })

        # Detect potential conflicts: chunks from different sources about the same entity
        # with differing values — heuristic: look for key-value patterns
        kv_map = defaultdict(list)  # key -> list of (value, source)
        for doc, meta in zip(retrieved_docs, metadatas):
            source_label = f"{meta.get('source', '?')} (Page {meta.get('page', '?')}, Line {meta.get('line', '?')})"
            # Parse "Key: Value" patterns from structured chunks (Excel/CSV rows)
            for segment in doc.split("|"):
                segment = segment.strip()
                if ":" in segment and not segment.startswith("["):
                    key, _, val = segment.partition(":")
                    key = key.strip().lower()
                    val = val.strip()
                    if key and val:
                        kv_map[key].append({"value": val, "source": source_label})

        for key, entries in kv_map.items():
            unique_values = set(e["value"].lower() for e in entries)
            if len(unique_values) > 1:
                analysis["conflicts"].append({
                    "field": key,
                    "values": entries,
                })

        return analysis

    def _filter_by_access(self, docs, metadatas, distances, user: User | None):
        """Remove chunks the current user is not allowed to see."""
        if user is None:
            return docs, metadatas, distances  # no filtering (legacy/admin mode)

        allowed = visible_owners(user)
        # Map allowed set: None in allowed means shared docs are ok → match "__shared__"
        allowed_owners = set()
        for a in allowed:
            allowed_owners.add("__shared__" if a is None else a)

        filtered = [(d, m, dist) for d, m, dist in zip(docs, metadatas, distances)
                     if m.get("owner", "__shared__") in allowed_owners]

        if not filtered:
            return [], [], []
        docs_f, metas_f, dists_f = zip(*filtered)
        return list(docs_f), list(metas_f), list(dists_f)

    def query(self, question: str, history: list[dict] = None, user: User | None = None) -> dict:
        try:
            chat_history = history[-10:] if history else []

            query_embed = self.embedder.encode(question).tolist()

            # Fetch more candidates so we still have enough after access filtering
            results = self.collection.query(
                query_embeddings=[query_embed],
                n_results=30,
                include=["documents", "distances", "metadatas"]
            )

            if not results["documents"] or not results["documents"][0]:
                return {
                    "content": "Value not available in the source documents.",
                    "sources": [],
                    "analysis": {"duplicates": [], "conflicts": [], "unique_sources": set()},
                }

            # ── Access control: drop chunks the user must not see ──
            raw_docs = results["documents"][0]
            raw_metas = results["metadatas"][0]
            raw_dists = results["distances"][0] if results.get("distances") else [0] * len(raw_docs)

            filtered = self._filter_by_access(raw_docs, raw_metas, raw_dists, user)
            if not filtered[0]:
                return {
                    "content": "Value not available in the source documents.",
                    "sources": [],
                    "analysis": {"duplicates": [], "conflicts": [], "unique_sources": set()},
                }

            retrieved_docs = list(filtered[0])[:15]
            metadatas = list(filtered[1])[:15]
            distances = list(filtered[2])[:15]
            similarity_scores = [round(1 - d, 4) for d in distances]

            # Run duplicate/conflict detection
            analysis = self._detect_duplicates_and_conflicts(retrieved_docs, metadatas)

            # Build context with source labels
            context_parts = []
            sources = []
            for i, (doc, meta, score) in enumerate(zip(retrieved_docs, metadatas, similarity_scores)):
                source_name = meta.get("source", "Unknown")
                page_num = meta.get("page", "?")
                line_num = meta.get("line", "?")
                section = meta.get("section", "")
                date_added = meta.get("date_added", "N/A")
                section_str = f", Section: {section}" if section else ""
                context_parts.append(
                    f"[Source: {source_name}, Page: {page_num}, Line/Row: {line_num}{section_str}, Date: {date_added}]\n{doc}"
                )
                sources.append({
                    "document": source_name,
                    "page": page_num,
                    "line": line_num,
                    "section": section,
                    "date_added": date_added,
                    "chunk": doc,
                    "similarity": score,
                    "owner": meta.get("owner", "__shared__"),
                    "visibility": meta.get("visibility", "shared"),
                })

            context = "\n\n---\n\n".join(context_parts)

            # ══════════════════════════════════════════════════════
            # LLM-POWERED CONFLICT DETECTION (semantic, cross-source)
            # This catches conflicts the heuristic misses, like
            # "refund in 14 days" (PDF) vs "refund in 30 days" (email)
            # ══════════════════════════════════════════════════════
            llm_conflicts = []
            if len(analysis["unique_sources"]) > 1:
                # Only run if chunks come from multiple sources (otherwise no cross-source conflict possible)
                llm_conflicts = self.conflict_detector.detect_conflicts(sources)

            # Merge LLM conflicts into the existing analysis dict
            # (existing heuristic conflicts stay — they're fast and free)
            for lc in llm_conflicts:
                # Avoid duplicates: skip if heuristic already caught this field
                heuristic_fields = {c["field"].lower() for c in analysis["conflicts"]}
                if lc["field"].lower() not in heuristic_fields:
                    analysis["conflicts"].append(lc)

            # Build analysis advisory for the LLM
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
                    if "values" in c:
                        # LLM-detected conflict (has values + resolution)
                        vals = ", ".join(f"'{v['value']}' from {v['source']}" for v in c['values'])
                        conflict_details.append(
                            f"Field '{c['field']}': {vals}. "
                            f"RESOLUTION: {c.get('resolution', 'Use the most recent source.')}"
                        )
                    else:
                        # Heuristic-detected conflict (original format)
                        vals = ", ".join(f"'{v['value']}' from {v['source']}" for v in c.get('values', []))
                        conflict_details.append(f"Field '{c['field']}' has different values: {vals}")
                analysis_advisory += f"\n⚠️ CONFLICTING DATA DETECTED: {'; '.join(conflict_details)}\n"

            # Build user context line for the LLM
            user_context = ""
            if user:
                user_context = (
                    f"\n## Current User\n"
                    f"Name: {user.name}, Role: {user.role.title()}\n"
                    f"You are answering on behalf of this user. "
                    f"Only documents they are authorized to see are included below.\n"
                )

            system_prompt = f"""You are a reliable enterprise knowledge agent. You answer questions ONLY from the provided document context.
{user_context}

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
- When values conflict across sources, present ALL conflicting values transparently and select one with clear justification (e.g., most recent source, most detailed source).

### Data Quality Detection
{analysis_advisory if analysis_advisory else "No duplicates or conflicts were pre-detected in the retrieved data."}

## Document Context
{context}
"""

            messages = [{"role": "system", "content": system_prompt}]
            for msg in chat_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": question})

            response = self.gpt.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=2000,
                temperature=0.2,
            )

            return {
                "content": response.choices[0].message.content.strip(),
                "sources": sources,
                "analysis": analysis,
            }

        except Exception as e:
            logging.error(f"RAG query failed: {e}", exc_info=True)
            return {
                "content": f"Error: {e}",
                "sources": [],
                "analysis": {"duplicates": [], "conflicts": [], "unique_sources": set()},
            }

    def add_documents(self, filename: str, chunks: list[dict],
                      owner: str | None = None, visibility: str = "shared"):
        """
        Store document chunks with ownership metadata.

        owner:      username who owns the doc (None = org-wide shared doc)
        visibility: "shared" (everyone) or "private" (access-controlled)
        """
        if not chunks:
            return

        today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        documents = [c["text"] for c in chunks]
        metadatas = [{
            "source": filename,
            "page": c["page"],
            "line": c.get("line", 1),
            "section": c.get("section", ""),
            "date_added": c.get("source_date") or today_date,
            "owner": owner or "__shared__",
            "visibility": visibility,
        } for c in chunks]
        ids = [f"{filename}_{i}" for i in range(len(chunks))]

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logging.info(f"Added {len(chunks)} chunks for '{filename}' "
                     f"[owner={owner or 'shared'}, visibility={visibility}]")

    def get_doc_count(self) -> int:
        return self.collection.count()

    def list_sources(self, user: User | None = None) -> list[dict]:
        """Return list of {source, owner, visibility} dicts, filtered by access."""
        all_meta = self.collection.get(include=["metadatas"])
        seen = set()
        sources = []

        if user is not None:
            allowed = visible_owners(user)
            allowed_owners = {"__shared__" if a is None else a for a in allowed}
        else:
            allowed_owners = None  # no filter

        for meta in all_meta["metadatas"]:
            name = meta.get("source", "Unknown")
            owner = meta.get("owner", "__shared__")
            vis = meta.get("visibility", "shared")

            if allowed_owners is not None and owner not in allowed_owners:
                continue
            if name not in seen:
                seen.add(name)
                sources.append({"source": name, "owner": owner, "visibility": vis})

        return sorted(sources, key=lambda s: s["source"])

    def delete_by_source(self, filename: str):
        all_data = self.collection.get(include=["metadatas"])
        ids_to_delete = []
        for doc_id, meta in zip(all_data["ids"], all_data["metadatas"]):
            if meta.get("source") == filename:
                ids_to_delete.append(doc_id)
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)

    def clear_database(self):
        """Deletes all items in the current collection."""
        all_ids = self.collection.get()["ids"]
        if all_ids:
            self.collection.delete(ids=all_ids)
        logging.info("Cleared all chunks from the database")
