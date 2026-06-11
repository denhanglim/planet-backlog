# PLANET BACKLOG — architecture & operating principles

Autonomous exoplanet-candidate discovery and vetting system. Classical algorithms detect
periodic transit signals in TESS light curves; an adversarial AI panel vets each candidate;
survivors are published as fully-provenanced dossiers on a static web experience.

Output is **vetted candidates with false-positive probabilities** — never "confirmed planets".
Confirmation requires radial-velocity follow-up, which is out of scope. All public framing is
ExoFOP-style: candidates for community follow-up.

## Non-negotiable principles

1. **The LLM never invents a number.** Every numeric quantity (period, depth, SNR, FPP,
   odd-even ratio, centroid offset) is computed by deterministic Python in `pipeline/`.
   The AI layer (`panel/`) only interprets computed diagnostics, reasons, cross-references,
   and writes prose. If a number isn't computed, it doesn't exist.
2. **Calibrate before you claim.** No novel candidate is shown until the pipeline has
   (a) recovered known planets in the same data, and (b) passed injection-recovery with
   measured completeness and reliability. These metrics are published on the site.
3. **Dedup ruthlessly.** Every candidate is cross-checked against TOI, confirmed-planet,
   and known-EB catalogs. Never present a known object as a discovery.
4. **Provenance everywhere.** Every dossier traces to TIC ID, sector, data product,
   pipeline version, every diagnostic, and every skeptic verdict. Reproducible.
5. **Honesty over results.** Failures are reported explicitly in the build log and the UI.
   A pipeline that recovers 0 novel candidates but provably re-finds known planets is a
   success. Fabricated data is total failure.

## Architecture

Two decoupled layers joined by a JSON contract in `data/`:

- **Layer A — `pipeline/` (Python, deterministic).** ingest → detrend → period search
  (BLS + TLS) → diagnostics (odd-even, secondary eclipse, shape, centroid, neighbors,
  systematics flags) → single-transit hunter → statistical validation (FPP).
- **Layer B — `panel/` (AI, interpretive).** Six skeptic agents (binary, blend, instrument,
  stellar, alias, catalog) each try to kill the candidate from one angle, reasoning only
  over computed diagnostics; a judge synthesizes verdicts. Driven via `claude -p` headless
  calls with strict JSON schemas. Verdicts are machine-consumable.

- **`calibration/`** — known-planet recovery + injection-recovery; emits `data/calibration.json`.
- **`web/`** — Next.js static-export frontend; renders **entirely** from `data/*.json`.
- **`tests/`** — pytest; includes an integration test asserting a known planet is recovered.

## Data contract (`data/`)

- `candidates.json` — candidates with all diagnostics, skeptic verdicts, judge synthesis,
  FPP, provenance, folded light-curve series.
- `calibration.json` — known-planet recovery table, completeness/reliability curves,
  injection-recovery scope and caveats.
- `run-meta.json` — pipeline version, run timestamps, target counts, environment.

## Running

```bash
.venv/bin/python -m pipeline.run --help     # science pipeline
.venv/bin/python -m calibration.run --help  # calibration gate
.venv/bin/python -m panel.run --help        # AI vetting panel (needs `claude` CLI)
cd web && npm run dev                        # frontend
.venv/bin/pytest tests/                      # tests
```
