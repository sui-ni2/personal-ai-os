import { spawnSync } from "node:child_process";
import { cp, rm } from "node:fs/promises";
import path from "node:path";

function run(command, args, environment = process.env) {
  const result = spawnSync(command, args, { stdio: "inherit", env: environment, shell: false });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

const options = new Set(process.argv.slice(2));
const nextCli = path.resolve("node_modules", "next", "dist", "bin", "next");
run(process.execPath, [nextCli, "build", "apps/web"], {
  ...process.env,
  PERSONAL_AI_OS_STATIC_EXPORT: "true",
  ...(options.has("--mobile-preview")
    ? { NEXT_PUBLIC_PERSONAL_AI_OS_MOBILE_PREVIEW: "true" }
    : {}),
});
run(process.execPath, ["scripts/prepare-static-export.mjs", "apps/web/out"]);

if (options.has("--dist")) {
  const projectRoot = process.cwd();
  const source = path.join(projectRoot, "apps", "web", "out");
  const destination = path.join(projectRoot, "dist");
  if (path.dirname(destination) !== projectRoot || path.basename(destination) !== "dist") {
    throw new Error(`Refusing to replace an unsafe hosted output path: ${destination}`);
  }
  await rm(destination, { recursive: true, force: true });
  await cp(source, destination, { recursive: true });
  process.stdout.write(`Prepared hosted static output in ${destination}\n`);
}
