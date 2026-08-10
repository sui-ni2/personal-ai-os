import { copyFile, readdir } from "node:fs/promises";
import path from "node:path";

const exportRoot = path.resolve(process.argv[2] || "apps/web/out");

async function collect(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await collect(absolute));
    else files.push(absolute);
  }
  return files;
}

let aliases = 0;
for (const source of await collect(exportRoot)) {
  if (!source.endsWith(".txt")) continue;
  const relative = path.relative(exportRoot, source);
  const parts = relative.split(path.sep);
  const marker = parts.findIndex((part) => part.startsWith("__next."));
  if (marker < 0 || marker === parts.length - 1) continue;
  const destination = path.join(
    exportRoot,
    ...parts.slice(0, marker),
    parts.slice(marker).join("."),
  );
  if (destination === source) continue;
  await copyFile(source, destination);
  aliases += 1;
}

process.stdout.write(`Prepared ${aliases} static RSC aliases in ${exportRoot}\n`);
