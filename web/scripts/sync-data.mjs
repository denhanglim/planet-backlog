// Copies the pipeline's JSON contract (../data/*.json) into src/data/ so the site
// builds purely from real pipeline output. Fails loudly if the contract is missing —
// the site must never render fabricated data.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dataDir = join(here, "..", "..", "data");
const outDir = join(here, "..", "src", "data");
mkdirSync(outDir, { recursive: true });

const required = ["candidates.json", "calibration.json", "run-meta.json"];
for (const f of required) {
  const src = join(dataDir, f);
  if (!existsSync(src)) {
    console.error(
      `FATAL: ${src} missing. Run the pipeline + calibration gate first — ` +
        `the site only renders real pipeline output.`
    );
    process.exit(1);
  }
  copyFileSync(src, join(outDir, f));
  console.log(`synced ${f}`);
}
