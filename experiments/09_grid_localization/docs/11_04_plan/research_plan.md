# Research Plan — April 2026
# Experiment: BS Placement Effect on AoA Informativeness

**Date:** 2026-04-11  
**Experiment codename:** `ne_bs_voronoi_15x15`  
**Predecessor:** `multi_user_voronoi_15x15` (center BS, results in `results/multi_user_voronoi_15x15/`)

---

## 1. Motivation

In the `multi_user_voronoi_15x15` experiment the serving BS sits at the exact
center of the grid. This means every grid point lies at a distinct azimuth
angle from the BS — the full circle (≈360°) is covered. As a result, **AoA is
an almost perfect discriminator**: adding AoA jumps accuracy from ≈50% (BASE_H)
to ≈88% (BASE_A_H) for XGBoost.

The open question is: **was that AoA gain a lucky artefact of a full angular
sweep, or is it a robust feature regardless of BS placement?**

In a real deployment the BS is *not* centred — it is mounted on a wall, at a
corridor end, or on a ceiling corner. When the BS is outside or at the edge of
the coverage area, all UEs are concentrated in a narrow angular sector, and AoA
carries far less discriminative power.

---

## 2. Geometry

### 2.1 Current setup (center BS)

```
Grid 15×15, spacing 2 m, offset [5, 5]
X ∈ [5, 33],  Y ∈ [5, 33]
Serving BS:  (19, 19, 10)  ← dead center of grid
IBS-1:      (-11, 19, 10)  30 m west  → E-W SINR gradient
IBS-2:       (19,-11, 10)  30 m south → N-S SINR gradient

AoA azimuth range seen by BS: ~0° to ~360°  (full circle)
```

### 2.2 New setup (NE corner BS)

```
Same grid: X ∈ [5, 33],  Y ∈ [5, 33]   (NE corner = (33, 33))
Serving BS:  (48, 48, 10)  ← 15 m north and 15 m east of NE corner
IBS-1:       (19, -10, 10) south of grid
IBS-2:       (-10, 19, 10) west of grid

AoA azimuth range seen by BS:
  NW corner (5, 33) → ~199°
  SW corner (5,  5) → ~225°
  SE corner (33, 5) → ~251°
  Spread ≈ 52°  (7× less than center-BS case)
```

The NE BS placement compresses all UE directions into one 52° quadrant.
AoA can still give an angular ordering within that quadrant, but the
absolute discriminative power is drastically reduced.

### 2.3 Distance ranges

| BS placement | d_min (m) | d_max (m) | d_max / d_min |
|---|---|---|---|
| Center (19,19) | 0 (BS at grid) | 28.3 (corners) | ∞ in limit |
| NE (48,48)     | 21.2 (NE corner) | 60.8 (SW corner) | 2.9 |

With the NE placement every UE is at a significant, non-zero distance from the
BS. RSS discrimination is no longer confounded by the near-zero-distance points
at the center of the grid.

---

## 3. Research Questions

### Q1 — AoA informativeness vs angular spread (primary)

> Does the AoA improvement (`BASE_A_H` − `BASE_H`) shrink when the BS is placed
> at the NE corner vs. at the center?

**Hypothesis:** Yes. With only 60° angular spread, AoA within that sector
gives limited discriminative power and the gain over RSS+SINR+history will be
much smaller than the 38-percentage-point jump seen with the center BS.

**Falsification condition:** AoA gain ≥ 15 pp in the NE experiment would
suggest that even within-sector azimuth variation is sufficient.

---

### Q2 — History compensation (secondary)

> With a less informative AoA, does transition history (h=3) compensate more
> strongly for the NE-BS case than for the center-BS case?

**Hypothesis:** The *relative* gain of adding history (`BASE_H` − `BASE`)
will be similar or larger in the NE case because there are more points with
similar RSS profiles that need disambiguation by trajectory.

---

### Q3 — RSS/SINR discrimination with edge BS

> With the BS at the NE corner, do RSS and SINR become *more* discriminative
> spatially (better distance contrast) or *less* (because all UEs are at large
> distance with little variation)?

**Hypothesis:** RSS variance increases (larger dynamic range: 14 m vs 54 m
distance), but SINR patterns change because the serving-to-interferer
geometry is different.

---

### Q4 — Spatial MAE distribution

> Does the NE BS placement create a "far corner dead zone" (SW corner of grid)
> where MAE is consistently higher, and is this mitigated by AoA or history?

**Expected pattern:** SW corner points are farthest from BS → lower SNR →
higher MAE in all non-AoA experiments. The MAE heatmap should show a
gradient from NE (low error) to SW (high error).

