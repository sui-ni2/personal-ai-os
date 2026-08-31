from __future__ import annotations

from typing import Any

from personal_ai_os_core import ProjectMetadata, ProjectView


class UserProject:
    """A tenant-owned, domain-neutral project that keeps the standard plugin contract."""

    def __init__(self, metadata: ProjectMetadata) -> None:
        self.metadata = metadata

    def context(self) -> dict[str, Any]:
        return {
            "scope": "user_project",
            "instructions": [
                "Use only explicitly granted tools and sources.",
                "Keep durable project state separate from provider conversation history.",
            ],
        }

    def tools(self) -> set[str]:
        return {"system.echo", "external:*"}

    def views(self) -> list[ProjectView]:
        return [ProjectView(id="overview", label="Overview", route=f"/projects/{self.metadata.id}")]

    def artifact_kinds(self) -> set[str]:
        return {"file", "url", "note"}

    def permissions(self) -> dict[str, list[str]]:
        return {"tools": ["system.echo", "external:*"], "files": []}
