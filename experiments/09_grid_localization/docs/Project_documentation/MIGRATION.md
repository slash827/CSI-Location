# Migrating to a new machine

Moving the gitignored data — the part `git clone` does not give you. For sending
results to a *collaborator*, see `SHARING.md` instead; that is a much smaller,
different bundle.

## The one rule

**Do not delete anything on the old machine until the new machine is verified
working.** The old machine is your only backup: `results/` is gitignored, so
nothing in it exists anywhere else. Transfer, verify with checksums, run a real
experiment end to end, *then* consider reclaiming space.

## What exists (as of 2026-09-11)

| Path | Size | Recoverable if lost? |
| :--- | ---: | :--- |
| `results/early_experiments/exp{10,11,13}/dataset/` | **14.61 GB** | **No.** Raw QuaDRiGa output from `experiments/06_urban_scenario/exp13_urban_dataset.m` and siblings. Only by re-running MATLAB for hours |
| `ml_training/` npz + pkl + plots | **5.80 GB** | Yes — derived. See the chain below |
| `results/grid_localization/` | 0.36 GB | **No.** Raw sim data behind every result in the report |
| `results/` everything else | 0.32 GB | Mixed — run outputs, analysis, plots |
| `ml_training/` everything else | 0.05 GB | Config and logs |
| `.venv/` | 5.84 GB | **Do not copy** — rebuild from `requirements.txt` |

Total to move: **~21 GB**. Over a gigabit LAN that is roughly five minutes, so
there is no need to trim anything for the transfer itself.

### The derived-data chain

```
results/early_experiments/exp11_2025-11-15_14-07-52/dataset/   3.53 GB  RAW
   └─> ml_training/output/processed_data/processed_{train,val}.npz   3.93 GB  derived
          └─> ml_training/**/saved_models/*.pkl                      ~1.8 GB  derived
```

Anything to the right of an arrow can be rebuilt from what is to its left.
Nothing can rebuild the leftmost column except MATLAB and QuaDRiGa.

## Transfer

Robocopy over the LAN, excluding only the virtual environment. `/MIR` is
deliberately **not** used — it deletes files at the destination that are absent at
the source, which is the wrong default when the destination might already hold
work.

```powershell
# on the NEW machine, from an elevated prompt, with the old machine's drive shared
robocopy "\\OLD-PC\d$\gilad\projects\Academy\CSI-Location" `
         "D:\gilad\projects\Academy\CSI-Location" `
         /E /XD .venv .git __pycache__ .pytest_cache /R:2 /W:5 /MT:16 /TEE `
         /LOG:"D:\migration.log"
