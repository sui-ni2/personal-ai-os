# Release evidence verification

Stable-release readiness is an evidence question, not a successful-command question. The verifier in
`scripts/release_evidence_verifier.py` checks a collected evidence bundle and refuses to report
`ready_to_tag` when required evidence is missing, stale, non-successful, unauditable, or attached to
a different commit.

It **does not** fetch GitHub data, create a tag, publish a release, or bypass repository rules. Evidence
collection remains a separate step so the final decision can be reproduced from a small JSON file.

## Required gates

A release bundle must contain exactly one successful result for each gate:

- `CI`
- `CodeQL`
- `Dependency Review`
- `Platform Readiness`
- `Release provider smoke`

Every gate must reference the exact expected full commit SHA, include an HTTPS source URL, and include
an ISO-8601 completion timestamp. By default, evidence older than 48 hours is blocked; the age window
can be changed explicitly for a particular release process.

## Evidence format

```json
{
  "commit_sha": "0123456789abcdef0123456789abcdef01234567",
  "checks": [
    {
      "name": "CI",
      "conclusion": "success",
      "head_sha": "0123456789abcdef0123456789abcdef01234567",
      "completed_at": "2026-08-18T11:00:00Z",
      "url": "https://github.com/owner/repo/actions/runs/123"
    },
    {
      "name": "CodeQL",
      "conclusion": "success",
      "head_sha": "0123456789abcdef0123456789abcdef01234567",
      "completed_at": "2026-08-18T11:05:00Z",
      "url": "https://github.com/owner/repo/actions/runs/124"
    },
    {
      "name": "Dependency Review",
      "conclusion": "success",
      "head_sha": "0123456789abcdef0123456789abcdef01234567",
      "completed_at": "2026-08-18T11:06:00Z",
      "url": "https://github.com/owner/repo/actions/runs/125"
    },
    {
      "name": "Platform Readiness",
      "conclusion": "success",
      "head_sha": "0123456789abcdef0123456789abcdef01234567",
      "completed_at": "2026-08-18T11:10:00Z",
      "url": "https://github.com/owner/repo/actions/runs/126"
    },
    {
      "name": "Release provider smoke",
      "conclusion": "success",
      "head_sha": "0123456789abcdef0123456789abcdef01234567",
      "completed_at": "2026-08-18T11:12:00Z",
      "url": "https://github.com/owner/repo/actions/runs/127"
    }
  ]
}
```

A normal pull-request run commonly reports `Release provider smoke` as `skipped`. That is expected for
an ordinary PR but **does not satisfy a stable-release bundle**. The verifier is intentionally stricter
than ordinary PR merge readiness.

## Run

```bash
python scripts/release_evidence_verifier.py evidence.json \
  --expected-sha 0123456789abcdef0123456789abcdef01234567
```

For reproducible review or tests, pin the observation time:

```bash
python scripts/release_evidence_verifier.py evidence.json \
  --expected-sha 0123456789abcdef0123456789abcdef01234567 \
  --as-of 2026-08-18T12:00:00Z \
  --max-age-hours 48
```

Exit status is `0` only when the bundle is ready. A blocked bundle exits `1`; malformed input or invalid
arguments exit `2`.

## Fail-closed boundary

The tool only verifies supplied evidence. It cannot prove that a URL is truthful merely because it is
HTTPS, cannot infer a missing check from another check, and cannot treat a retry as proof that previous
failure evidence was irrelevant. Automated collection should preserve the original GitHub run/job URL
and exact commit association so a maintainer can audit the decision independently.
