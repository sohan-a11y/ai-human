"""
Git Integration Tool — full git workflow support for the AI Human agent.

Supports:
  - clone, init, status, diff, add, commit, push, pull
  - branch (create, list, switch, delete)
  - merge, rebase
  - log (with formatting options)
  - stash, pop
  - create/list PRs (via GitHub CLI `gh` if available)
  - show file at a specific commit
  - find commits by message/author/date
"""

from __future__ import annotations
import subprocess
import os
from pathlib import Path
from tools.base_tool import BaseTool


def _run_git(args: list[str], cwd: str = ".", timeout: int = 60) -> tuple[bool, str]:
    """Run a git command. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output = result.stderr.strip() if not output else output + "\n" + result.stderr.strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, "git not found — install Git from https://git-scm.com"
    except subprocess.TimeoutExpired:
        return False, f"git command timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


class GitTool(BaseTool):
    name = "git"
    description = (
        "Full git workflow: clone, commit, push, pull, branch, merge, PR creation, log, diff, stash. "
        "Specify 'action' and optionally 'repo_path', 'message', 'branch', 'remote', 'args'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "status", "diff", "add", "commit", "push", "pull",
                    "clone", "init", "log", "branch", "checkout", "merge",
                    "stash", "stash_pop", "rebase", "reset", "show",
                    "create_pr", "list_prs", "search_commits", "tag",
                ],
            },
            "repo_path": {"type": "string", "default": "."},
            "message": {"type": "string", "description": "Commit message"},
            "branch": {"type": "string", "description": "Branch name"},
            "remote": {"type": "string", "default": "origin"},
            "url": {"type": "string", "description": "For clone"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "Files for git add"},
            "args": {"type": "string", "description": "Extra args passed directly to git"},
            "pr_title": {"type": "string"},
            "pr_body": {"type": "string"},
            "base_branch": {"type": "string", "default": "main"},
            "search_query": {"type": "string", "description": "For search_commits"},
        },
        "required": ["action"],
    }

    def run(
        self,
        action: str,
        repo_path: str = ".",
        message: str = "",
        branch: str = "",
        remote: str = "origin",
        url: str = "",
        files: list | None = None,
        args: str = "",
        pr_title: str = "",
        pr_body: str = "",
        base_branch: str = "main",
        search_query: str = "",
    ) -> str:
        cwd = str(Path(repo_path).resolve())

        if action == "status":
            ok, out = _run_git(["status", "--short", "--branch"], cwd)
            return out

        elif action == "diff":
            extra = args.split() if args else []
            ok, out = _run_git(["diff"] + extra, cwd)
            return out or "No changes"

        elif action == "add":
            targets = files if files else ([args] if args else ["."])
            ok, out = _run_git(["add"] + targets, cwd)
            return out or "Files staged"

        elif action == "commit":
            if not message:
                return "Error: commit message required"
            ok, out = _run_git(["commit", "-m", message], cwd)
            return out

        elif action == "push":
            extra = ["--set-upstream", remote, branch] if branch else [remote]
            ok, out = _run_git(["push"] + extra, cwd)
            return out

        elif action == "pull":
            extra = [remote, branch] if branch else [remote]
            ok, out = _run_git(["pull"] + extra, cwd)
            return out

        elif action == "clone":
            if not url:
                return "Error: url required for clone"
            target = args if args else Path(url).stem
            ok, out = _run_git(["clone", url, target], cwd)
            return out

        elif action == "init":
            ok, out = _run_git(["init"], cwd)
            return out

        elif action == "log":
            n = args if args else "20"
            ok, out = _run_git([
                "log", f"-{n}",
                "--pretty=format:%h %ad %an: %s",
                "--date=short",
            ], cwd)
            return out or "No commits"

        elif action == "branch":
            if branch:
                # Create branch
                ok, out = _run_git(["checkout", "-b", branch], cwd)
                return out
            else:
                ok, out = _run_git(["branch", "-a"], cwd)
                return out

        elif action == "checkout":
            if not branch:
                return "Error: branch name required"
            ok, out = _run_git(["checkout", branch], cwd)
            return out

        elif action == "merge":
            if not branch:
                return "Error: branch to merge required"
            ok, out = _run_git(["merge", branch], cwd)
            return out

        elif action == "stash":
            msg_args = ["-m", message] if message else []
            ok, out = _run_git(["stash", "push"] + msg_args, cwd)
            return out

        elif action == "stash_pop":
            ok, out = _run_git(["stash", "pop"], cwd)
            return out

        elif action == "rebase":
            target = branch or base_branch
            ok, out = _run_git(["rebase", target], cwd)
            return out

        elif action == "reset":
            extra = args.split() if args else ["HEAD~1", "--soft"]
            ok, out = _run_git(["reset"] + extra, cwd)
            return out

        elif action == "show":
            target = args or "HEAD"
            ok, out = _run_git(["show", target, "--stat"], cwd)
            return out

        elif action == "tag":
            if not args:
                ok, out = _run_git(["tag", "-l"], cwd)
                return out
            tag_args = args.split()
            if message:
                tag_args += ["-m", message]
            ok, out = _run_git(["tag"] + tag_args, cwd)
            return out

        elif action == "search_commits":
            if not search_query:
                return "Error: search_query required"
            ok, out = _run_git([
                "log", "--all", f"--grep={search_query}",
                "--pretty=format:%h %ad %an: %s", "--date=short",
            ], cwd)
            return out or f"No commits matching '{search_query}'"

        elif action == "create_pr":
            # Uses GitHub CLI
            if not pr_title:
                pr_title = f"PR from {branch or 'current branch'}"
            body = pr_body or ""
            ok, out = self._gh_cli(
                ["pr", "create", "--title", pr_title, "--body", body,
                 "--base", base_branch],
                cwd=cwd
            )
            return out

        elif action == "list_prs":
            ok, out = self._gh_cli(["pr", "list", "--state", "open"], cwd=cwd)
            return out

        return f"Unknown action: {action}"

    def _gh_cli(self, args: list[str], cwd: str = ".") -> tuple[bool, str]:
        """Run GitHub CLI command."""
        try:
            result = subprocess.run(
                ["gh"] + args,
                cwd=cwd, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except FileNotFoundError:
            return False, "GitHub CLI (gh) not installed. See: https://cli.github.com"
        except Exception as e:
            return False, str(e)
