"""
API Integrations — Gmail, Slack, GitHub, Google Calendar.
Each uses only standard/free APIs. Keys configured in .env.
"""

from __future__ import annotations
from tools.base_tool import BaseTool


# ── GMAIL ────────────────────────────────────────────────────────────────────

class GmailReadTool(BaseTool):
    name = "gmail_read"
    description = "Read recent Gmail emails. Returns subject, sender, snippet."
    parameters = {"type": "object", "properties": {
        "max_results": {"type": "integer", "default": 10},
        "query": {"type": "string", "default": "is:unread"},
    }}

    def run(self, max_results: int = 10, query: str = "is:unread") -> str:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            import json
            from pathlib import Path

            token_file = Path("data/gmail_token.json")
            if not token_file.exists():
                return "Gmail not configured. Run: python setup_gmail.py"

            creds = Credentials.from_authorized_user_file(str(token_file))
            service = build("gmail", "v1", credentials=creds)
            results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
            messages = results.get("messages", [])

            output = []
            for msg in messages[:max_results]:
                m = service.users().messages().get(userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["Subject", "From"]).execute()
                headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
                output.append(f"From: {headers.get('From','?')}\nSubject: {headers.get('Subject','?')}\nSnippet: {m.get('snippet','')[:100]}")
            return "\n\n".join(output) if output else "No messages found"
        except ImportError:
            return "Requires: pip install google-api-python-client google-auth-oauthlib"
        except Exception as e:
            return f"Gmail error: {e}"


class GmailSendTool(BaseTool):
    name = "gmail_send"
    description = "Send an email via Gmail."
    parameters = {"type": "object", "properties": {
        "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"},
    }, "required": ["to", "subject", "body"]}

    def run(self, to: str, subject: str, body: str) -> str:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            import base64
            from email.mime.text import MIMEText
            from pathlib import Path

            creds = Credentials.from_authorized_user_file("data/gmail_token.json")
            service = build("gmail", "v1", credentials=creds)
            msg = MIMEText(body)
            msg["to"] = to
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return f"Email sent to {to}"
        except Exception as e:
            return f"Gmail send error: {e}"


# ── SLACK ─────────────────────────────────────────────────────────────────────

class SlackSendTool(BaseTool):
    name = "slack_send"
    description = "Send a message to a Slack channel."
    parameters = {"type": "object", "properties": {
        "channel": {"type": "string", "description": "#channel-name"},
        "message": {"type": "string"},
    }, "required": ["channel", "message"]}

    def run(self, channel: str, message: str) -> str:
        import os
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return "Set SLACK_BOT_TOKEN in .env"
        try:
            import requests
            resp = requests.post("https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}"},
                json={"channel": channel, "text": message}, timeout=10)
            data = resp.json()
            return "Sent" if data.get("ok") else f"Slack error: {data.get('error')}"
        except Exception as e:
            return f"Slack error: {e}"


class SlackReadTool(BaseTool):
    name = "slack_read"
    description = "Read recent messages from a Slack channel."
    parameters = {"type": "object", "properties": {
        "channel": {"type": "string"}, "limit": {"type": "integer", "default": 10},
    }, "required": ["channel"]}

    def run(self, channel: str, limit: int = 10) -> str:
        import os
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return "Set SLACK_BOT_TOKEN in .env"
        try:
            import requests
            resp = requests.get("https://slack.com/api/conversations.history",
                headers={"Authorization": f"Bearer {token}"},
                params={"channel": channel, "limit": limit}, timeout=10)
            data = resp.json()
            if not data.get("ok"):
                return f"Error: {data.get('error')}"
            msgs = data.get("messages", [])
            return "\n".join(f"[{m.get('ts','')}] {m.get('text','')}" for m in msgs)
        except Exception as e:
            return f"Slack error: {e}"


# ── GITHUB ────────────────────────────────────────────────────────────────────

class GitHubTool(BaseTool):
    name = "github"
    description = "Interact with GitHub: list issues, PRs, check CI status, create issues."
    parameters = {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["list_issues", "list_prs", "create_issue", "get_ci_status"]},
        "repo": {"type": "string", "description": "owner/repo"},
        "title": {"type": "string"}, "body": {"type": "string"},
        "pr_number": {"type": "integer"},
    }, "required": ["action", "repo"]}

    def run(self, action: str, repo: str, title: str = "", body: str = "", pr_number: int = 0) -> str:
        import os, requests
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Authorization": f"token {token}"} if token else {}
        base = f"https://api.github.com/repos/{repo}"

        try:
            if action == "list_issues":
                r = requests.get(f"{base}/issues", headers=headers, params={"state": "open", "per_page": 10})
                return "\n".join(f"#{i['number']} {i['title']}" for i in r.json())
            elif action == "list_prs":
                r = requests.get(f"{base}/pulls", headers=headers, params={"state": "open", "per_page": 10})
                return "\n".join(f"#{p['number']} {p['title']}" for p in r.json())
            elif action == "create_issue":
                r = requests.post(f"{base}/issues", headers=headers, json={"title": title, "body": body})
                data = r.json()
                return f"Issue created: #{data.get('number')} {data.get('html_url','')}"
            elif action == "get_ci_status":
                r = requests.get(f"{base}/actions/runs", headers=headers, params={"per_page": 5})
                runs = r.json().get("workflow_runs", [])
                return "\n".join(f"{run['name']}: {run['conclusion'] or run['status']}" for run in runs)
        except Exception as e:
            return f"GitHub error: {e}"
        return "Unknown action"


# ── GOOGLE CALENDAR ──────────────────────────────────────────────────────────

class CalendarReadTool(BaseTool):
    name = "calendar_read"
    description = "Read upcoming events from Google Calendar."
    parameters = {"type": "object", "properties": {"days": {"type": "integer", "default": 7}}}

    def run(self, days: int = 7) -> str:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            import datetime

            creds = Credentials.from_authorized_user_file("data/calendar_token.json")
            service = build("calendar", "v3", credentials=creds)

            now = datetime.datetime.utcnow().isoformat() + "Z"
            end = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).isoformat() + "Z"

            result = service.events().list(
                calendarId="primary", timeMin=now, timeMax=end,
                singleEvents=True, orderBy="startTime", maxResults=20
            ).execute()
            events = result.get("items", [])
            return "\n".join(
                f"{e['start'].get('dateTime', e['start'].get('date'))}: {e.get('summary','?')}"
                for e in events
            ) or "No upcoming events"
        except ImportError:
            return "Requires: pip install google-api-python-client google-auth-oauthlib"
        except Exception as e:
            return f"Calendar error: {e}"