```

`/E` copies subdirectories including empty ones; `/XD` excludes directories;
`/MT:16` uses 16 threads; `/R:2 /W:5` limits retries so one locked file cannot
stall the run overnight.

Alternatively clone from GitHub for everything tracked, and robocopy only
`results\` and `ml_training\` — it amounts to the same bytes, since the tracked
part is tiny. **If you take that selective route, note there are five directories
named `results` in this repo**, and the gitignore pattern `results/` has no
leading slash, so it matches every one of them:

| Path | Size | |
| :--- | ---: | :--- |
| `results/` | 16 GB | the main one |
| `ml_training/results/` | 776 MB | |
| `ml_training/output/results/` | 666 MB | |
| `experiments/results/` | 28 KB | stray output from scripts run with the wrong working directory — but its 3 files are **unique**, not duplicates of the main tree |
| `experiments/09_grid_localization/docs/results/` | 60 KB | three committed documents; already tracked, so a clone provides them |

The whole-tree robocopy above picks all of these up. A selective copy can miss
`experiments/results/`.

> **Latent trap:** because `results/` matches at any depth, any *new* file added
> to `experiments/09_grid_localization/docs/results/` is silently gitignored. The
> three documents already there survive only because git keeps tracking files
> added before an ignore rule started matching them. Put new documentation
> elsewhere, or force-add it with `git add -f`.

## Verify before trusting

On the **old** machine, record a manifest:

```powershell
cd D:\gilad\projects\Academy\CSI-Location
Get-ChildItem -Recurse -File -Path results, ml_training -ErrorAction SilentlyContinue |
  Where-Object { $_.Length -gt 10MB } |
  ForEach-Object { "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm MD5).Hash, $_.FullName.Substring($PWD.Path.Length+1) } |
  Sort-Object | Set-Content old_machine_manifest.txt
```

Run the identical command on the new machine, then compare:

```powershell
Compare-Object (Get-Content old_machine_manifest.txt) (Get-Content new_machine_manifest.txt)
```

Empty output means every file over 10 MB transferred intact. Hashing only files
above 10 MB keeps this to minutes rather than hours while still covering all the
irreplaceable data.

## Rebuild the environment

Do **not** copy `.venv`. The new GPU likely wants a different CUDA build.

```powershell
cd D:\gilad\projects\Academy\CSI-Location
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
# follow the torch instructions at the top of requirements.txt, then:
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Confirm the GPU is visible:

```powershell
.\.venv\Scripts\python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

MATLAB and QuaDRiGa v2.8.1 need installing separately; they are only required to
generate *new* simulation data, not to re-run any ML in this repo.

## Smoke test

Proves the data, the environment and the GPU all landed correctly:

```bash
.venv/Scripts/python experiments/09_grid_localization/src/python/experiments_ablation/error_decomposition.py
```

Expect roughly: all 19.43 m, multi-antenna 15.29 m, single-antenna 34.81 m. If
those match, the migration is sound.

Then run the Python test suite:

```bash
.venv/Scripts/python -m pytest experiments/09_grid_localization/src/python/tests/ -v
```

---

## Reclaiming space on the old machine — afterwards

Only once the new machine passes the smoke test. Ordered by risk.

### 🟢 Safe — derived, cheap to rebuild (~1.8 GB)

Saved scikit-learn model files. A k-NN "model" stores its entire training set,
which is why `knn_model.pkl` is 751 MB; it rebuilds in minutes.

```
ml_training/output/saved_models/knn_model.pkl                             751 MB
ml_training/results/baseline_2025-11-07_20-58-41/models/knn_model.pkl     489 MB
ml_training/results/baseline_2025-11-07_20-22-48/models/knn_model.pkl     123 MB
ml_training/output/results/optimized_*/models/random_forest_v*_model.pkl  ~415 MB
```

### 🟡 Medium — derived, but expensive and depends on keeping exp11 (3.93 GB)

```
ml_training/output/processed_data/processed_train.npz   3.00 GB
ml_training/output/processed_data/processed_val.npz     0.75 GB
```

Rebuildable from exp11's raw dataset via the preprocessing step. **Only delete
these while exp11's dataset still exists.** Deleting both together ends that
research line permanently.

### 🔴 Never delete without an external backup first

```
results/early_experiments/exp13_2025-11-26_20-23-00/dataset/   10.56 GB
results/early_experiments/exp11_2025-11-15_14-07-52/dataset/    3.53 GB
results/early_experiments/exp10_2025-11-07_12-40-00/dataset/    0.85 GB
results/grid_localization/                                      0.36 GB
```

Raw QuaDRiGa output. Referenced by `experiments/04_data_generation_LOS/`,
`05_data_generation_NLOS/` and `06_urban_scenario/`, including a file named
`RECOVERY_INSTRUCTIONS.md`. The exp10/11/13 line was superseded by experiment 09,
but "superseded" is not "reproducible" — regenerating them means re-running
MATLAB simulations that originally took hours.

If space is genuinely tight, archive these three to an external drive, verify the
checksums there, and only then delete from the working machine.

### Not worth the risk

The two `*_backup_20260509_1741` directories are **not** duplicates — they hold 29
and 26 files against 87 and 81 in their live counterparts, so they are partial
snapshots. Together they are 5.3 MB. The 16 `exp13b_*` runs total 139 MB. Neither
is worth the chance of discarding something unique.
