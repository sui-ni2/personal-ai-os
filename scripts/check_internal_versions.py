from __future__ import annotations

import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements-dev.txt"
RUNTIME_VERSION_FILE = ROOT / "apps" / "api" / "src" / "personal_ai_os" / "__init__.py"
WEB_PACKAGE_FILE = ROOT / "apps" / "web" / "package.json"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
README_FILE = ROOT / "README.md"
SECURITY_FILE = ROOT / "SECURITY.md"
INTERNAL_PREFIX = "personal-ai-os-"
EXACT_PIN_RE = re.compile(
    r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*==\s*([^\s;]+)"
)
RUNTIME_VERSION_RE = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$', re.MULTILINE)
SEMVER_RE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)
CHANGELOG_RELEASE_RE = re.compile(
    r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}\s*$",
    re.MULTILINE,
)
README_STABLE_RE = re.compile(
    r"Personal AI OS `v(\d+\.\d+\.\d+)` is the current stable tagged release\."
)
SUPPORTED_SECTION_RE = re.compile(
    r"^## Supported versions\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
SECURITY_STABLE_RE = re.compile(
    r"current stable `v(\d+)\.(\d+)\.x` release line"
)


@dataclass(frozen=True)
class Project:
    path: Path
    name: str
    version: str
    dependencies: tuple[str, ...]


def parse_semver(value: str, *, field: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"{field} must be a semantic version, found {value!r}")
    return tuple(int(match.group(index)) for index in (1, 2, 3))


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


def runtime_version() -> str:
    if not RUNTIME_VERSION_FILE.is_file():
        raise ValueError(
            f"missing runtime version file: {RUNTIME_VERSION_FILE.relative_to(ROOT)}"
        )
    match = RUNTIME_VERSION_RE.search(RUNTIME_VERSION_FILE.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(
            f"missing __version__ assignment: {RUNTIME_VERSION_FILE.relative_to(ROOT)}"
        )
    return match.group(1)


def web_version() -> str:
    if not WEB_PACKAGE_FILE.is_file():
        raise ValueError(f"missing web package metadata: {WEB_PACKAGE_FILE.relative_to(ROOT)}")
    try:
        payload = json.loads(WEB_PACKAGE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in {WEB_PACKAGE_FILE.relative_to(ROOT)}"
        ) from exc
    value = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing version in {WEB_PACKAGE_FILE.relative_to(ROOT)}")
    parse_semver(value, field=str(WEB_PACKAGE_FILE.relative_to(ROOT)))
    return value


def changelog_stable_version(text: str) -> str:
    match = CHANGELOG_RELEASE_RE.search(text)
    if match is None:
        raise ValueError("CHANGELOG.md has no dated stable release heading")
    version = match.group(1)
    parse_semver(version, field="CHANGELOG.md stable release")
    return version


def readme_stable_version(text: str) -> str:
    matches = README_STABLE_RE.findall(text)
    if len(matches) != 1:
        raise ValueError(
            "README.md must contain exactly one current stable tagged-release statement"
        )
    version = matches[0]
    parse_semver(version, field="README.md current stable release")
    return version


def security_stable_line(text: str) -> tuple[int, int]:
    section = SUPPORTED_SECTION_RE.search(text)
    if section is None:
        raise ValueError("SECURITY.md is missing a Supported versions section")
    matches = SECURITY_STABLE_RE.findall(section.group("body"))
    if len(matches) != 1:
        raise ValueError(
            "SECURITY.md Supported versions must contain exactly one current stable vMAJOR.MINOR.x release line"
        )
    return int(matches[0][0]), int(matches[0][1])


def source_version_errors(
    *,
    package_version: str,
    runtime: str,
    web: str,
) -> list[str]:
    errors: list[str] = []
    parse_semver(package_version, field="aligned internal package version")
    parse_semver(runtime, field="API runtime version")
    parse_semver(web, field="web package version")
    if runtime != package_version:
        errors.append(
            "API runtime __version__ does not match the aligned package version: "
            f"runtime={runtime}, packages={package_version}"
        )
    if web != package_version:
        errors.append(
            "web package version does not match the aligned package version: "
            f"web={web}, packages={package_version}"
        )
    return errors


def public_policy_errors(
    *,
    changelog_text: str,
    readme_text: str,
    security_text: str,
) -> list[str]:
    stable = changelog_stable_version(changelog_text)
    readme = readme_stable_version(readme_text)
    security_major_minor = security_stable_line(security_text)
    stable_major, stable_minor, _ = parse_semver(stable, field="CHANGELOG.md stable release")

    errors: list[str] = []
    if readme != stable:
        errors.append(
            "README current stable release does not match the latest dated CHANGELOG release: "
            f"README=v{readme}, CHANGELOG=v{stable}"
        )
    if security_major_minor != (stable_major, stable_minor):
        errors.append(
            "SECURITY supported stable line does not match the latest dated CHANGELOG release: "
            f"SECURITY=v{security_major_minor[0]}.{security_major_minor[1]}.x, "
            f"CHANGELOG=v{stable}"
        )
    return errors


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
        try:
            parse_semver(expected_version, field="aligned internal package version")
        except ValueError as exc:
            errors.append(str(exc))

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

        try:
            api_runtime_version = runtime_version()
            web_package_version = web_version()
            errors.extend(
                source_version_errors(
                    package_version=expected_version,
                    runtime=api_runtime_version,
                    web=web_package_version,
                )
            )
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

        try:
            errors.extend(
                public_policy_errors(
                    changelog_text=CHANGELOG_FILE.read_text(encoding="utf-8"),
                    readme_text=README_FILE.read_text(encoding="utf-8"),
                    security_text=SECURITY_FILE.read_text(encoding="utf-8"),
                )
            )
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    if errors:
        for error in errors:
            print(f"::error title=Internal package version check::{error}")
        return 1

    expected_version = next(iter(versions))
    names = ", ".join(sorted(internal))
    stable_version = changelog_stable_version(CHANGELOG_FILE.read_text(encoding="utf-8"))
    print(
        f"Internal/public version policy check passed: {len(internal)} packages, API runtime, "
        f"and web source at v{expected_version}; public stable policy at v{stable_version} "
        f"({names})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
