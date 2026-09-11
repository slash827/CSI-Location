# Sharing this project

## What a collaborator gets from `git clone` alone

Everything needed to **read and audit** the work:

- `docs/Project_documentation/` — final report, technical documentation, research overview, handover, slides
- `docs/figures/` — all publication figures
- `docs/results_of_record/` — the machine-written JSON/Markdown backing every number (see its `MANIFEST.md`)
- `src/python/`, `src/matlab/`, `configs/` — the full pipeline

They do **not** get `results/`, which is gitignored.

## What requires the data bundle

Re-running anything. `results/` is ~16 GB locally, but almost all of that is
pre-2026 experiments unrelated to this work — five files under
`results/early_experiments/` account for ~14.6 GB on their own. The subset needed
to reproduce the report is **~68 MB**.

| Bundle | Size | Enables |
| :--- | ---: | :--- |
| `notebook_experiments/multi_user_poc/` | ~15 MB | viewing all 90 diagnostic plots and raw run outputs |
| `grid_localization/grid_25x25/` | ~53 MB | re-running the entire Campaign B ML pipeline |

Trained checkpoints (`.pt`) are excluded — they retrain in under six minutes.

## Building the bundle

```bash
# from the repo root; build at a SHORT path, Windows MAX_PATH bites otherwise
B="d:/gilad/_bundle/CSI-Location-results"
mkdir -p "$B/notebook_experiments" "$B/grid_localization"
cp -r results/notebook_experiments/multi_user_poc "$B/notebook_experiments/"
find "$B/notebook_experiments" -name "*.pt" -delete      # bundle copy only
cp -r results/grid_localization/grid_25x25 "$B/grid_localization/"

powershell -NoProfile -Command \
  "Compress-Archive -Path 'd:\gilad\_bundle\CSI-Location-results' \
   -DestinationPath 'd:\gilad\CSI-Location-results-bundle.zip' -CompressionLevel Optimal"
```

Every step is a copy. Nothing under `results/` is moved or deleted.

Add `README.md` at the bundle root telling the recipient to unpack the two folders
into `results/`; a copy of that text lives alongside this file in the bundle that
was built on 2026-09-11.

## Delivery

- **Google Drive** — simplest, and the project already uses Drive for the technical document.
- **GitHub Release asset** — attaches the zip to the repo itself, so the link never
  rots and the version is explicit. 63 MB is well inside the 2 GB per-asset limit.

Do **not** commit `results/` to git. 358 MB of `.mat` files would bloat the repo
permanently, git never forgets a blob, and GitHub rejects files over 100 MB.

## A warning about disk cleanup

`results/` is gitignored, so it exists in exactly one place with no backup. The
large files under `results/early_experiments/` are referenced by
`experiments/04_data_generation_LOS/`, `05_data_generation_NLOS/` and
`06_urban_scenario/` — including a `RECOVERY_INSTRUCTIONS.md`. Treat freeing disk
space as its own task, with archive-and-verify before any deletion. It has nothing
to do with sharing: the bundle above is 68 MB either way.
