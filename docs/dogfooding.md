# Dogfooding: why Personal AI OS exists

## Status of this evidence

This is an honest first-party usage case from the project's maintainer. It is not a claim
of broad adoption, an external testimonial, or evidence of independent users. It records
the real problem that motivated the project and the criteria used to judge whether the
software is useful.

## The problem I feel in daily use

I use AI mainly for private work and occasionally want to share a workflow with a friend.
I do not need an enterprise collaboration platform, but I do need more than a collection
of disconnected chat windows and scripts.

My work is spread across different projects and tools. Context gets fragmented, the same
boundaries must be explained repeatedly, and it is difficult to see what an AI actually
did across chat, tools, files, and project-specific workflows. A convenient system can
quickly become unsafe if it mixes projects, exposes credentials, stores private reasoning,
or lets a model run arbitrary commands.

I want one personal workspace that:

- keeps Chat, structured Memory, Repository activity, tools, and Projects in one place;
- stays useful when only one person operates it;
- keeps private data, credentials, logs, and project artifacts local and outside the
  open-source distribution;
- supports different model providers without binding the product to one provider;
- exposes only allowlisted, permission-checked, auditable MCP tools;
- keeps domain plugins isolated so a Soccer or lottery workflow cannot redefine the
  general-purpose core;
- works on desktop and phone without turning a private functional API into a public
  anonymous service;
- shows observable execution status without storing or presenting private chain-of-thought.

## What the project is testing

Personal AI OS tests whether a modular monolith can provide that experience without
becoming a complex multi-user platform. The current implementation combines a Next.js
workbench, a FastAPI API, SQLite persistence, provider adapters, auditable streaming
events, an allowlisted MCP gateway, structured memory, repository events, and isolated
project plugins.

The project is successful for this maintainer only if it reduces repeated context setup
while preserving the safety boundaries above. A feature is not considered successful
merely because it exists in code or looks complete in a screenshot.

## How first-party issues will be recorded

Real problems found during private daily use may be turned into public GitHub issues only
after all personal data, credentials, private project names, conversations, paths, and
runtime artifacts have been removed. Each issue should describe:

1. the user-visible friction;
2. the expected outcome;
3. the affected general component or isolated plugin;
4. privacy, permission, migration, and compatibility constraints;
5. the verification needed before the issue can be closed.

Issues created by the maintainer will be labelled as first-party dogfooding. They must not
be presented as external feedback, community adoption, or a third-party testimonial.

## Current next question

The next useful proof is not another broad architectural layer. It is a small, repeatable
maintainer workflow that can inspect an explicitly selected repository and summarize its
test, documentation, security, and release readiness without reading secrets or changing
the repository. That workflow should produce a reviewable report and remain optional to
the general Personal AI OS experience.
