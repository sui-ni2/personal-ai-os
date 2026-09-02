from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ProjectMetadata(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    status: str = "active"


class ProjectView(BaseModel):
    id: str
    label: str
    route: str


class ProjectPlugin(Protocol):
    metadata: ProjectMetadata

    def context(self) -> dict[str, Any]: ...

    def tools(self) -> set[str]: ...

    def views(self) -> list[ProjectView]: ...

    def artifact_kinds(self) -> set[str]: ...

    def permissions(self) -> dict[str, list[str]]: ...


class ProjectRegistry:
    def __init__(self, plugins: list[ProjectPlugin] | None = None) -> None:
        self._plugins: dict[str, ProjectPlugin] = {}
        for plugin in plugins or []:
            self.register(plugin)

    def register(self, plugin: ProjectPlugin) -> None:
        project_id = plugin.metadata.id
        if project_id in self._plugins:
            raise ValueError(f"Project already registered: {project_id}")
        self._plugins[project_id] = plugin

    def unregister(self, project_id: str) -> None:
        """Remove a runtime-only user project after its persisted record was explicitly erased."""
        try:
            del self._plugins[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def get(self, project_id: str) -> ProjectPlugin:
        try:
            return self._plugins[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def list(self) -> list[ProjectMetadata]:
        return [plugin.metadata for plugin in self._plugins.values()]

    def describe(self, project_id: str) -> dict[str, Any]:
        plugin = self.get(project_id)
        return {
            "metadata": plugin.metadata.model_dump(),
            "context": plugin.context(),
            "tools": sorted(plugin.tools()),
            "views": [view.model_dump() for view in plugin.views()],
            "artifact_kinds": sorted(plugin.artifact_kinds()),
            "permissions": plugin.permissions(),
        }
