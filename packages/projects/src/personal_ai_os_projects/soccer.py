from __future__ import annotations

from typing import Any

from personal_ai_os_core import ProjectMetadata, ProjectView


_PRIVATE_CONTINUITY_TOOLS = {
    "project.state.snapshot",
    "project.state.history",
    "project.state.put",
    "project.experience.append",
    "project.workflow.list",
    "project.workflow.create",
    "project.workflow.advance",
    "project.workflow.transitions",
}


class SoccerProject:
    """Example plugin. Domain data stays inside plugin-owned context and artifacts."""

    metadata = ProjectMetadata(
        id="soccer",
        name="Soccer",
        description="Example domain plugin for soccer workflows; never a core dependency.",
        icon="ball",
    )

    def context(self) -> dict[str, Any]:
        return {
            "scope": "soccer-plugin",
            "boundary": "Soccer data is plugin-owned and must not change core schemas.",
            "continuity": "Private state/workflow tools are project-bound and contain no public Soccer strategy.",
        }

    def tools(self) -> set[str]:
        return {"system.echo", *_PRIVATE_CONTINUITY_TOOLS}

    def views(self) -> list[ProjectView]:
        return [ProjectView(id="overview", label="Plugin overview", route="/projects/soccer")]

    def artifact_kinds(self) -> set[str]:
        return {"file", "url", "note"}

    def permissions(self) -> dict[str, list[str]]:
        return {"tools": sorted(self.tools()), "files": []}
