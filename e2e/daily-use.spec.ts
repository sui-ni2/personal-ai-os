import { expect, test, type APIRequestContext } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const api = "http://127.0.0.1:8000/api";

async function setGeneralBudget(request: APIRequestContext, limitTokens: number) {
  const response = await request.put(`${api}/budgets`, {
    data: { scope_type: "project", scope_id: "general", period: "daily", limit_tokens: limitTokens, warn_percent: 80, hard_limit: true },
  });
  expect(response.ok()).toBeTruthy();
}

test.beforeEach(async ({ page, request }) => {
  await setGeneralBudget(request, 100_000);
  await page.addInitScript(() => window.localStorage.setItem("personal-ai-os:experience-mode", "advanced"));
});

test.afterEach(async ({ request }) => {
  await setGeneralBudget(request, 100_000);
});

test("daily Project, Memory, send scope, budget hard stop, execution, and reload path", async ({ page }, testInfo) => {
  const projectName = `Daily-use E2E ${testInfo.project.name}`;
  await page.goto("/projects");
  await page.getByLabel("New project name").fill(projectName);
  await page.getByLabel("New project description").fill("Deterministic daily-use validation project");
  await page.getByRole("button", { name: "Create project" }).click();
  const project = page.locator("article").filter({ hasText: projectName }).first();
  await expect(project).toContainText(projectName);
  await project.getByRole("button", { name: "Control" }).click();
  await expect(page.getByText("Project control center")).toBeVisible();

  for (const [kind, value] of [["goal", "Ship a safe daily workflow"], ["task", "Validate execution"], ["decision", "Keep context scoped"], ["outcome", "Daily path completed"]] as const) {
    await page.getByLabel("Record type").selectOption(kind);
    await page.getByLabel("Project update").fill(value);
    await page.getByRole("button", { name: "Add" }).click();
    await expect(page.getByRole("listitem").filter({ hasText: value }).last()).toBeVisible();
  }

  await page.goto("/memory");
  await page.getByText("Add memory", { exact: true }).click();
  await page.getByLabel("Memory", { exact: true }).fill("daily-use-e2e=approved");
  await page.getByRole("button", { name: "Save memory" }).click();
  await page.getByRole("button", { name: "review" }).click();
  await expect(page.getByText("daily-use-e2e=approved")).toBeVisible();
  await page.getByRole("button", { name: "Accept" }).first().click();

  await page.goto("/chat?new=1");
  const composer = page.getByLabel("Message", { exact: true });
  await composer.fill("Run the deterministic daily-use request.");
  await page.getByRole("button", { name: /Send/ }).click();
  await expect(page.getByText("Deterministic E2E response from openai")).toBeVisible();
  await expect(page.getByText("What left this workspace for the last request")).toBeVisible();

  const saveMemory = page.getByRole("button", { name: "Save to Memory" }).last();
  await saveMemory.click();
  const memoryDialog = page.getByRole("dialog", { name: "Save what matters" });
  await expect(memoryDialog).toBeVisible();
  await expect(page.getByLabel("Memory note")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(memoryDialog).toBeHidden();
  await expect(saveMemory).toBeFocused();

  await page.reload();
  await expect(page.getByText("Deterministic E2E response from openai")).toBeVisible();

  await page.goto("/settings");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByLabel("Estimated token limit").fill("1");
  await page.getByRole("button", { name: "Set hard limit" }).click();
  await expect(page.getByText("Budget saved")).toBeVisible();
  await page.goto("/chat?new=1");
  await composer.fill("This deterministic request must stop at the budget.");
  await page.getByRole("button", { name: /Send/ }).click();
  await expect(page.getByRole("alert")).toContainText("Budget hard limit reached. No provider request was sent.");
});

test("fallback consent, external confirmation, and recovery resume stay explicit", async ({ page, request }, testInfo) => {
  const routing = await request.put(`${api}/routing`, {
    data: { policy: "ASK_BEFORE_FALLBACK", fallback_provider: "anthropic", fallback_model: "anthropic-e2e" },
  });
  expect(routing.ok()).toBeTruthy();

  await page.goto("/chat?new=1");
  await page.getByLabel("Allow one policy-approved fallback").check();
  const composer = page.getByLabel("Message", { exact: true });
  await composer.fill("force deterministic timeout with explicit fallback consent");
  await page.getByRole("button", { name: /Send/ }).click();
  await expect(page.getByText("Deterministic E2E response from anthropic")).toBeVisible();

  await page.getByRole("button", { name: "Use an advanced tool" }).click();
  const connector = page.getByLabel("Connector");
  const externalConnector = connector.getByRole("option", { name: /Deterministic external confirmation/ });
  await expect(externalConnector).toBeAttached();
  const connectorId = await externalConnector.getAttribute("value");
  expect(connectorId).toBeTruthy();
  await connector.selectOption(connectorId!);
  await composer.fill("Run the confirmed deterministic external fixture.");
  page.once("dialog", async (dialog) => {
    expect(dialog.message()).toContain("External tool action: external.echo");
    await dialog.accept();
  });
  await page.getByRole("button", { name: /Send/ }).click();
  await expect(page.getByText("Deterministic E2E response from openai")).toBeVisible();

  const key = `e2e-resume-${testInfo.project.name}`;
  const state = await request.put(`${api}/projects/general/state/records`, {
    data: { namespace: "task", key, value: { summary: "Resume from deterministic recovery" }, source: "playwright", expected_version: 0 },
  });
  expect(state.ok()).toBeTruthy();
  const started = await request.post(`${api}/projects/general/recovery/sessions`);
  expect(started.ok()).toBeTruthy();
  const session = await started.json();
  const checkpoint = await request.post(`${api}/projects/general/recovery/sessions/${session.session_id}/checkpoint`, {
    data: { expected_version: session.recovery_version },
  });
  expect(checkpoint.ok()).toBeTruthy();

  await page.goto("/projects");
  await expect(page.getByRole("button", { name: "Preview recovery" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Preview recovery" }).first().click();
  await expect(page.getByRole("button", { name: "Confirm and resume" })).toBeVisible();
  await page.getByRole("button", { name: "Confirm and resume" }).click();
  await expect(page.getByText("Recovery was confirmed. New work resumes from the persisted project state shown above.")).toBeVisible();
});

test("keyboard, focus restoration, axe, and mobile viewport cover daily surfaces", async ({ page, isMobile }) => {
  for (const route of ["/projects", "/memory", "/settings"]) {
    await page.goto(route);
    const results = await new AxeBuilder({ page }).include("main").analyze();
    expect(results.violations).toEqual([]);
    const main = page.getByRole("main");
    const initialFocusable = main.locator("a, button, input, select, textarea").first();
    await initialFocusable.focus();
    await expect(initialFocusable).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(main.locator(":focus")).toBeVisible();
  }

  await page.goto("/chat?new=1");
  await page.getByRole("button", { name: "Open conversation history" }).click();
  const history = page.getByRole("dialog", { name: "Conversation history" });
  await expect(history).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(history).toBeHidden();
  await expect(page.getByRole("button", { name: "Open conversation history" })).toBeFocused();
  if (isMobile) await expect(page.getByRole("main")).toBeVisible();
});
