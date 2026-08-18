from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import re
from typing import Literal


Scope = Literal["runtime", "development"]

_SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)


@dataclass(frozen=True, order=True)
class VersionCore:
    major: int
    minor: int
    patch: int


@dataclass(frozen=True)
class ParsedVersion:
    raw: str
    core: VersionCore
    prerelease: str | None


@dataclass(frozen=True)
class DependencyRiskSummary:
    package: str
    current_version: str
    new_version: str
    update_level: str
    scope: Scope
    affected_surface: str
    toolchain_or_framework: bool
    risk: str
    review_mode: str
    decision: str
    auto_merge_allowed: bool
    required_checks: tuple[str, ...]
    release_notes_url: str | None
    rationale: tuple[str, ...]


def _parse_semver(value: str) -> ParsedVersion:
    match = _SEMVER_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"unsupported semantic version: {value!r}")
    return ParsedVersion(
        raw=value.strip(),
        core=VersionCore(
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
        ),
        prerelease=match.group("prerelease"),
    )


def _update_level(current: ParsedVersion, new: ParsedVersion) -> str:
    if new.core < current.core:
        return "downgrade"
    if new.core == current.core:
        if new.prerelease == current.prerelease:
            return "same"
        # Moving from a stable build to a prerelease of the same core is a downgrade in stability.
        if current.prerelease is None and new.prerelease is not None:
            return "prerelease"
        if current.prerelease is not None or new.prerelease is not None:
            return "prerelease"
        return "same"
    if new.major != current.major:
        return "major"
    if new.minor != current.minor:
        return "minor"
    if new.patch != current.patch:
        return "patch"
    return "prerelease"


def summarize_dependency_change(
    *,
    package: str,
    current_version: str,
    new_version: str,
    scope: Scope,
    affected_surface: str,
    toolchain_or_framework: bool = False,
    release_notes_url: str | None = None,
) -> DependencyRiskSummary:
    if scope not in ("runtime", "development"):
        raise ValueError("scope must be 'runtime' or 'development'")
    if not package.strip():
        raise ValueError("package must be non-empty")
    if not affected_surface.strip():
        raise ValueError("affected_surface must be non-empty")
    if release_notes_url is not None and not release_notes_url.startswith("https://"):
        raise ValueError("release_notes_url must be HTTPS when supplied")

    current = _parse_semver(current_version)
    new = _parse_semver(new_version)
    level = _update_level(current, new)
    rationale: list[str] = []

    if level == "downgrade":
        risk = "high"
        review_mode = "blocked_change"
        rationale.append("The proposed version is lower than the current version.")
    elif level == "major":
        risk = "high"
        review_mode = "migration_required"
        rationale.append("A major-version change requires an explicit compatibility migration.")
    elif level == "prerelease":
        risk = "high"
        review_mode = "compatibility_review"
        rationale.append("Prerelease transitions are not treated as routine maintenance.")
    elif level == "minor" and toolchain_or_framework:
        risk = "high"
        review_mode = "compatibility_review"
        rationale.append("A framework/toolchain minor update can change build or runtime contracts.")
    elif level == "minor" and scope == "runtime":
        risk = "medium"
        review_mode = "compatibility_review"
        rationale.append("A runtime minor update may change application behavior or compatibility.")
    elif level == "minor":
        risk = "medium"
        review_mode = "focused_review"
        rationale.append("A development dependency minor update needs focused tooling validation.")
    elif level == "patch" and (scope == "runtime" or toolchain_or_framework):
        risk = "medium"
        review_mode = "focused_review"
        rationale.append("A patch update still touches a runtime, framework, or toolchain boundary.")
    elif level == "patch":
        risk = "low"
        review_mode = "routine_review"
        rationale.append("A development-only patch is narrow but still requires repository checks.")
    else:
        risk = "low"
        review_mode = "no_change"
        rationale.append("The normalized semantic version is unchanged.")

    if toolchain_or_framework:
        rationale.append("The dependency is marked as a framework/toolchain boundary.")
    if scope == "runtime":
        rationale.append("The dependency is marked as runtime-affecting.")
    if release_notes_url is None:
        rationale.append("No release-notes URL was supplied; review should not infer migration safety.")

    checks: list[str] = ["CI", "Dependency Review"]
    if scope == "runtime" or toolchain_or_framework or level in ("major", "prerelease"):
        checks.extend(["CodeQL", "Platform Readiness"])

    # Stable order and no duplicates make the result easy to compare in automation.
    required_checks = tuple(dict.fromkeys(checks))

    return DependencyRiskSummary(
        package=package.strip(),
        current_version=current.raw,
        new_version=new.raw,
        update_level=level,
        scope=scope,
        affected_surface=affected_surface.strip(),
        toolchain_or_framework=toolchain_or_framework,
        risk=risk,
        review_mode=review_mode,
        decision="needs_review",
        auto_merge_allowed=False,
        required_checks=required_checks,
        release_notes_url=release_notes_url,
        rationale=tuple(rationale),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Produce a deterministic dependency-update risk summary. "
            "The tool never approves or auto-merges a dependency change."
        )
    )
    parser.add_argument("--package", required=True)
    parser.add_argument("--from-version", required=True)
    parser.add_argument("--to-version", required=True)
    parser.add_argument("--scope", choices=("runtime", "development"), required=True)
    parser.add_argument("--surface", required=True)
    parser.add_argument("--toolchain-or-framework", action="store_true")
    parser.add_argument("--release-notes-url", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = summarize_dependency_change(
            package=args.package,
            current_version=args.from_version,
            new_version=args.to_version,
            scope=args.scope,
            affected_surface=args.surface,
            toolchain_or_framework=args.toolchain_or_framework,
            release_notes_url=args.release_notes_url,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
