from __future__ import annotations

import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements-dev.txt"
INTERNAL_PREFIX = "personal-ai-os-"
EXACT_PIN_RE = re.compile(
    r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*==\s*([^\s;]+)"
)


@dataclass(frozen=True)
class Project:
    path: Path
    name: str
    version: str
    dependencies: tuple[str, ...]


def editable_paths() -> list[Path]:
    paths: list[Path] = []
    for raw_line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        value: str | None = None
        if line.startswith("-e "):
            value = line[3:].strip()
        elif line.startswith("--editable "):
            value = line[len("--editable ") :].strip()
        elif line.startswith("-e="):
            value = line[3:].strip()
        elif line.startswith("--editable="):
            value = line[len("--editable=") :].strip()

        if value:
            paths.append((ROOT / value).resolve())

    return paths


def load_project(path: Path) -> Project:
    pyproject = path / "pyproject.toml"
    if not pyproject.is_file():
        raise ValueError(f"editable path has no pyproject.toml: {path.relative_to(ROOT)}")

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})
    name = project.get("name")
    version = project.get("version")
    dependencies = project.get("dependencies", [])

    if not isinstance(name, str) or not name:
        raise ValueError(f"missing [project].name: {pyproject.relative_to(ROOT)}")
    if not isinstance(version, str) or not version:
        raise ValueError(f"missing [project].version: {pyproject.relative_to(ROOT)}")
    if not isinstance(dependencies, list) or not all(
        isinstance(dep, str) for dep in dependencies
    ):
        raise ValueError(f"invalid [project].dependencies: {pyproject.relative_to(ROOT)}")

    return Project(path, name, version, tuple(dependencies))


def main() -> int:
    errors: list[str] = []

    try:
        projects = [load_project(path) for path in editable_paths()]
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        print(f"::error title=Internal package version check::{exc}")
        return 1

    internal = {project.name: project for project in projects if project.name.startswith(INTERNAL_PREFIX)}
    if not internal:
        print("::error title=Internal package version check::No internal editable packages found")
        return 1

    versions = {project.version for project in internal.values()}
    if len(versions) != 1:
        rendered = ", ".join(
            f"{name}={project.version}" for name, project in sorted(internal.items())
        )
        errors.append(f"local package versions are not aligned: {rendered}")
    else:
        expected_version = next(iter(versions))
        for project in internal.values():
            for dependency in project.dependencies:
                dependency_name = dependency.split(";", 1)[0].strip()
                match = EXACT_PIN_RE.match(dependency_name)

                referenced_name: str | None = None
                for name in internal:
                    if dependency_name == name or dependency_name.startswith(
                        (f"{name}==", f"{name} ", f"{name}[")
                    ):
                        referenced_name = name
                        break

                if referenced_name is None:
                    continue

                if match is None or match.group(1) != referenced_name:
                    errors.append(
                        f"{project.name} must pin {referenced_name} exactly to =={expected_version}; "
                        f"found {dependency!r}"
                    )
                    continue

                pinned_version = match.group(2)
                if pinned_version != expected_version:
                    errors.append(
                        f"{project.name} pins {referenced_name}=={pinned_version}, "
                        f"but local version is {expected_version}"
                    )

    if errors:
        for error in errors:
            print(f"::error title=Internal package version check::{error}")
        return 1

    expected_version = next(iter(versions))
    names = ", ".join(sorted(internal))
    print(
        f"Internal package version check passed: {len(internal)} packages at "
        f"v{expected_version} ({names})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
