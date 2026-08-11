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

## Where the current product falls short

The current implementation is an early foundation, not a finished product. My present
experience exposes several important gaps:

- useful AI conversations still depend on configuring an external model API before the
  product can do meaningful model-backed work;
- the available provider and model choices are limited, so I cannot yet freely use the
  model I prefer through one consistent interface;
- the main panels contain too much information and feel more complicated than necessary;
- the voice path exists in the implementation, but a real end-to-end voice conversation
  has not yet been successfully connected and accepted;
- Settings is not integrated into the experience in the place and form I expect, which
  makes configuration feel separate from the work it controls;
- as a whole, the product is not yet polished or complete enough to call broadly useful.

These are not cosmetic omissions to hide before publishing. They are the maintainer's
real first-party problems and should become a prioritized, verifiable improvement backlog.
External API dependence, provider choice, interface density, voice acceptance, and
settings integration must each be addressed without weakening the project's privacy and
permission boundaries.

## Long-term intent

Despite the unfinished experience, I want to keep building Personal AI OS rather than
treating it as a short-lived prototype. The long-term goal is to make it useful beyond my
own private workflow: software that ordinary people can understand, configure, trust, and
use with the model provider they choose.

Reaching that goal requires honest iteration. The project should not claim broad adoption
or product maturity before those exist. Progress should instead be demonstrated through
working releases, successful end-to-end checks, resolved dogfooding issues, clearer user
experience, and preserved safety boundaries.

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

## Current priority

The next useful proof is not another broad feature area. It is closing the first-run and
text-chat loop so a new user can configure a provider and complete a natural conversation
within a few minutes. The ordered improvement plan is maintained in `../ROADMAP.md`.
