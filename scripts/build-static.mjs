import { spawnSync } from "node:child_process";

function run(command, args, environment = process.env) {
  const result = spawnSync(command, args, { stdio: "inherit", env: environment, shell: false });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

const pnpmCli = process.env.npm_execpath;
if (!pnpmCli) throw new Error("Run this script through pnpm build:static");
run(process.execPath, [pnpmCli, "build:web"], {
  ...process.env,
  PERSONAL_AI_OS_STATIC_EXPORT: "true",
});
run(process.execPath, ["scripts/prepare-static-export.mjs", "apps/web/out"]);
