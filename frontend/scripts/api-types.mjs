// Generate src/api/schema.d.ts from the backend's OpenAPI schema.
//   node scripts/api-types.mjs          write the file
//   node scripts/api-types.mjs --check  exit 1 if the committed file is stale
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repo = resolve(frontend, "..");
const target = resolve(frontend, "src/api/schema.d.ts");
const python = resolve(
  repo,
  process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python",
);

const schemaJson = execFileSync(python, ["scripts/export_openapi.py"], { cwd: repo, encoding: "utf8" });
const header = "// Generated from the backend OpenAPI schema by `npm run gen:api`. Do not edit.\n\n";
const generated = header + astToString(await openapiTS(JSON.parse(schemaJson)));

if (process.argv.includes("--check")) {
  const normalize = (text) => text.replace(/\r\n/g, "\n");
  const current = existsSync(target) ? readFileSync(target, "utf8") : "";
  if (normalize(current) !== normalize(generated)) {
    console.error("src/api/schema.d.ts is out of date with the backend schema. Run `npm run gen:api`.");
    process.exit(1);
  }
  console.log("API types are up to date.");
} else {
  writeFileSync(target, generated);
  console.log(`Wrote ${target}`);
}
