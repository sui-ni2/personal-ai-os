from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".local-state" / "codex-handoff"
FACTS_JSON = STATE_DIR / "facts.json"
FACTS_MD = STATE_DIR / "FACTS.md"
HANDOFF_MD = STATE_DIR / "HANDOFF.md"
MAX_STATUS_LINES = 200
MAX_COMMITS = 5

SENSITIVE_PARTS = {
    ".env",
    ".secrets",
    "secrets",
    "credentials",
    "cookies",
    "browser-profiles",
}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.rstrip("\r\n")


def safe_path(raw: str) -> str:
    path = raw.strip().strip('"')
    lowered = path.lower().replace("\\", "/")
    parts = {part for part in lowered.split("/") if part}
    if parts & SENSITIVE_PARTS or any(lowered.endswith(suffix) for suffix in SENSITIVE_SUFFIXES):
        return "[sensitive path omitted]"
    return path


def status_items(raw: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for line in raw.splitlines()[:MAX_STATUS_LINES]:
        if len(line) < 3:
            continue
        code = line[:2]
        raw_path = line[3:]
        if " -> " in raw_path:
            old, new = raw_path.split(" -> ", 1)
            path = f"{safe_path(old)} -> {safe_path(new)}"
        else:
            path = safe_path(raw_path)
        items.append({"status": code, "path": path})
    return items


def recent_commits(raw: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in raw.splitlines()[:MAX_COMMITS]:
        sha, _, subject = line.partition("\t")
        rows.append({"sha": sha, "subject": subject})
    return rows


def ensure_handoff_template() -> None:
    if HANDOFF_MD.exists():
        return
    HANDOFF_MD.write_text(
        "# Codex Account Handoff\n\n"
        "Update this file only with compact semantic context that Git cannot reconstruct. "
        "Do not copy chat transcripts, credentials, tokens, cookies, or private reasoning.\n\n"
        "## Objective\n- Pending first handoff.\n\n"
        "## Completed\n- None recorded yet.\n\n"
        "## Decisions / constraints\n- None recorded yet.\n\n"
        "## Blockers\n- None recorded yet.\n\n"
        "## Next action\n- Inspect `FACTS.md`, then reconstruct the active task from the changed files.\n",
        encoding="utf-8",
    )


def main() -> int:
    top = Path(git("rev-parse", "--show-toplevel")).resolve()
    if top != ROOT.resolve():
        raise RuntimeError(f"Repository root mismatch: expected {ROOT}, got {top}")

    timestamp = datetime.now(timezone.utc).isoformat()
    branch = git("branch", "--show-current") or "(detached HEAD)"
    head = git("rev-parse", "HEAD")
    status = status_items(git("status", "--porcelain=v1", "--untracked-files=all"))
    unstaged = git("diff", "--shortstat", "--") or "clean"
    staged = git("diff", "--cached", "--shortstat", "--") or "clean"
    commits = recent_commits(git("log", f"-{MAX_COMMITS}", "--pretty=format:%h%x09%s"))

    payload = {
        "schema": 1,
        "generated_at": timestamp,
        "repository": ROOT.name,
        "branch": branch,
        "head": head,
        "dirty": bool(status),
        "status": status,
        "unstaged_summary": unstaged,
        "staged_summary": staged,
        "recent_commits": commits,
        "note": "Facts only; no file contents, credentials, chat transcript, or private reasoning are captured.",
    }

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    FACTS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status_lines = [f"- `{item['status']}` `{item['path']}`" for item in status] or ["- Working tree clean."]
    commit_lines = [f"- `{item['sha']}` {item['subject']}" for item in commits] or ["- No commits found."]
    FACTS_MD.write_text(
        "\n".join(
            [
                "# Codex Handoff Facts",
                "",
                f"Generated: `{timestamp}`",
                f"Branch: `{branch}`",
                f"HEAD: `{head}`",
                f"Unstaged: {unstaged}",
                f"Staged: {staged}",
                "",
                "## Working tree",
                *status_lines,
                "",
                "## Recent commits",
                *commit_lines,
                "",
                "> Local-only factual snapshot. No source-file contents or secrets are copied into this file.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    ensure_handoff_template()
    print(FACTS_MD.relative_to(ROOT))
    print(HANDOFF_MD.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
