import { spawnSync } from "node:child_process";
import { access, copyFile, cp, mkdir, rm } from "node:fs/promises";
import path from "node:path";

const projectRoot = process.cwd();
const webRoot = path.join(projectRoot, "apps", "web");
const source = path.join(webRoot, "dist");
const destination = path.join(projectRoot, "dist");
const vinextCli = path.join(projectRoot, "node_modules", "vinext", "dist", "cli.js");

if (path.dirname(destination) !== projectRoot || path.basename(destination) !== "dist") {
  throw new Error(`Refusing to replace an unsafe hosted output path: ${destination}`);
}

const result = spawnSync(process.execPath, [vinextCli, "build"], {
  cwd: webRoot,
  stdio: "inherit",
  shell: false,
  env: {
    ...process.env,
    NEXT_PUBLIC_PERSONAL_AI_OS_MOBILE_PREVIEW: "true",
  },
});
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);

await access(path.join(source, "server", "index.js"));
await rm(destination, { recursive: true, force: true });
await cp(source, destination, { recursive: true });
await mkdir(path.join(destination, ".openai"), { recursive: true });
await copyFile(
  path.join(projectRoot, ".openai", "hosting.json"),
  path.join(destination, ".openai", "hosting.json"),
);
process.stdout.write(`Prepared vinext Sites output in ${destination}\n`);
