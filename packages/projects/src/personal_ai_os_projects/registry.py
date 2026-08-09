from pathlib import Path

from personal_ai_os_core import ProjectRegistry

from .general import GeneralProject
from .p5 import P5Project
from .soccer import SoccerProject


def create_project_registry(
    include_soccer: bool = True,
    include_p5: bool = True,
    data_dir: Path | None = None,
) -> ProjectRegistry:
    plugins = [GeneralProject()]
    if include_soccer:
        plugins.append(SoccerProject())
    if include_p5:
        storage_path = (data_dir / "projects" / "p5" / "p5.db") if data_dir else None
        plugins.append(P5Project(storage_path))
    return ProjectRegistry(plugins)
