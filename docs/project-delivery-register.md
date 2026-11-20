# Personal AI OS — persistent project delivery register

> **Dated snapshot:** 2026-11-20, Asia/Singapore. Repository: `sui-ni2/personal-ai-os`. This is an index, not a live GitHub/CI status feed.
> `docs/project-delivery-register.json` is the machine-readable inventory. Check current code, PR head, reviews and exact SHA before any modification.

## Rules for continuing the work

1. Retain every tracked line: **active** work continues, **ready** designs turn into implementation, **design** produces an accepted RFC, **external** waits for real evidence, **deferred** retains an explicit review trigger, **completed** is not repeated without regression.
2. **A plan, saved record, submitted PR, passing mock, or green CI is not a finished product.** Move status only after explicit evidence and acceptance. The register checker validates bookkeeping, not GitHub state or real-world truth.
3. Finish active changes before starting overlapping ones. Use small reviewed branches and exact-SHA checks. No direct-main push, forced update, automated merge, secret access, migration without backup or unauthorized publication.
4. Keep all domain workflows behind the project boundary. Community/local-first remains runnable; cloud identity/billing stays fail-closed. Do not publish unapproved private candidate files or account materials.
5. Each project-building run must inspect this index, live open PRs/issues, relevant design and completed evidence, then close one verifiable step or record the real blocker. No empty repetition, manufactured adoption or meaningless PRs.

## Tracked commitments

### 1 · Active implementation and maintenance

| ID | Priority | Workstream | Next verified step |
| --- | --- | --- | --- |
| PAI-012 | P1 | Backup, migration, restore and user data portability | Advance integration safety checks; preserve all private records. |
| PAI-020 | P0 | Next.js 16.4.5 security patch review | Prioritize #168 without automatic merge. |
| PAI-021 | P2 | Python 3.15-slim major compatibility | Review #166 as a compatibility project, not an automatic patch. |
| PAI-022 | P1 | vinext and Cloudflare packages alignment | Review #162/#163 together without fragmentary upgrades. |
| PAI-023 | P2 | UI icons and Node type dependency maintenance | Review #159/#161 only for warranted benefit. |
| PAI-031 | P1 | Maintainer and open-source application evidence | Keep public ledger accurate; check application result only through actual decision evidence. |

### 2 · Designed and ready to build

| ID | Priority | Workstream | Next verified step |
| --- | --- | --- | --- |
| PAI-016 | P0 | v0.4 release-candidate gate and stable handoff | Finish candidate verification; do not automatically merge, tag or release. |
| PAI-033 | P1 | First-run Doctor diagnostic comprehension | Build targeted diagnostic UX/regression without exposing private state. |

### 3 · Design needed before implementation

| ID | Priority | Workstream | Next verified step |
| --- | --- | --- | --- |
| PAI-005 | P0 | Task/Decision/Outcome lifecycle provenance | Design lifecycle state transitions and failure tests. |
| PAI-008 | P1 | Unified Settings and first-run information architecture | Write screen and consent/secret handling RFC before UI changes. |
| PAI-025 | P2 | End-to-end speech input and spoken response | Design small voice acceptance and cancellation matrix. |
| PAI-026 | P2 | Codex/Research project plugins | Specify one reference plugin and prove isolation. |
| PAI-027 | P3 | Tasks, Calendar, Journal, Reading and daily workflow | Prioritize a single need after real external usage evidence. |

### 4 · External tests and owner acceptance needed

