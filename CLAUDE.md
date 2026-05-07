# CLAUDE.md — CSI-Location Project Conventions

## Project Overview

Indoor localization research proving that movement history (transitions) improves prediction accuracy. Pipeline: **MATLAB + QuaDRiGa** (data generation) → **Python scikit-learn/XGBoost** (ML).

Main experiment: `experiments/09_grid_localization/`

---

## Architecture

### Language split
- **MATLAB** (`src/matlab/`): simulation data generation via QuaDRiGa, saves `.mat` + `.jsonc` config
- **Python** (`src/python/`): ML pipeline, model training, evaluation, reporting

### Python module structure
- `pipelines/localization_pipeline.py` — classification pipeline (main entry point)
- `pipelines/localization_pipeline_regression.py` — 3D regression variant
- `pipelines/multi_user_pipeline.py` — multi-UE support
- `utils/read_jsonc.py` — shared JSONC parser
- `utils/parse_terminal_output.py` — terminal output parsing utility
- `run_experiment_matrix.py` — sweep runner for multiple grids/algorithms
- `compare_placements.py` — center vs NE BS comparison plots
- `plot_mae_heatmap.py` — per-grid-point MAE scatter map
- `configs/` — JSONC experiment configs (not ML code)

### MATLAB module structure
- `core/generate_simulation_data.m` — main simulation engine
- `core/run_single_user_sim.m` — parfor-compatible per-user wrapper
- `lib/AreaGenerator.m`, `lib/GeometryUtils.m`, `lib/TrafficUtils.m`, `lib/read_jsonc.m` — reusable classes/utilities
- `runners/run_*.m` — experiment entry points (set OVERRIDE_* globals, call core/)
- `tests/` — MATLAB unit tests

### Model class hierarchy
```
LocalizationModel (ABC)
├── GaussianStaticModel / GaussianTransitionModel
└── BaseSklearnModel
    ├── RandomForestModel
    ├── XGBoostModel
    └── MLPModel
```
All models implement `train()`, `predict()`, and `get_name()`.

---

## Naming Conventions

| Scope | Python | MATLAB |
|---|---|---|
| Variables / functions | `snake_case` | `camelCase` or `snake_case` |
| Classes | `PascalCase` | `PascalCase` (classdef) |
| Constants | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` (globals) |
| Private methods | `_leading_underscore` | n/a |
| Metric names | lowercase internally (`'rss'`, `'sinr'`), uppercase in configs/output |

---

## Error Handling

**Python patterns — use these:**

```python
# Optional dependency with graceful fallback
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

# File existence check with context
if not sim_file.exists():
    raise FileNotFoundError(f"Simulation data not found: {sim_file}")

# Invalid argument
raise ValueError(f"Invalid metric specification: {feature_spec}")

# Numeric stability — never divide by zero or let log-space underflow
std = max(std, 1e-6)
log_posterior -= np.max(log_posterior[np.isfinite(log_posterior)])
```

**MATLAB patterns:**
```matlab
error('Config field missing: %s', field_name);   % fatal
warning('Unknown area type: %s. Using default.', area_type);  % recoverable
```

---

## Data Flow

```
MATLAB generates:
  results/grid_localization/grid_NxN/sim_data_*/
    ├── simulation_data.mat       (metrics + walk path)
    └── data_generation_config.jsonc

Python loads (SimulationData class):
  - scipy.io.loadmat → metrics dict: {'rss': ndarray[N], 'sinr': ndarray[N], ...}
  - true_locations: ndarray[N]  (1-indexed grid point labels, from MATLAB)
  - grid_positions: ndarray[n_points, 2 or 3]
  - neighbors: dict {0-indexed point → [0-indexed neighbors]}

Index convention:
  - Grid point labels: 1-indexed (MATLAB origin) — preserve this in output
  - Array indexing: 0-indexed internally (convert with label - 1)
  - XGBoost: 0-indexed labels; remap after prediction
```

**Config loading order (fallback chain):**
1. `data_generation_config.jsonc`
2. `config.jsonc`
3. `config.json`

---

## Configuration (JSONC)

Configs live in `experiments/09_grid_localization/configs/`. All configs use JSONC (JSON with `//` comments). Top-level keys:

```jsonc
{
  "experiment": { "name": "...", "random_seed": 42 },
  "grid": { "size": 10, "spacing": 2.0, "neighbor_connectivity": 8 },
  "movement": { "steps_per_point": 400, "ue_speed": 1.5 },
  "channel": { "scenario": "3GPP_38.901_UMi_NLOS", "center_frequency": 3e9 },
  "base_station": { "position": [x, y, z], "tx_power_dbm": 30 },
  "ml_task": { "type": "classification", "max_history_length": 3 }
}
```