---

### Q5 — AoA elevation vs azimuth

> Does elevation angle (which encodes the vertical geometry relative to BS)
> remain informative even when azimuth is compressed?

With BS at (43, 43, **10**) and UE at height 1.5 m, elevation angle =
arctan(8.5 / distance). Near points (NE corner, d=14m): elevation ≈ 31°.
Far points (SW corner, d=54m): elevation ≈ 9°. A 22° elevation spread means
elevation AoA still encodes rough distance — it may carry *more* relative
information than azimuth in this configuration.

---

## 4. Experiment Matrix

All experiments run with XGBoost + RF, same 5 device profiles as before,
temporal 80/20 split, h=3.

| Key | Features | h | AoA | Extra | Compare to center-BS |
|-----|----------|---|-----|-------|----------------------|
| BASE | RSS+SINR | 0 | No | — | ✓ |
| BASE_H | RSS+SINR | 3 | No | — | ✓ |
| BASE_H_dp | RSS+SINR | 3 | No | device | ✓ |
| BASE_A | RSS+SINR+AoA | 0 | Yes | — | ✓ |
| BASE_A_H | RSS+SINR+AoA | 3 | Yes | — | ✓ |
| BASE_A_H_dp | RSS+SINR+AoA | 3 | Yes | device | ✓ |
| BASE_dp | RSS+SINR | 0 | No | device | ✓ |
| BASE_uid | RSS+SINR | 0 | No | user ID | ✓ |

Cross-user experiments: `cross_user_BASE_H`, `cross_user_BASE_A_H`.

---

## 5. Comparison Protocol

For each experiment key, report the **delta** relative to the center-BS result:

```
Δacc  = acc_NE  − acc_center
ΔMAE  = MAE_NE  − MAE_center   (positive = NE is worse)
```

Key comparisons:

| Comparison | What it isolates |
|---|---|
| `BASE_A_H` vs `BASE_H` (both placements) | AoA gain per placement |
| `BASE_A_H` NE vs `BASE_A_H` center | Net placement effect on AoA model |
| `BASE_H` NE vs `BASE_H` center | Placement effect without AoA |
| MAE heatmap NE vs center | Spatial distribution of errors |
| Elevation AoA only vs full AoA | Within-NE: azimuth vs elevation contribution |

---

## 6. Simulation Configuration

New config file: `configs/ne_bs_voronoi_15x15_config.jsonc`

Key differences vs `multi_user_voronoi_15x15_config.jsonc`:

```jsonc
"base_station": {
  "position": [48, 48, 10],   // NE placement: 15m north + 15m east of NE corner (33,33)
  "interferers": {
    "positions": [
      [19, -10, 10],           // south  (was [-11, 19, 10] west)
      [-10, 19, 10]            // west   (was [19, -11, 10] south)
    ]
  }
}
```

Everything else (grid, movement, channel scenario, device profiles) is
identical to ensure clean comparability.

Wrapper script: `src/matlab/run_ne_bs_15x15.m`  
Output dir: `results/grid_localization/grid_15x15/sim_data_ne_bs_<timestamp>/`  
Python pipeline output: `results/ne_bs_voronoi_15x15/`

---

## 7. Engineering Improvements

These improvements benefit both this experiment and future runs of
`multi_user_voronoi_15x15`.

### 7.1 MATLAB simulation parallelism

The 5-user loop in `run_multi_user_15x15.m` runs sequentially. Each user is
completely independent. Options (in order of effort):

**Option A — `parfor` (Parallel Computing Toolbox required)**

```matlab
parfor u = 1:n_users
    % set overrides locally (parfor workers have separate workspaces)
    run_single_user(u, profiles, output_dir, config_name);
end
```

This gives ~5× speedup on a 4–6 core machine. Requires PCT toolbox.  
The `generate_simulation_data` script must be refactored into a callable
function (`run_single_user.m`) that takes parameters instead of globals.

**Option B — spawn MATLAB subprocess per user (no toolbox)**

From Python: `subprocess.Popen(['matlab', '-batch', 'run_user_1_15x15'])` for
each user, monitor stdout files for completion. Requires one wrapper script per
user but no toolbox.

**Recommendation:** Implement Option A (`parfor`) as it is cleanest.
Detect whether PCT is available at runtime and fall back to sequential `for`.

### 7.2 Progress bar and ETA in MATLAB

Add to `generate_simulation_data.m` immediately before `l.get_channels()`:

```matlab
fprintf('[%s] Starting QuaDRiGa channel generation for %d snapshots...\n', ...
        datestr(now,'HH:MM:SS'), n_snapshots);
tic;
```

