# 5-minute evaluation

This short path verifies durable project state without an API key, a provider call, MCP knowledge, or adapter setup. It uses a non-sensitive example project and ordinary browser/HTTP actions only.

## 1. Start locally

With Docker installed, run from a fresh checkout:

```bash
docker compose up --build -d
```

Open `http://127.0.0.1:8080`. The default local Compose path is loopback-only and does not make a billable model call when no provider is configured.

## 2. Create a Project

Open **Projects**, enter `Long-running research` and a short description in **Create project**, then select **Create project**. This creates a tenant-scoped, provider-neutral project; it does not create a provider account or a plugin.

## 3. Add durable example state

The current release candidate exposes the state surface through the local API while richer project editors are still evolving. In PowerShell, paste the following; replace `long-running-research` only if the created project used a different generated id.

```powershell
$base = "http://127.0.0.1:8080/api/projects/long-running-research/state"
$records = @(
  @{ namespace = "task"; key = "next"; value = @{ title = "Review two sources" }; source = "5-minute-evaluation"; expected_version = 0 },
  @{ namespace = "decision"; key = "scope"; value = @{ choice = "Use public sources only" }; source = "5-minute-evaluation"; expected_version = 0 },
  @{ namespace = "outcome"; key = "draft"; value = @{ status = "in_progress" }; source = "5-minute-evaluation"; expected_version = 0 }
)
$records | ForEach-Object { Invoke-RestMethod -Method Put -Uri "$base/records" -ContentType "application/json" -Body ($_ | ConvertTo-Json -Compress) }
Invoke-RestMethod -Method Post -Uri "$base/experience" -ContentType "application/json" -Body (@{ namespace = "reviewed_memory"; text = "Keep conclusions tied to cited sources."; source = "5-minute-evaluation"; confidence = 1 } | ConvertTo-Json -Compress)
```

These are project-owned Task, Decision, Outcome, and reviewed-Memory examples. Project creation and state writes also create bounded activity metadata; values stay in the project-private SQLite store.

## 4. Inspect continuity and activity

Return to **Projects** and use **Continuity** on the new card. The preview shows the current state and reviewed Memory, not provider chat history. The card also shows the latest project activity.

## 5. Verify restart recovery

Open the text Chat page for the new project, then return to Projects. This records a metadata-only recovery checkpoint without sending a message, so it needs no provider key and never stores a provider session or private reasoning. Restart the app:

```bash
docker compose restart
```

Open **Projects** again. If the browser session did not record a clean close, use **Preview recovery**, inspect the bounded state, then choose **Confirm and resume**. The application never restores silently and does not mark a normal close as a crash. If the session closed cleanly, the status is `clean`; the Continuity preview still proves the project state persisted.

## 6. Optional provider-switch isolation check

If two supported providers are already configured by you, switch the selected provider in Chat **without sending a message**, then open the same project’s Continuity preview. Task, Decision, Outcome, reviewed Memory, file/change references you add as state, workflows, and recovery metadata remain project-scoped rather than provider-scoped. Do not add a key solely for this evaluation.

## What this does and does not prove

It proves no-key startup, generic Project creation, tenant/project-scoped persistence, visible activity, bounded continuity, and explicit restart recovery. It does not prove a provider model response, cloud identity/billing, third-party adoption, or a production deployment.

Stop the local app with `docker compose down`. Do not use `-v` unless you intentionally want to delete the named local data volume.
