"""Read-only git tools the hypothesis engine can call during an
investigation, scoped to a single fixed repo path chosen server-side (never
by the model). Lets the engine look past the single pre-fetched diff when
the actual regression isn't in the most recent commit.
"""

import re
import subprocess

_COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": (
                "List recent commits in the watched repo, most recent first. "
                "Use this to look further back than the single diff you were "
                "given, if it doesn't fully explain the failure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "max_count": {
                        "type": "integer",
                        "description": "Number of commits to return (1-20).",
                        "default": 5,
                    },
                    "path": {
                        "type": "string",
                        "description": "Optional: scope history to this file/path within the repo.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_show",
            "description": "Get the full diff/patch for a specific commit hash from git_log's output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commit_hash": {
                        "type": "string",
                        "description": "Commit hash from a prior git_log call.",
                    },
                },
                "required": ["commit_hash"],
            },
        },
    },
]


def git_log(repo_path, max_count=5, path=None):
    max_count = max(1, min(int(max_count or 5), 20))
    cmd = ["git", "-C", repo_path, "log", f"-{max_count}", "--no-color", "--date=short", "--pretty=format:%H|%ad|%s"]
    if path:
        cmd += ["--", path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        output = result.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"(git_log failed: {exc})"
    if not output:
        return "(no matching commit history)"
    return output


def git_show(repo_path, commit_hash):
    if not _COMMIT_HASH_RE.match(commit_hash or ""):
        return "(invalid commit hash)"
    cmd = ["git", "-C", repo_path, "show", "--no-color", commit_hash]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        output = result.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"(git_show failed: {exc})"
    return output or "(empty diff)"


def call_tool(repo_path, name, arguments):
    if name == "git_log":
        return git_log(repo_path, max_count=arguments.get("max_count", 5), path=arguments.get("path"))
    if name == "git_show":
        return git_show(repo_path, arguments.get("commit_hash", ""))
    return f"(unknown tool: {name})"
