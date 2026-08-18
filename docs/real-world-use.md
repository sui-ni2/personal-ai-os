# Real-world use and external evidence

Personal AI OS is looking for first-hand evidence about whether the project is useful outside the maintainer's own workflow. The purpose of this page is to make that evidence easy to submit and difficult to misrepresent.

The current verified state is summarized in [`docs/evidence-ledger.md`](evidence-ledger.md). That ledger deliberately separates maintenance/repository reach from independently attributable adoption evidence.

## Useful evidence

The strongest public evidence is reproducible and attributable to an independent user or contributor. Examples include:

- a fresh-install report with the tested OS/runtime and version;
- a real workflow description explaining what the user attempted and what happened;
- a bug report found during genuine use;
- a focused pull request from an external contributor;
- a public follow-up showing that reported friction was fixed and independently re-tested.

Failed adoption is still useful evidence. A report explaining why someone stopped using the project can be more actionable than an unqualified positive comment.

## What does not count

The project does not treat the following as adoption evidence:

- maintainer-authored testimonials or self-replies;
- synthetic or duplicate accounts;
- paid, reciprocal, or coordinated stars/forks/comments;
- generated testimonials or placeholder feedback;
- CI runs, release automation, Dependabot activity, or repository settings by themselves;
- claims that cannot be tied to a real public report or contribution.

Repository maintenance and automated verification are still valuable, but they are maintenance evidence rather than external adoption.

## How to contribute evidence

Use one of these paths:

1. **Installation / first-run testing:** Issue #7 or the `Early tester feedback` issue form.
2. **Windows fresh-install verification:** Issue #15.
3. **macOS/Linux Docker verification:** Issue #56.
4. **Ongoing or attempted real workflow:** Issue #55 or the `Real-world use` issue form.
5. **Code or documentation contribution:** open a focused pull request following `CONTRIBUTING.md`.

## Privacy boundary

Never post API keys, `.env` contents, authorization headers, cookies, private conversations, runtime databases, secret-bearing logs, uploads/backups, or private project data. A sanitized description of the workflow and outcome is sufficient.

## Maintainer handling

Maintainers should preserve unfavorable but good-faith reports, distinguish independent evidence from first-party dogfooding, and link fixes back to the original external report when possible. Public metrics may be summarized later, but only from verifiable repository evidence and with the observation date stated. Update the evidence ledger only when the public source supports the claim.