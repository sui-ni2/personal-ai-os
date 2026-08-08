from __future__ import annotations

from typing import Any

from personal_ai_os_core import ProjectMetadata, ProjectView


class GeneralProject:
    metadata = ProjectMetadata(
        id="general",
        name="General",
        description="A provider-neutral workspace with no domain-specific schema.",
        icon="sparkles",
    )

    def context(self) -> dict[str, Any]:
        return {"scope": "general", "instructions": ["Use only explicitly granted tools and sources."]}

    def tools(self) -> set[str]:
        return {"system.echo"}

    def views(self) -> list[ProjectView]:
        return [ProjectView(id="overview", label="Overview", route="/projects/general")]

    def artifact_kinds(self) -> set[str]:
        return {"file", "url", "note"}

    def permissions(self) -> dict[str, list[str]]:
        return {"tools": ["system.echo"], "files": []}
