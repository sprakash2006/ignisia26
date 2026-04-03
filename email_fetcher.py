"""
email_fetcher.py — Real IMAP email fetcher for the RAG pipeline.

Connects to any IMAP server (Gmail, Outlook, custom), fetches
UNSEEN emails, parses them via the ingestor's _process_email logic,
and tracks seen Message-IDs to avoid re-ingesting.

Environment variables (set in .env):
    EMAIL_IMAP_SERVER   — e.g. imap.gmail.com
    EMAIL_ADDRESS       — e.g. yourname@gmail.com
    EMAIL_PASSWORD      — app password (NOT your main password)
    EMAIL_FOLDER        — mailbox folder to poll (default: INBOX)
"""

import os
import imaplib
import email as email_lib
import email.policy
import tempfile
import logging
from email.utils import parsedate_to_datetime
from rag_ingestor import FileIngestor

logger = logging.getLogger(__name__)


class EmailFetcher:
    def __init__(self):
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "")
        self.email_addr = os.getenv("EMAIL_ADDRESS", "")
        self.email_pass = os.getenv("EMAIL_PASSWORD", "")
        self.folder = os.getenv("EMAIL_FOLDER", "INBOX")
        self.ingestor = FileIngestor()
        self._seen_ids: set[str] = set()  # Message-IDs already processed

    def is_configured(self) -> bool:
        """Check if IMAP credentials are set."""
        return bool(self.imap_server and self.email_addr and self.email_pass)

    def reload_config(self):
        """Re-read env vars (useful if user updates .env at runtime)."""
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "")
        self.email_addr = os.getenv("EMAIL_ADDRESS", "")
        self.email_pass = os.getenv("EMAIL_PASSWORD", "")
        self.folder = os.getenv("EMAIL_FOLDER", "INBOX")

    def fetch_new_emails(self) -> list[dict]:
        """
        Connect to IMAP, fetch UNSEEN emails, parse & chunk them.

        Returns a list of dicts:
            {
                "filename": "email_<message_id_hash>.eml",
                "subject": "Re: Pricing Update",
                "from": "alice@example.com",
                "date": "2025-04-01",
                "chunks": [ {text, page, line, section, source_date}, ... ]
            }
        """
        if not self.is_configured():
            return []

        results = []
        conn = None

        try:
            # Connect
            conn = imaplib.IMAP4_SSL(self.imap_server)
            conn.login(self.email_addr, self.email_pass)
            conn.select(self.folder, readonly=False)

            # Search for UNSEEN emails
            status, msg_nums = conn.search(None, "UNSEEN")
            if status != "OK" or not msg_nums[0]:
                return []

            email_ids = msg_nums[0].split()
            logger.info(f"Found {len(email_ids)} unseen email(s)")

            for eid in email_ids:
                try:
                    # Fetch the full email
                    status, data = conn.fetch(eid, "(RFC822)")
                    if status != "OK" or not data[0]:
                        continue

                    raw_bytes = data[0][1]
                    msg = email_lib.message_from_bytes(
                        raw_bytes, policy=email_lib.policy.default
                    )

                    # Dedup by Message-ID
                    msg_id = msg.get("Message-ID", "")
                    if msg_id and msg_id in self._seen_ids:
                        continue
                    if msg_id:
                        self._seen_ids.add(msg_id)

                    # Extract basic headers for display
                    subject = str(msg.get("Subject", "(No Subject)"))
                    sender = str(msg.get("From", "Unknown"))
                    email_date = None
                    raw_date = msg.get("Date")
                    if raw_date:
                        try:
                            dt = parsedate_to_datetime(str(raw_date))
                            email_date = dt.strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    # Write to a temp .eml file so the ingestor can parse it
                    safe_id = (msg_id or str(eid)).replace("<", "").replace(">", "")
                    safe_id = "".join(c if c.isalnum() else "_" for c in safe_id)[:60]
                    eml_filename = f"email_{safe_id}.eml"
                    tmp_path = os.path.join(tempfile.gettempdir(), eml_filename)

                    with open(tmp_path, "wb") as f:
                        f.write(raw_bytes)

                    # Parse & chunk via the ingestor
                    chunks, _ = self.ingestor.process_file(tmp_path)

                    # Clean up temp file
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

                    if chunks:
                        results.append({
                            "filename": eml_filename,
                            "subject": subject,
                            "from": sender,
                            "date": email_date or "unknown",
                            "chunks": chunks,
                        })

                    # Mark as SEEN so we don't re-fetch next poll
                    conn.store(eid, "+FLAGS", "\\Seen")

                except Exception as e:
                    logger.error(f"Failed to process email {eid}: {e}")
                    continue

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP error: {e}")
        except Exception as e:
            logger.error(f"Email fetch failed: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                    conn.logout()
                except Exception:
                    pass

        return results

    def test_connection(self) -> tuple[bool, str]:
        """
        Test IMAP connection. Returns (success, message).
        Useful for the UI to show connection status.
        """
        if not self.is_configured():
            return False, "IMAP credentials not configured in .env"

        try:
            conn = imaplib.IMAP4_SSL(self.imap_server)
            conn.login(self.email_addr, self.email_pass)
            status, folders = conn.list()
            conn.logout()
            return True, f"Connected to {self.imap_server} as {self.email_addr}"
        except imaplib.IMAP4.error as e:
            return False, f"IMAP auth failed: {e}"
        except Exception as e:
            return False, f"Connection failed: {e}"