When adding new config fields, always add `//` comments explaining units and valid values.

---

## CLI Patterns (Python)

Use `argparse` with `choices`, `nargs`, and explicit `type=` conversions. Always include multi-line `epilog` with usage examples.

```python
parser = argparse.ArgumentParser(
    description='...',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""Examples:\n  python script.py --data-dir <path> ..."""
)
parser.add_argument('--data-dir', required=True)
parser.add_argument('--model', choices=['gaussian', 'random_forest', 'xgboost', 'mlp'], default='gaussian')
parser.add_argument('--metrics', nargs='+', default=['rss', 'sinr'])
parser.add_argument('--split-method', choices=['random', 'temporal'], default='temporal')
```

Comma-separated metric combos (`--metrics "rss,sinr"`) are parsed into lists internally.

**MATLAB entry points** live in `src/matlab/runners/` — wrapper scripts that set `global OVERRIDE_*` variables, then call `core/generate_simulation_data`.

---

## Key Implementation Patterns

### Feature extraction (smart mode)
`TransitionFeatureExtractor` builds a **fixed-size** feature vector regardless of grid size:
- Size = `n_metrics * (history_length + 4)` — current + deltas + cumulative + trend + variance
- This is the key scalability contribution; always prefer `--feature-mode smart` for large grids.

### Memory management for large grids
Chunk large batch operations to stay under a memory budget (default 256 MB):
```python
chunk_size = max(1, int(_MEM_BUDGET / (n_paths * history_len * 8)))
for start in range(0, N, chunk_size):
    # process chunk
```

### Path resolution
Derive all paths from a single root constant:
```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
```

### Reporting
All pipelines save a `PIPELINE_REPORT.md` in the output directory using markdown tables. Print `[OK] Report saved to: <path>` on completion.

### Timing
Accumulate timings in `self.timing` dict, print summary at end of pipeline.

---

## Testing

### Running the tests

```bash
# Python — from the project root
.venv/Scripts/python -m pytest experiments/09_grid_localization/src/python/tests/ -v

# MATLAB — from src/matlab/  (tests/ is unchanged; runners are in runners/)
results = runtests('tests/TestGridGeneration'); disp(results)
results = runtests('tests/TestReadJsonc');      disp(results)
```

All Python tests must pass before committing changes to the pipeline.

### Python test files (`src/python/tests/`)

| File | What it covers |
|---|---|
| `test_read_jsonc.py` | JSONC comment stripping, edge cases (URLs in strings), real config smoke-test |
| `test_feature_engineering.py` | `build_history_features`, `build_delta_features`, `get_feature_cols`, `make_split` (chronological order + no leakage), `build_grid_lookup`, `compute_mae` |
| `test_aoa_noise.py` | `_apply_aoa_noise`: quantized to 5° steps, zero-mean, user-specific seeds, azimuth ≠ elevation noise |
| `test_experiment_runner.py` | `run_one_experiment`: label remapping round-trip (1-indexed IDs preserved through XGBoost 0-indexed training), cross-user exclusion logic, per-user/per-cell alignment |
| `test_adaptive_vmax.py` | Heatmap colour-scale function: good/bad model regimes, outlier robustness |
| `test_results_sanity.py` | **Integration** — loads saved CSVs + raw .mat files to verify: BASE_H > BASE for both models/experiments, AoA gain < 15 pp at NE BS, NE-BS azimuths confined to SW quadrant, SINR > −35 dB (catches the old 30 dB calibration bug), history gain similar across both BS placements |

### MATLAB test files (`src/matlab/tests/`)

| File | What it covers |
|---|---|
| `TestReadJsonc.m` | JSONC parsing, real config smoke-test |
| `TestGridGeneration.m` | Grid positions, NE-BS angular spread (<90°), center-BS spread (>270°), neighbor symmetry, no self-loops, walk stays in grid, walk visits >95% of points |

### Known baseline results (regression guard)

If a change breaks these, the tests will catch it:
- Center BS, XGBoost, BASE_H: ~50.4% accuracy, ~4.53 m MAE
- Center BS, XGBoost, BASE_A_H: ~83.6% accuracy, ~0.39 m MAE
- NE BS, XGBoost, AoA gain (BASE_A_H − BASE_H): ~7 pp (center BS: ~33 pp)
- SINR range in simulation data: −35 to +65 dB

---

## Git & Results

- `results/` is **gitignored** — all simulation data and experiment outputs are local only
- Only commit: source code, configs, `TASKS.md`, docs
- Wait a few seconds after background Python processes finish before `git add` (avoids "Stream closed" errors)
- Preferred split method: `--split-method temporal` (prevents data leakage)
