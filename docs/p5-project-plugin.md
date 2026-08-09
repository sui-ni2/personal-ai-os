# P5 project plugin

P5 / 排列5 is an isolated project plugin. It registers through the same project contract as
General and Soccer, but owns its workflow state and SQLite database under
`data/projects/p5/p5.db`. It does not add fields to Chat, Memory, Repository, provider, or
execution-event schemas and it has no P3 access.

## Daily contract

The workflow contract is `P5_POST_DRAW_2222_NEXT_DAY_V1`:

1. Do not check before 22:22 in `Asia/Shanghai`.
2. If the official result is not confirmed, persist a waiting state and retry after ten minutes.
3. Review the settled issue and append its rule evidence.
4. Do not retune a rule from one draw; weight changes begin only after ten observations.
5. Generate and atomically persist exactly 10,000 unique candidates for the next issue.
6. Run deterministic, replayable 10xthink feature scoring, filters, and Top10 dehomogenization.
7. Lock Top10 and its Top5 prefix, then append the audit event.

An existing 10,000-row lock is immutable and reused on a repeated daily call. A partial lock is
treated as an error instead of being overwritten.

The execution path is identified as GPT/ChatGPT and the plugin denies Codex and P3. The current
lock remains paper-only research and does not authorize betting.

## API and tools

- `GET /api/projects/p5/home`
- `GET /api/projects/p5/history`
- `GET /api/projects/p5/candidates?issue=...&number=...`
- `GET /api/projects/p5/audit`
- `POST /api/projects/p5/daily-run`

The same operations are allowlisted as local MCP tools: `p5.status`, `p5.history`,
`p5.candidate.lookup`, `p5.daily.run`, and `p5.audit`. Other projects cannot invoke them.

Each stored candidate includes generation order, raw and adjusted scores, feature scores,
triggered filters, elimination reason, final-filter survival, final rank, Top10/Top5 flags,
model version, and creation time.

## Views

- `/projects/p5` — P5 Home
- `/projects/p5/history` — History
- `/projects/p5/candidates` — Candidate Explorer
- `/projects/p5/audit` — Model Audit
