from personal_ai_os_core import ProjectRegistry

from .general import GeneralProject
from .soccer import SoccerProject


def create_project_registry(include_soccer: bool = True) -> ProjectRegistry:
    plugins = [GeneralProject()]
    if include_soccer:
        plugins.append(SoccerProject())
    return ProjectRegistry(plugins)
