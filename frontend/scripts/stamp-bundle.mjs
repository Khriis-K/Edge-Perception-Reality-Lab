// Stamp dist/ with a digest of the sources it was built from (see scripts/frontend_bundle.py).
// dist/ is committed, and pytest fails if the sources change without a rebuild.
import { execFileSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repo = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const python = resolve(repo, process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");

execFileSync(python, ["scripts/frontend_bundle.py", "stamp"], { cwd: repo, stdio: "inherit" });
