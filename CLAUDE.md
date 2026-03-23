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
- `localization_pipeline.py` — classification pipeline (main entry point)
- `localization_pipeline_regression.py` — 3D regression variant
- `run_experiment_matrix.py` — sweep runner for multiple grids/algorithms
- `multi_user_pipeline.py` — multi-UE support
- `read_jsonc.py` — shared JSONC parser
- `configs/` — JSONC experiment configs (not ML code)

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

**MATLAB entry points** use wrapper scripts that set `global OVERRIDE_*` variables, then call `generate_simulation_data`.

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

No formal test framework. Validation happens via:
1. **Integration**: run `run_experiment_matrix.py` end-to-end and check the output CSV/report
2. **Sanity checks in data loading**: raise `FileNotFoundError` / `ValueError` early
3. **One-off analysis scripts**: `analyze_results.py`, `validate_*.py` in `src/python/`

When adding new models or features, verify against known results:
- 10×10 XGBoost static baseline ≈ 33.8% accuracy (RSS+SINR, temporal split)

---

## Git & Results

- `results/` is **gitignored** — all simulation data and experiment outputs are local only
- Only commit: source code, configs, `TASKS.md`, docs
- Wait a few seconds after background Python processes finish before `git add` (avoids "Stream closed" errors)
- Preferred split method: `--split-method temporal` (prevents data leakage)
