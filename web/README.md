# Planet Backlog — web

The static web experience for [Planet Backlog](../README.md). A Next.js 16 static
export that renders **entirely** from the pipeline's JSON contract — no number on the
site exists outside `../data/*.json`.

## How it gets its data

`scripts/sync-data.mjs` copies the pipeline contract (`../data/candidates.json`,
`calibration.json`, `run-meta.json`) into `src/data/` before every `dev` and `build`
(via the `predev` / `prebuild` npm hooks). It **fails loudly** if any file is missing —
the site must never render fabricated data, so the build aborts rather than ship a
placeholder.

Generate the contract first (from the repo root):

```bash
.venv/bin/python -m calibration.run
.venv/bin/python -m pipeline.run --calibration --blind
.venv/bin/python -m panel.run          # needs the Claude Code CLI authenticated
```

## Develop

```bash
npm install
npm run dev      # http://localhost:3000 — re-syncs data on start
```

## Build

```bash
npm run build    # static export in out/
```

## Pages

- **Home** — mission + live counters from the run metadata.
- **The Ledger** — filterable candidate gallery with folded-curve sparklines.
- **Candidate dossier** — interactive folded light curve with the TLS model overlay,
  full diagnostics, and a JSON export for independent verification.
- **The Tribunal** — the six skeptics, their verdict stamps, evidence chips, and full
  reasoning.
- **Trust** — completeness matrix, null trials, and reliability from the calibration gate.

## Stack

Next.js 16 (App Router, static export) · React 19 · TypeScript · Tailwind v4 ·
three / @react-three/fiber · d3 · framer-motion · lenis.
