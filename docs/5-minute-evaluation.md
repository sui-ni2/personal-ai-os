# 5-minute evaluation

Allow about five minutes for the browser steps **after installation and startup**. Downloads and the first build can take longer. No API key is needed to create a project, record progress, and check persistence. A real chat response requires a configured provider.

## 1. Install and start

For a new source checkout, install Git, then run:

```bash
git clone --branch main --single-branch https://github.com/sui-ni2/personal-ai-os.git
cd personal-ai-os
git rev-parse HEAD
```

Keep that SHA for your report. Choose one startup path:

| Environment | Install / start | Open app |
| --- | --- | --- |
| Docker Desktop or Docker Engine with Compose | `docker compose up --build -d` | `http://127.0.0.1:8080` |
| Windows source, without Docker | Commands below; requires Python 3.11+, Node.js 20+, pnpm 11 | `http://localhost:3000` |

On Windows, install dependencies once from the checkout root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

Wait for setup to finish. Start these in two separate terminals, both at the checkout root:

```powershell
# Terminal 1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev-api.ps1
```

```powershell
# Terminal 2
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev-web.ps1
```

For prerequisite checks, manual setup, or troubleshooting, see [Try without an API key](try-without-api.md) and [README startup instructions](../README.md#start-locally). Keep the default localhost bindings. No provider credential is added by these setup paths.

## 2. Create a project

Open **Projects**. Fill **New project name** with `First run notes` and **New project description** with a short, non-sensitive goal. Select **Create project** and find its card.

## 3. Record and update progress in Control

On that project's card, select **Control**, then scroll below the project cards to **Project control center**. Check its project name. Use **Record type**, **Project update**, and **Add**:

| Record type | Example Project update |
| --- | --- |
| `task` | Review two public sources |
| `decision` | Use public sources only |
| `outcome` | Outline started; source review pending |

Check that each entry appears under **Tasks**, **Decisions**, or **Outcomes**. To record later progress, select the same type and **Add** a new entry, for example `Task update: first source reviewed; second still pending`. This appends a progress record; the current UI does not edit the earlier entry in place or offer a completed-task toggle. Record only what you actually did.

Ordinary project operations use this existing UI; no HTTP request or generated project id is needed. Reviewed Memory is a separate review workflow. These Task/Decision/Outcome records are not automatically accepted Memory.

## 4. Inspect continuity

On the same card, select **Continuity**. Inspect the persisted project records in the preview. It is bounded project state, not a copied provider session, full chat history, or proof that reviewed core Memory was included.

## 5. Open normal Text chat

On the project's card, select **Open**. Verify **Project context** is your new project and keep **Text** selected.

- **No provider configured:** the app explains the missing server-side credential and disables **Send message**. This is the expected no-key result. Continue to restart; report real chat as **not tested**, not successful.
- **A provider is configured by you:** choose it with **Model**, write a short, non-sensitive request for your own workflow, and select **Send message**. Wait for a completed reply and note the provider/model and whether the reply was useful. Supported choices are OpenAI, Anthropic, and explicitly enabled local Ollama. Configuration is described in [README](../README.md#optional-local-ollama); keys stay server-side. Record a failure if the request fails.

## 6. Restart and confirm persistence

Return to **Projects** first. Restart with the same checkout and data location:

- Docker: run `docker compose restart`.
- Windows source: stop the API and web terminals with **Ctrl+C**, then run the same two startup commands from step 1. Do not rerun setup while the services are running.

Reload the app. Find the same project, open **Control**, and confirm the original records and progress updates remain. Open **Continuity** again and compare the state. If you completed a real chat, open the project and select that conversation from history; check that the earlier messages and reply remain.

If **Restart recovery** offers **Preview recovery**, inspect it before choosing **Confirm and resume**. A clean close may offer no recovery; that is expected and does not invalidate the persistence check. A page reload alone is not a service restart.

## Report the result

Use the [short external test packet](external-test-packet.md) to report success, a partial path, or the exact step that failed. No-key persistence can succeed while the full chat workflow remains partial. This guide and maintainer/CI runs do not establish independent adoption.

Stop Docker with `docker compose down`, or stop the two source terminals with **Ctrl+C**. Keep the data volume/directory; `docker compose down -v` deletes it.
