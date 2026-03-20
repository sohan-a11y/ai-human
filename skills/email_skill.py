"""Email skill pack — send/receive email via SMTP/IMAP (works with any provider)."""

from tools.base_tool import BaseTool


class EmailSendTool(BaseTool):
    name = "email_send"
    description = "Send an email via SMTP. Supports Gmail, Outlook, custom SMTP servers."
    parameters = {"type": "object", "properties": {
        "to": {"type": "string", "description": "Recipient email address(es), comma-separated"},
        "subject": {"type": "string"},
        "body": {"type": "string"},
        "smtp_server": {"type": "string", "default": "smtp.gmail.com"},
        "smtp_port": {"type": "integer", "default": 587},
        "username": {"type": "string", "default": "", "description": "SMTP username (or set EMAIL_USER env)"},
        "password": {"type": "string", "default": "", "description": "SMTP password/app password (or set EMAIL_PASS env)"},
        "attachments": {"type": "string", "default": "", "description": "Comma-separated file paths to attach"},
        "html": {"type": "boolean", "default": False, "description": "Send body as HTML"},
    }, "required": ["to", "subject", "body"]}

    def run(self, to: str, subject: str, body: str, smtp_server: str = "smtp.gmail.com",
            smtp_port: int = 587, username: str = "", password: str = "",
            attachments: str = "", html: bool = False) -> str:
        import os
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        from pathlib import Path

        user = username or os.environ.get("EMAIL_USER", "")
        pwd = password or os.environ.get("EMAIL_PASS", "")
        if not user or not pwd:
            return "Error: Set EMAIL_USER and EMAIL_PASS env vars, or pass username/password."

        try:
            msg = MIMEMultipart()
            msg["From"] = user
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html" if html else "plain"))

            if attachments:
                for path_str in attachments.split(","):
                    path = Path(path_str.strip())
                    if path.exists():
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(path.read_bytes())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={path.name}")
                        msg.attach(part)

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(user, pwd)
                server.sendmail(user, [r.strip() for r in to.split(",")], msg.as_string())
            return f"Email sent to {to}"
        except Exception as e:
            return f"Error sending email: {e}"


class EmailReadTool(BaseTool):
    name = "email_read"
    description = "Read emails from an IMAP inbox. Returns recent unread messages."
    parameters = {"type": "object", "properties": {
        "imap_server": {"type": "string", "default": "imap.gmail.com"},
        "username": {"type": "string", "default": ""},
        "password": {"type": "string", "default": ""},
        "folder": {"type": "string", "default": "INBOX"},
        "count": {"type": "integer", "default": 5, "description": "Number of recent emails to fetch"},
        "unread_only": {"type": "boolean", "default": True},
    }, "required": []}

    def run(self, imap_server: str = "imap.gmail.com", username: str = "",
            password: str = "", folder: str = "INBOX", count: int = 5,
            unread_only: bool = True) -> str:
        import os
        import imaplib
        import email
        from email.header import decode_header

        user = username or os.environ.get("EMAIL_USER", "")
        pwd = password or os.environ.get("EMAIL_PASS", "")
        if not user or not pwd:
            return "Error: Set EMAIL_USER and EMAIL_PASS env vars."

        try:
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(user, pwd)
            mail.select(folder)

            criteria = "UNSEEN" if unread_only else "ALL"
            status, data = mail.search(None, criteria)
            ids = data[0].split()

            if not ids:
                return "No emails found."

            results = []
            for eid in ids[-count:]:
                _, msg_data = mail.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                subject = ""
                raw_subject = decode_header(msg["Subject"] or "")
                for part, enc in raw_subject:
                    if isinstance(part, bytes):
                        subject += part.decode(enc or "utf-8", errors="replace")
                    else:
                        subject += part

                from_addr = msg.get("From", "")
                date = msg.get("Date", "")

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="replace")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="replace")

                results.append(f"From: {from_addr}\nDate: {date}\nSubject: {subject}\n{body[:500]}\n---")

            mail.logout()
            return "\n".join(results) if results else "No emails found."
        except Exception as e:
            return f"Error reading email: {e}"


class EmailSearchTool(BaseTool):
    name = "email_search"
    description = "Search emails by subject, sender, or date range."
    parameters = {"type": "object", "properties": {
        "query": {"type": "string", "description": "Search query (subject keywords)"},
        "from_addr": {"type": "string", "default": "", "description": "Filter by sender"},
        "since": {"type": "string", "default": "", "description": "Date filter, e.g. '01-Jan-2024'"},
        "count": {"type": "integer", "default": 10},
        "imap_server": {"type": "string", "default": "imap.gmail.com"},
        "username": {"type": "string", "default": ""},
        "password": {"type": "string", "default": ""},
    }, "required": ["query"]}

    def run(self, query: str, from_addr: str = "", since: str = "",
            count: int = 10, imap_server: str = "imap.gmail.com",
            username: str = "", password: str = "") -> str:
        import os
        import imaplib
        import email
        from email.header import decode_header

        user = username or os.environ.get("EMAIL_USER", "")
        pwd = password or os.environ.get("EMAIL_PASS", "")
        if not user or not pwd:
            return "Error: Set EMAIL_USER and EMAIL_PASS env vars."

        try:
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(user, pwd)
            mail.select("INBOX")

            criteria_parts = [f'SUBJECT "{query}"']
            if from_addr:
                criteria_parts.append(f'FROM "{from_addr}"')
            if since:
                criteria_parts.append(f'SINCE "{since}"')

            criteria = " ".join(criteria_parts)
            status, data = mail.search(None, criteria)
            ids = data[0].split()

            if not ids:
                mail.logout()
                return "No matching emails found."

            results = []
            for eid in ids[-count:]:
                _, msg_data = mail.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                subject = ""
                raw_subject = decode_header(msg["Subject"] or "")
                for part, enc in raw_subject:
                    if isinstance(part, bytes):
                        subject += part.decode(enc or "utf-8", errors="replace")
                    else:
                        subject += part
                results.append(f"From: {msg.get('From', '')} | {msg.get('Date', '')} | {subject}")

            mail.logout()
            return f"Found {len(ids)} results:\n" + "\n".join(results)
        except Exception as e:
            return f"Error: {e}"
