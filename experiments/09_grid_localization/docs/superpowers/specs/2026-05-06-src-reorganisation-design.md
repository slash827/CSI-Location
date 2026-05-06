# Design Spec — src/ Directory Reorganisation
**Date:** 2026-05-06  
**Status:** Approved  
**Scope:** `experiments/09_grid_localization/src/python/` and `src/matlab/`

---

## 1. Goal

Introduce topic-based subdirectories in both source trees so each file's role is clear at a glance. The Python reorganisation uses proper packages (`__init__.py`) so imports are explicit and IDE-navigable. Scripts that are not imported by anything else stay flat at the root of `src/python/` and can be moved into further subdirectories in a future session.

---

## 2. Python — New Layout

### 2.1 New packages

```
src/python/
  pipelines/
    __init__.py                          (empty)
    localization_pipeline.py             (moved)
    localization_pipeline_regression.py  (moved)
    multi_user_pipeline.py               (moved)
  utils/
    __init__.py                          (empty)
    read_jsonc.py                        (moved)
    parse_terminal_output.py             (moved)
  tests/                                 (unchanged)
  plot_*.py                              (stay flat)
  analyze_*.py                           (stay flat)
  compare_placements.py                  (stays flat)
  gen_voronoi_map.py                     (stays flat)
  investigate_model.py                   (stays flat)
  validate_voronoi_10x10.py              (stays flat)
  run_experiment_matrix.py               (stays flat)
  run_full_pipeline.py                   (stays flat)
```

### 2.2 Import updates

All changes are mechanical one-line substitutions.

| File | Old import | New import |
|---|---|---|
| `pipelines/localization_pipeline.py` | `from read_jsonc import read_jsonc` | `from utils.read_jsonc import read_jsonc` |
| `pipelines/localization_pipeline_regression.py` | `from read_jsonc import read_jsonc` | `from utils.read_jsonc import read_jsonc` |
| `pipelines/multi_user_pipeline.py` | `from read_jsonc import read_jsonc as _rjsonc` (inside `_read_bs_geometry`) | `from utils.read_jsonc import read_jsonc as _rjsonc` |
| `run_experiment_matrix.py` | `from localization_pipeline import …` | `from pipelines.localization_pipeline import …` |
| `analyze_voronoi_cells.py` | `from localization_pipeline import …` | `from pipelines.localization_pipeline import …` |
| `analyze_heterogeneous.py` | `from read_jsonc import read_jsonc` | `from utils.read_jsonc import read_jsonc` |
| `plot_data_generation.py` | `from read_jsonc import read_jsonc` | `from utils.read_jsonc import read_jsonc` |
| `plot_mae_heatmap.py` | `from multi_user_pipeline import …` | `from pipelines.multi_user_pipeline import …` |
| `gen_voronoi_map.py` | `from multi_user_pipeline import …` | `from pipelines.multi_user_pipeline import …` |
| `compare_placements.py` | `from multi_user_pipeline import …` (inside `_bs_position`) | `from pipelines.multi_user_pipeline import …` |
| `tests/test_adaptive_vmax.py` | `from multi_user_pipeline import …` | `from pipelines.multi_user_pipeline import …` |
| `tests/test_aoa_noise.py` | `from multi_user_pipeline import …` | `from pipelines.multi_user_pipeline import …` |
| `tests/test_experiment_runner.py` | `from multi_user_pipeline import …` | `from pipelines.multi_user_pipeline import …` |
| `tests/test_feature_engineering.py` | `from multi_user_pipeline import …` | `from pipelines.multi_user_pipeline import …` |
| `tests/test_read_jsonc.py` | `from read_jsonc import read_jsonc` | `from utils.read_jsonc import read_jsonc` |

### 2.3 Test runner — no change needed

`tests/conftest.py` already does:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```
`parent.parent` resolves to `src/python/`, so both `pipelines.*` and `utils.*` are importable without modification.

### 2.4 CLAUDE.md run command updates

```bash
# Before
python multi_user_pipeline.py --data-dir <path>
python localization_pipeline.py --data-dir <path>

# After
python pipelines/multi_user_pipeline.py --data-dir <path>
python pipelines/localization_pipeline.py --data-dir <path>
```

---

## 3. MATLAB — New Layout

```
src/matlab/
  core/
    generate_simulation_data.m   (moved)
    run_single_user_sim.m        (moved)
  lib/
    AreaGenerator.m              (moved)
    GeometryUtils.m              (moved)
    TrafficUtils.m               (moved)
    read_jsonc.m                 (moved)
  runners/
    run_from_config.m            (moved)
    run_voronoi.m                (moved)
    run_voronoi_10x10.m          (moved)
    run_voronoi_15x15.m          (moved)
    run_voronoi_20x20.m          (moved)
    run_multi_bs_10x10.m         (moved)
    run_multi_bs_10x10_v2.m      (moved)
    run_multi_user_15x15.m       (moved)
    run_ne_bs_15x15.m            (moved)
    run_env_variability_15x15.m  (moved)
  tests/                         (unchanged)
```

### 3.1 addpath changes

**`core/generate_simulation_data.m`** — add near top:
```matlab
addpath(fullfile(fileparts(mfilename('fullpath')), '..', 'lib'));
```

**Every file in `runners/`** — add near top:
```matlab
src_matlab = fullfile(fileparts(mfilename('fullpath')), '..');
addpath(fullfile(src_matlab, 'core'));
addpath(fullfile(src_matlab, 'lib'));
```

**`tests/TestReadJsonc.m` and `tests/TestGridGeneration.m`** — add near top:
```matlab
src_matlab = fullfile(fileparts(mfilename('fullpath')), '..');
addpath(fullfile(src_matlab, 'core'));
addpath(fullfile(src_matlab, 'lib'));
```

### 3.2 WORKSPACE_ROOT / path derivation

Runner scripts currently derive `WORKSPACE_ROOT` as:
```matlab
fileparts(fileparts(mfilename('fullpath')))   % was: src/matlab → experiment root
```
After moving into `runners/`, one more `fileparts` is needed:
```matlab
fileparts(fileparts(fileparts(mfilename('fullpath'))))  % runners → src/matlab → experiment root
```
Every occurrence of this pattern in every runner must be updated.

---

## 4. Documentation updates

| File | Change |
|---|---|
| `CLAUDE.md` | Update Python run commands; update module structure diagram; update test run command |
| `docs/Project_documentation/technical_documentation.md` | Update §2 module structure listing |
| `docs/11_04_plan/TASKS.md` | Mark "Deferred MATLAB Directory Reorganisation" task as done |

---

## 5. Verification

After all moves and edits:
1. Run Python test suite: `.venv/Scripts/python -m pytest experiments/09_grid_localization/src/python/tests/ -v` — all tests must pass
2. Smoke-test a flat script: `python experiments/09_grid_localization/src/python/compare_placements.py` — must produce 6 output files without import errors
3. MATLAB path check: open MATLAB, `cd runners`, run `run_ne_bs_15x15` with a dry-run flag — no "undefined function" errors
