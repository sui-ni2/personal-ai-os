# Governance

Personal AI OS currently uses a maintainer-led open-source model with public issues, pull requests, CI, and release gates.

## Decision process

Routine bug fixes, documentation improvements, tests, and narrowly scoped UX changes can proceed through focused pull requests.

Changes that affect persistent data, authentication, credential handling, MCP permissions, tenant boundaries, project-plugin isolation, or release criteria should explain the design and security impact before merge.

When tradeoffs are material, the maintainer should record the decision in the issue, pull request, or project documentation rather than relying on private context.

## Issue triage

Issues are prioritized by:

1. security or privacy impact;
2. data-loss or correctness risk;
3. release blockers;
4. reproducible user-facing failures;
5. contributor onboarding and documentation friction;
6. broader feature work.

`good first issue` and `help wanted` labels are reserved for concrete work that an external contributor can independently validate. They should not be used to manufacture activity.

## Pull requests

Pull requests should be focused, explain the user-visible outcome, identify security or schema effects, and list verification performed. CI must be green before maintainer merge.

External contributions are reviewed under the same correctness and privacy standards as maintainer changes. A pull request is not considered evidence of adoption merely because it exists; the project distinguishes maintainer work from genuine external contribution.

## Releases

A release is not created solely to increase repository activity. Release candidates must satisfy the documented release gates, including automated checks and any required real-provider smoke tests.

If a required credential or external dependency is unavailable, the release remains blocked rather than being marked successful with simulated evidence.

## Current maintainer model

The repository currently has a single primary maintainer. Governance can be revised if sustained external contributors emerge and maintainer responsibilities need to be shared.