And after:

```matlab
elapsed = toc;
fprintf('[%s] Channel generation complete in %.1f s  (%.2f ms/snapshot)\n', ...
        datestr(now,'HH:MM:SS'), elapsed, elapsed/n_snapshots*1000);
```

For the walk generation loop, add a counter every 1000 steps:

```matlab
if mod(step, 1000) == 0
    pct = step / config.n_steps * 100;
    elapsed = toc;
    eta = elapsed / pct * (100 - pct);
    fprintf('  Walk: %d/%d steps (%.0f%%)  ETA: %.0fs\r', ...
            step, config.n_steps, pct, eta);
end
```

### 7.3 Python pipeline parallelism

Current state: Python 3.11.2, GIL always on.

**Short-term (no upgrade): `ProcessPoolExecutor`**

Each experiment in `EXPERIMENTS` is fully independent after features are built.
The model training phase can be parallelised across experiments using separate
worker processes:

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

def _train_experiment(exp_def, train_df, test_df, grid_lookup, model_name):
    ...  # returns (key, results_dict)

with ProcessPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(_train_experiment, exp, ...): exp for exp in EXPERIMENTS}
    for fut in as_completed(futures):
        key, res = fut.result()
        results[model_name][key] = res
```

Feature building (the slower part) can also be parallelised per-experiment
since the feature cache is populated independently.

**Longer-term: Python 3.13t (free-threaded)**

Python 3.13 ships a second interpreter build (`python3.13t`) that disables the
GIL. `uv` can install it:

```bash
uv python install 3.13t
uv venv .venv-313t --python 3.13t
```

Free-threaded Python allows true `threading.Thread` parallelism for pure-Python
loops (feature extraction, result aggregation). NumPy/sklearn already release
the GIL internally, so the net speedup for this workload is moderate; process
parallelism is probably still better for CPU-bound training.

**Recommendation:** Implement `ProcessPoolExecutor` parallelism now (works
on 3.11, no upgrade needed). If you want to explore 3.13t, `uv` makes it easy
to install side-by-side without affecting the system Python.

### 7.4 Timestamped log files

**MATLAB** — add at the top of each `run_*.m` script:

```matlab
log_dir = fullfile(output_dir, 'logs');
mkdir(log_dir);
log_file = fullfile(log_dir, sprintf('run_%s.log', ...
           datestr(now, 'yyyy-mm-dd_HH-MM-SS')));
diary(log_file);
diary on;
```

And `diary off` at the end. All `fprintf` output is captured.

**Python** — add to `multi_user_pipeline.py`:

```python
import logging, datetime

def setup_logging(out_dir: Path) -> None:
    log_dir = out_dir / 'logs'
    log_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = log_dir / f'run_{ts}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s  %(levelname)s  %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(),   # also print to console
        ]
    )
    logging.info(f'Log file: {log_file}')
```

Replace all `print(...)` calls in the pipeline with `logging.info(...)`.
The log file then captures the full run with timestamps, making it easy to
compare timing across runs.

### 7.5 `tqdm` progress bar in Python pipeline

Add to feature building and training loops:

```python
from tqdm import tqdm

for exp in tqdm(EXPERIMENTS, desc='Experiments', unit='exp'):
    ...

# Per-user model training:
for uid in tqdm(train_users, desc=f'{exp_key} training users', leave=False):
    ...
```

---

## 8. Expected Results

| Experiment | Center BS (ref) | NE BS prediction |
|---|---|---|
| BASE accuracy | 47.0% | Similar or slightly better (better distance range) |
| BASE_H accuracy | 52.5% | Similar (history not AoA-dependent) |
| BASE_A accuracy | 82.5% | **Much lower** — AoA barely discriminates in 60° sector |
| BASE_A_H accuracy | 88.0% | **Much lower** than center, but better than NE BASE_A |
| AoA gain (`BASE_A_H`−`BASE_H`) | +35 pp | **<15 pp** predicted |
| MAE spatial pattern | Roughly uniform | Gradient NE→SW (farther = worse) |

The elevation AoA channel may partially compensate (it encodes distance with
BS at 10m height) — watch for `BASE_A` performing better than expected relative
to the azimuth argument.

---

## 9. Deliverables

1. `configs/ne_bs_voronoi_15x15_config.jsonc`
2. `src/matlab/run_ne_bs_15x15.m`
3. `results/ne_bs_voronoi_15x15/` — CSV + image outputs
4. Engineering improvements implemented in `generate_simulation_data.m` and
   `multi_user_pipeline.py`
5. Updated `research_documentation.md` with NE-BS results and comparison tables
