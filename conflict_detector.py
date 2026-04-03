import logging
import json
import re
from datetime import datetime
from openai import OpenAI


class ConflictDetector:
    def __init__(self, openai_client: OpenAI):
        self.gpt = openai_client

    def detect_conflicts(self, sources: list[dict]) -> list[dict]:
        """
        Takes the retrieved source chunks and checks for semantic
        contradictions between chunks from DIFFERENT documents.

        Args:
            sources: list of dicts (same format as your existing sources list):
                {
                    "document": "Pricing_2025.xlsx",
                    "page": 1,
                    "line": 42,
                    "section": "Sheet1",
                    "date_added": "2025-04-03",
                    "chunk": "...",
                    "similarity": 0.87,
                }

        Returns:
            list of conflict dicts for the frontend/prompt:
                {
                    "field": "unit pricing",
                    "summary": "Email quotes ₹500/unit but spreadsheet shows ₹650/unit",
                    "trusted_source": "Pricing_2025.xlsx",
                    "trusted_detail": "Page 1, Row 42",
                    "trusted_date": "2025-03-01",
                    "untrusted_source": "acme_email_jan.txt",
                    "untrusted_detail": "Page 1, Line 3",
                    "untrusted_date": "2025-01-15",
                    "resolution": "Trusting 'Pricing_2025.xlsx' (dated 2025-03-01)..."
                    "values": [
                        {"value": "₹650/unit", "source": "Pricing_2025.xlsx (Row 42)"},
                        {"value": "₹500/unit", "source": "acme_email_jan.txt (Line 3)"},
                    ]
                }
        """
        if len(sources) < 2:
            return []

        # Only compare chunks from DIFFERENT documents
        cross_source_pairs = []
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                if sources[i]["document"] != sources[j]["document"]:
                    cross_source_pairs.append((sources[i], sources[j]))

        if not cross_source_pairs:
            return []

        
        cross_source_pairs = cross_source_pairs[:10]

        return self._llm_conflict_check(cross_source_pairs)

    def _llm_conflict_check(self, pairs: list[tuple]) -> list[dict]:
        """Send cross-source pairs to GPT, ask for contradictions."""

        pairs_text = ""
        for idx, (a, b) in enumerate(pairs):
            src_a = f"{a['document']} (Page {a.get('page', '?')}, Line/Row {a.get('line', '?')})"
            src_b = f"{b['document']} (Page {b.get('page', '?')}, Line/Row {b.get('line', '?')})"
            pairs_text += f"""
--- PAIR {idx + 1} ---
SOURCE A [{src_a}] (date: {a.get('date_added', 'unknown')}):
{a['chunk'][:600]}

SOURCE B [{src_b}] (date: {b.get('date_added', 'unknown')}):
{b['chunk'][:600]}
"""

        prompt = f"""You are a conflict detection engine for a company knowledge base.
Analyze each pair of document chunks below. For each pair, determine if they contain
CONTRADICTORY information — meaning different values for the SAME thing.

Examples of real conflicts:
- Different prices for the same product
- Different refund periods for the same policy  
- Different contact info for the same person
- Different deadlines or dates for the same event

NOT conflicts:
- Two chunks about completely different topics
- Same info repeated in different words
- One chunk has extra detail the other lacks (that's supplementary, not contradictory)

{pairs_text}

Respond ONLY with this JSON (no markdown, no backticks, no extra text):
{{
    "conflicts": [
        {{
            "pair_index": 1,
            "has_conflict": true,
            "field": "unit price",
            "summary": "Source A quotes ₹500/unit while Source B shows ₹650/unit for Widget Pro",
            "value_a": "₹500/unit",
            "value_b": "₹650/unit"
        }}
    ]
}}

If NO conflicts exist, return: {{"conflicts": []}}"""

        try:
            response = self.gpt.chat.completions.create(
                model="gpt-4o-mini",  
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.0,
            )

            raw = response.choices[0].message.content.strip()
            raw = re.sub(r'^```json\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            result = json.loads(raw)

            conflicts = []
            for c in result.get("conflicts", []):
                if not c.get("has_conflict"):
                    continue

                pair_idx = c["pair_index"] - 1
                if pair_idx < 0 or pair_idx >= len(pairs):
                    continue

                chunk_a, chunk_b = pairs[pair_idx]

                # Resolve: pick the newer or more authoritative source
                trusted, untrusted, resolution = self._resolve_conflict(
                    chunk_a, chunk_b, c.get("summary", "")
                )

                src_label = lambda s: (
                    f"{s['document']} (Page {s.get('page', '?')}, "
                    f"{'Row' if str(s.get('document','')).endswith(('.xlsx','.csv')) else 'Line'} "
                    f"{s.get('line', '?')})"
                )

                conflicts.append({
                    "field": c.get("field", "unknown"),
                    "summary": c.get("summary", "Conflicting information detected"),
                    "trusted_source": trusted["document"],
                    "trusted_detail": f"Page {trusted.get('page', '?')}, Row/Line {trusted.get('line', '?')}",
                    "trusted_date": trusted.get("date_added", "unknown"),
                    "untrusted_source": untrusted["document"],
                    "untrusted_detail": f"Page {untrusted.get('page', '?')}, Row/Line {untrusted.get('line', '?')}",
                    "untrusted_date": untrusted.get("date_added", "unknown"),
                    "resolution": resolution,
                    "values": [
                        {"value": c.get("value_a", "?"), "source": src_label(chunk_a)},
                        {"value": c.get("value_b", "?"), "source": src_label(chunk_b)},
                    ],
                })

            return conflicts

        except json.JSONDecodeError as e:
            logging.error(f"Conflict detection JSON parse failed: {e}")
            return []
        except Exception as e:
            logging.error(f"Conflict detection failed: {e}")
            return []

    def _resolve_conflict(self, chunk_a: dict, chunk_b: dict, summary: str) -> tuple:
        """
        Decide which source to trust.
        Priority: date (newer wins) → file type (spreadsheet > PDF > text/email)
        Returns: (trusted, untrusted, reason_string)
        """
        date_a = self._parse_date(chunk_a.get("date_added"))
        date_b = self._parse_date(chunk_b.get("date_added"))

        # 1. Try date-based resolution
        if date_a and date_b and date_a != date_b:
            if date_a > date_b:
                return (chunk_a, chunk_b,
                    f"Trusting '{chunk_a['document']}' (dated {chunk_a.get('date_added')}) — "
                    f"it is more recent than '{chunk_b['document']}' (dated {chunk_b.get('date_added')}).")
            else:
                return (chunk_b, chunk_a,
                    f"Trusting '{chunk_b['document']}' (dated {chunk_b.get('date_added')}) — "
                    f"it is more recent than '{chunk_a['document']}' (dated {chunk_a.get('date_added')}).")

        # 2. Same date or no dates → file type heuristic
        # Spreadsheets are usually the source of truth for pricing/data
        priority = {".xlsx": 4, ".xls": 4, ".csv": 3, ".pdf": 2, ".docx": 2, ".txt": 1, ".eml": 1}
        ext_a = "." + chunk_a["document"].rsplit(".", 1)[-1].lower() if "." in chunk_a["document"] else ""
        ext_b = "." + chunk_b["document"].rsplit(".", 1)[-1].lower() if "." in chunk_b["document"] else ""
        pri_a = priority.get(ext_a, 0)
        pri_b = priority.get(ext_b, 0)

        if pri_a > pri_b:
            return (chunk_a, chunk_b,
                f"Both sources have the same date. Trusting '{chunk_a['document']}' — "
                f"structured data sources (spreadsheets) are typically the canonical reference.")
        elif pri_b > pri_a:
            return (chunk_b, chunk_a,
                f"Both sources have the same date. Trusting '{chunk_b['document']}' — "
                f"structured data sources (spreadsheets) are typically the canonical reference.")
        else:
            # Same priority — trust A by default, flag for human review
            return (chunk_a, chunk_b,
                f"Could not determine which source is more authoritative. "
                f"Defaulting to '{chunk_a['document']}' — recommend manual verification.")

    def _parse_date(self, date_str) -> datetime | None:
        if not date_str or date_str in ("unknown", "N/A"):
            return None
        formats = [
            "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
            "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str), fmt)
            except ValueError:
                continue
        return None