| ID | Priority | Workstream | Next verified step |
| --- | --- | --- | --- |
| PAI-007 | P0 | Real provider switching with persisted project state | Run operator-controlled credentialed/local-provider acceptance with redacted outcome. |
| PAI-013 | P0 | Real Windows distribution and rollback acceptance | Obtain real operator environment and rollback verification without deleting user data. |
| PAI-014 | P2 | Signing identity and signed Windows artifacts | Retain unsigned limitation until owner supplies authorized custody. |
| PAI-015 | P1 | Physical mobile PWA and assistive-tech verification | Request consented actual-device test; no emulation substitution. |
| PAI-017 | P0 | Seven-to-fourteen-day daily dogfooding | Collect day-by-day results; time elapsed alone is insufficient. |
| PAI-018 | P0 | Independent first-use and real-workflow evidence | Continue Issues #7 and #55; do not manufacture adoption. |
| PAI-019 | P0 | Independent Windows and macOS/Linux clean installs | Continue Issues #15 and #56 and fix reproduced friction. |
| PAI-024 | P1 | Cross-client project-state handoff acceptance | Compare two genuine clients using synthetic handoff; keep unpublished working materials private. |

### 5 · Deliberately deferred with review triggers

| ID | Priority | Workstream | Next verified step |
| --- | --- | --- | --- |
| PAI-028 | P2 | Gemini and new model provider adapters | No untested new provider in v0.4 candidate. |
| PAI-029 | P3 | Managed-cloud account, billing and device sync | Maintain fail-closed cloud contract. |
| PAI-030 | P3 | Agent swarms, marketplace and unrelated integrations | Do not increase v0.4 scope to inflate feature count. |

### 6 · Completed baselines — do not rebuild

| ID | Priority | Workstream | Next verified step |
| --- | --- | --- | --- |
| PAI-001 | P0 | Published v0.3.0 community release | Preserve evidence without re-releasing completed work. |
| PAI-002 | P0 | Project persistence, handoff, and restart recovery | Extend, not rebuild, the existing persistence engine. |
| PAI-003 | P0 | Recorded state is not completed work (PR #169) | Preserve neutral Recorded labels; reopen only if a regression is observed. |
| PAI-004 | P0 | Project State Reconciler read-only v1 | Preserve the metadata-only, bounded API invariants; keep the Projects-screen preview and conflict classification as separate future increments. |
| PAI-006 | P0 | Provider-neutral core and project isolation | Preserve existing boundaries; real provider use has a separate gate. |
| PAI-009 | P0 | Budget reservation and usage safety | Keep regression coverage; invoices need independent evidence. |
| PAI-010 | P0 | MCP side-effect confirmation and send-scope receipt | Do not weaken permission or replay boundaries. |
| PAI-011 | P0 | Interrupted execution and unknown side-effect safety | Keep external provider failures distinct from fixture coverage. |
| PAI-032 | P2 | Upstream FastMCP contribution and related issue | Monitor only meaningful regression or follow-up. |

## Immediate build order

- **PAI-003/PAI-004:** both are completed with exact-head CI; preserve the distinction between recorded state and real execution. **PAI-005** remains a separate lifecycle design.
- **PAI-020:** security fix #168 remains a separate review and merge decision; **PAI-021/022/023** are compatibility-sensitive updates, not an automated merge batch.
- **PAI-016:** assemble exact-head v0.4 evidence; maintain the independent provider, device, install and multi-day-use limitations recorded in PAI-007/013/015/017/018/019.
- **PAI-024:** perform real cross-client pilot only in authorized environments; do not copy or publish private candidate source.

## Append-only plan retention

The [historical ID baseline](project-delivery-ids.txt) independently retains every
workstream ID. Removing an ID from both JSON and Markdown still fails the
validator. New plans must be added to all three in a reviewed change.
Changing the historical baseline itself requires explicit review; this prevents
accidental loss but is not cryptographic protection from malicious edits.

## Checks and provenance

Run `python scripts/check_project_delivery_register.py` or the focused pytest. The validator checks mandatory status-dependent gates, unique IDs, and one-to-one indexed rows; it **cannot** confirm that a PR merged, CI passed, or external users adopted the product.

### Public references

The register uses only already-public repository design and issue/PR references. Private conversation contents, credentials, proprietary candidate packages and other projects remain out of Git.
