"""
Task Templates Library — pre-built goal templates for common recurring workflows.

Built-in templates:
  - morning_briefing: Check emails, calendar, news, weather summary
  - end_of_day_report: Summarize what was done, pending tasks, tomorrow's plan
  - project_setup: Create folder structure, init git, create README, setup venv
  - code_review: Review recent git changes, run tests, check for issues
  - weekly_backup: Backup important directories to archive
  - research_topic: Deep research on a topic and save report
  - system_health: Check CPU, RAM, disk, running processes
  - inbox_zero: Read all emails, categorize, draft responses for important ones
  - daily_standup: Generate standup summary from recent git commits
  - learn_new_skill: Research and practice a new programming skill

Templates are parameterized with placeholders like {project_name}, {email}, etc.
Users can save custom templates.
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class TaskTemplate:
    id: str
    name: str
    description: str
    goal_template: str          # Goal text with {placeholders}
    parameters: dict[str, str]  # {param_name: description}
    category: str               # "productivity" | "development" | "research" | "system" | "communication"
    estimated_minutes: int      # Rough estimate
    is_builtin: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)

    def instantiate(self, **kwargs) -> str:
        """Fill in placeholders and return a ready-to-run goal."""
        goal = self.goal_template
        for key, value in kwargs.items():
            goal = goal.replace(f"{{{key}}}", str(value))
        # Fill remaining placeholders with defaults from parameters
        for param_name, param_desc in self.parameters.items():
            if f"{{{param_name}}}" in goal:
                goal = goal.replace(f"{{{param_name}}}", f"[{param_name}]")
        return goal


# ── Built-in Templates ────────────────────────────────────────────────────────

BUILTIN_TEMPLATES: list[TaskTemplate] = [
    TaskTemplate(
        id="morning_briefing",
        name="Morning Briefing",
        description="Start the day with a comprehensive overview of emails, calendar, news",
        goal_template=(
            "Good morning! Give me my morning briefing:\n"
            "1. Check Gmail for unread emails and summarize the top {max_emails} most important\n"
            "2. Check Google Calendar for today's events\n"
            "3. Check the weather for {city}\n"
            "4. Search for top news headlines in {topics}\n"
            "5. Summarize everything in a concise morning brief"
        ),
        parameters={
            "max_emails": "Number of emails to show (default: 5)",
            "city": "Your city for weather (default: current location)",
            "topics": "News topics of interest (default: technology, world news)",
        },
        category="productivity",
        estimated_minutes=5,
        tags=["daily", "email", "calendar", "news"],
    ),

    TaskTemplate(
        id="end_of_day_report",
        name="End of Day Report",
        description="Summarize the day's work and plan for tomorrow",
        goal_template=(
            "Create my end of day report:\n"
            "1. Look at {project_dir} git log for today's commits\n"
            "2. Review the task completion log for today\n"
            "3. List what was accomplished\n"
            "4. List what's still pending\n"
            "5. Draft a plan for tomorrow\n"
            "6. Save the report to {output_file}"
        ),
        parameters={
            "project_dir": "Directory of your main project (default: current directory)",
            "output_file": "Where to save the report (default: data/eod_report.md)",
        },
        category="productivity",
        estimated_minutes=10,
        tags=["daily", "report", "planning"],
    ),

    TaskTemplate(
        id="project_setup",
        name="New Project Setup",
        description="Set up a complete new project with proper structure",
        goal_template=(
            "Set up a new {language} project called '{project_name}':\n"
            "1. Create directory structure at {base_dir}/{project_name}\n"
            "2. Initialize git repository\n"
            "3. Create README.md with project description: {description}\n"
            "4. Set up {language} environment ({setup_commands})\n"
            "5. Create .gitignore for {language}\n"
            "6. Make initial commit with message 'Initial project setup'\n"
            "7. Open the project in VS Code"
        ),
        parameters={
            "project_name": "Name of the project",
            "language": "Programming language (Python, Node.js, etc.)",
            "base_dir": "Where to create the project (default: ~/Projects)",
            "description": "Short project description",
            "setup_commands": "Setup commands (e.g., 'python -m venv venv')",
        },
        category="development",
        estimated_minutes=15,
        tags=["git", "setup", "development"],
    ),

    TaskTemplate(
        id="code_review",
        name="Code Review",
        description="Review recent code changes and check for issues",
        goal_template=(
            "Review the code in {repo_path}:\n"
            "1. Run 'git diff {base_branch}' to see all changes\n"
            "2. Run the test suite: {test_command}\n"
            "3. Check for common issues: syntax errors, security vulnerabilities, code style\n"
            "4. Check if new code has proper error handling\n"
            "5. Write a code review report with: summary, issues found, suggestions\n"
            "6. Save review to {output_file}"
        ),
        parameters={
            "repo_path": "Path to the repository",
            "base_branch": "Base branch to compare against (default: main)",
            "test_command": "Command to run tests (default: pytest)",
            "output_file": "Where to save review (default: data/code_review.md)",
        },
        category="development",
        estimated_minutes=20,
        tags=["git", "testing", "code quality"],
    ),

    TaskTemplate(
        id="research_topic",
        name="Deep Research",
        description="Thoroughly research a topic and save a comprehensive report",
        goal_template=(
            "Research the following topic thoroughly: {topic}\n"
            "1. Search the web for recent information about {topic}\n"
            "2. Find {num_sources} different reliable sources\n"
            "3. Read and summarize each source\n"
            "4. Synthesize the information into a coherent overview\n"
            "5. Include: key concepts, current state, trends, practical applications\n"
            "6. Save a comprehensive Markdown report to {output_file}\n"
            "7. Also save a brief executive summary (1 page)"
        ),
        parameters={
            "topic": "Topic to research",
            "num_sources": "Number of sources to consult (default: 5)",
            "output_file": "Where to save the report (default: data/research_{topic}.md)",
        },
        category="research",
        estimated_minutes=30,
        tags=["research", "web", "report"],
    ),

    TaskTemplate(
        id="system_health",
        name="System Health Check",
        description="Check system resources and running processes",
        goal_template=(
            "Run a complete system health check:\n"
            "1. Check CPU usage (flag if >80% average)\n"
            "2. Check RAM usage (flag if >85%)\n"
            "3. Check disk space on all drives (flag if <10GB free)\n"
            "4. List top 10 CPU-consuming processes\n"
            "5. Check if important services are running: {services_to_check}\n"
            "6. Check network connectivity\n"
            "7. Generate a health report and {action_if_issues}"
        ),
        parameters={
            "services_to_check": "Services to verify are running (e.g., 'nginx, postgresql')",
            "action_if_issues": "What to do if issues found (default: alert and log)",
        },
        category="system",
        estimated_minutes=5,
        tags=["monitoring", "system", "health"],
    ),

    TaskTemplate(
        id="inbox_zero",
        name="Inbox Zero",
        description="Process all emails and achieve inbox zero",
        goal_template=(
            "Help me achieve inbox zero:\n"
            "1. Read all unread emails from Gmail\n"
            "2. Categorize each as: urgent, important, low priority, spam/newsletter\n"
            "3. For urgent emails: draft a response and show me for approval\n"
            "4. For newsletters/spam: mark as read or unsubscribe\n"
            "5. Create a summary of action items from important emails\n"
            "6. Save the email summary to {output_file}"
        ),
        parameters={
            "output_file": "Where to save summary (default: data/email_summary.md)",
        },
        category="communication",
        estimated_minutes=20,
        tags=["email", "gmail", "productivity"],
    ),

    TaskTemplate(
        id="daily_standup",
        name="Daily Standup Generator",
        description="Generate standup notes from recent git activity",
        goal_template=(
            "Generate my daily standup report:\n"
            "1. Look at git log for {repo_path} for the last 24 hours\n"
            "2. Look at git log for any other repos: {other_repos}\n"
            "3. Check my calendar for yesterday's meetings\n"
            "4. Generate standup in this format:\n"
            "   - What I did yesterday\n"
            "   - What I'm doing today\n"
            "   - Any blockers\n"
            "5. Post to {slack_channel} Slack channel if configured"
        ),
        parameters={
            "repo_path": "Main repository path",
            "other_repos": "Other repos to check (comma-separated paths)",
            "slack_channel": "Slack channel to post to (optional)",
        },
        category="communication",
        estimated_minutes=5,
        tags=["standup", "git", "slack"],
    ),

    TaskTemplate(
        id="weekly_backup",
        name="Weekly Backup",
        description="Backup important directories to a timestamped archive",
        goal_template=(
            "Perform weekly backup:\n"
            "1. Create backup archive at {backup_dir}/backup_{date}.zip\n"
            "2. Include directories: {dirs_to_backup}\n"
            "3. Exclude: {exclude_patterns}\n"
            "4. Verify the archive is not corrupted\n"
            "5. Delete backups older than {retention_days} days\n"
            "6. Report: backup size, duration, files backed up"
        ),
        parameters={
            "backup_dir": "Where to store backups (default: D:/Backups)",
            "dirs_to_backup": "Directories to backup (comma-separated)",
            "exclude_patterns": "Patterns to exclude (default: __pycache__, .git, node_modules)",
            "retention_days": "How many days to keep old backups (default: 30)",
        },
        category="system",
        estimated_minutes=15,
        tags=["backup", "system", "files"],
    ),

    TaskTemplate(
        id="learn_new_skill",
        name="Learn New Skill",
        description="Research, learn, and practice a new programming skill",
        goal_template=(
            "Help me learn: {skill}\n"
            "1. Search for the best tutorials and documentation on {skill}\n"
            "2. Summarize the key concepts in plain language\n"
            "3. Create a simple example/demo project at {project_dir}\n"
            "4. Write the example code and test it works\n"
            "5. Create a cheat sheet saved to {cheat_sheet_file}\n"
            "6. Suggest 3 practice exercises to reinforce learning"
        ),
        parameters={
            "skill": "Skill or technology to learn",
            "project_dir": "Where to create demo (default: data/learning_demos/{skill})",
            "cheat_sheet_file": "Cheat sheet path (default: docs/cheat_{skill}.md)",
        },
        category="research",
        estimated_minutes=45,
        tags=["learning", "practice", "development"],
    ),
]


class TaskTemplateLibrary:
    """Manage built-in and custom task templates."""

    def __init__(self, templates_file: str = "data/custom_templates.json"):
        self._templates_file = Path(templates_file)
        self._templates_file.parent.mkdir(parents=True, exist_ok=True)
        self._builtin: dict[str, TaskTemplate] = {t.id: t for t in BUILTIN_TEMPLATES}
        self._custom: dict[str, TaskTemplate] = {}
        self._load_custom()

    def get(self, template_id: str) -> Optional[TaskTemplate]:
        return self._custom.get(template_id) or self._builtin.get(template_id)

    def list_all(self) -> list[TaskTemplate]:
        templates = list(self._builtin.values()) + list(self._custom.values())
        return sorted(templates, key=lambda t: t.name)

    def list_by_category(self, category: str) -> list[TaskTemplate]:
        return [t for t in self.list_all() if t.category == category]

    def search(self, query: str) -> list[TaskTemplate]:
        query_lower = query.lower()
        return [
            t for t in self.list_all()
            if query_lower in t.name.lower()
            or query_lower in t.description.lower()
            or any(query_lower in tag for tag in t.tags)
        ]

    def instantiate(self, template_id: str, **params) -> Optional[str]:
        """Get a filled-in goal from a template."""
        template = self.get(template_id)
        if not template:
            return None
        return template.instantiate(**params)

    def save_custom(self, template: TaskTemplate) -> None:
        """Save a custom template."""
        template.is_builtin = False
        self._custom[template.id] = template
        self._save_custom()

    def delete_custom(self, template_id: str) -> bool:
        if template_id in self._custom:
            del self._custom[template_id]
            self._save_custom()
            return True
        return False

    def to_summary_list(self) -> str:
        """Return formatted list of all templates for agent context."""
        lines = ["Available Task Templates:"]
        for t in self.list_all():
            lines.append(f"  [{t.id}] {t.name} ({t.category}, ~{t.estimated_minutes}min) — {t.description}")
        return "\n".join(lines)

    def _load_custom(self) -> None:
        if not self._templates_file.exists():
            return
        try:
            data = json.loads(self._templates_file.read_text())
            for item in data:
                t = TaskTemplate(**item)
                self._custom[t.id] = t
        except Exception:
            pass

    def _save_custom(self) -> None:
        data = [asdict(t) for t in self._custom.values()]
        self._templates_file.write_text(json.dumps(data, indent=2))
