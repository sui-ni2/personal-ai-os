# Short independent-use test packet

Choose one small task you actually need to do, using non-sensitive material. Follow the [five-minute UI path](5-minute-evaluation.md): install, start, create a project, **Projects → Control**, record Task/Decision/Outcome and progress, try normal Text chat, restart the services, and inspect the same project and conversation. Installation/build time is separate from the browser exercise.

With no configured provider, complete the project/persistence steps and report chat as **not tested**. For the full path, use your own configured OpenAI, Anthropic, or local Ollama service. Do not substitute a mocked response for real inference. No API commands are needed for ordinary project or chat operations.

Paste the following into [Early tester feedback](https://github.com/sui-ni2/personal-ai-os/issues/new?template=early_tester.yml) or [Issue #55](https://github.com/sui-ni2/personal-ai-os/issues/55). Failed and partial attempts are useful; stop at a blocker and describe it.

```text
Tester relationship: independent user / contributor / maintainer
Date:
Environment: OS + architecture; browser/version; Docker version OR Python/Node/pnpm versions
Version/SHA: tested tag (if any) + full git rev-parse HEAD
Fresh install: yes / no (existing checkout, caches, or data?)
Install: success / failure / not tested; approximate time; first failing step if any
Startup + open app: success / failure; Docker or source path; URL; approximate time
My real workflow: what I needed to do; why I tried this workspace
Project + Control: Task/Decision/Outcome and later progress visible? yes / no / not tested
Normal Text chat: success / failure / not tested; provider/model; useful for the task? why?
Restart: success / failure / not tested; how I stopped and restarted API + web
Persistence: same project + updates + continuity? yes / no / not tested
Conversation after restart: earlier messages + reply? yes / no / not tested
Overall: success / partial / failure (name any incomplete step)
Friction / reason I stopped / one change that would help me continue:
Optional sanitized screenshot or reproducible error:
```

**Success** for the full path requires a real completed chat and service-restart persistence. **Partial** includes a successful no-key project loop, missing-provider chat, or any untested step. A setup failure is **failure**, with later steps marked not tested. Existing-checkout results are welcome but must not be labeled fresh-install proof.

Never post credentials, `.env` contents, authorization headers, cookies, private conversations, databases, logs containing secrets, uploads/backups, or private project data. Describe a private task without reproducing its contents. A sanitized report is sufficient.

## Evidence boundary

`INDEPENDENT_ADOPTION_VERIFIED = 0` remains the current baseline. Only a test genuinely completed and reported by an independent user can support changing that value, after the source is linked and assessed in the [evidence ledger](evidence-ledger.md). An independent failed install is useful external feedback; it does not establish successful continued adoption. Maintainer runs, CI, synthetic tests/feedback, Stars, and Forks cannot satisfy the independent-user boundary. This packet is a blank reporting aid, not a testimonial or a completed test.
