# src/ Directory Reorganisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce `pipelines/` and `utils/` Python packages and `core/` `lib/` `runners/` MATLAB subdirectories so each file's role is clear at a glance, without breaking any existing imports or tests.

**Architecture:** Python files that are imported by others move into proper packages with `__init__.py`; one-off scripts stay flat at `src/python/` root. MATLAB files split by role into `core/` (simulation engine), `lib/` (reusable classes), and `runners/` (experiment entry points); each runner gets `addpath` calls to resolve the new locations.

**Tech Stack:** Python 3.11, pytest, MATLAB (no Parallel Computing Toolbox required for path changes), git mv for history-preserving moves.

---

## File Map

### Python moves (5 files into packages)

| From | To |
|---|---|
| `src/python/localization_pipeline.py` | `src/python/pipelines/localization_pipeline.py` |
| `src/python/localization_pipeline_regression.py` | `src/python/pipelines/localization_pipeline_regression.py` |
| `src/python/multi_user_pipeline.py` | `src/python/pipelines/multi_user_pipeline.py` |
| `src/python/read_jsonc.py` | `src/python/utils/read_jsonc.py` |
| `src/python/parse_terminal_output.py` | `src/python/utils/parse_terminal_output.py` |

### Python files with import updates (stay flat)

`run_experiment_matrix.py`, `analyze_voronoi_cells.py`, `analyze_heterogeneous.py`,
`plot_data_generation.py`, `plot_mae_heatmap.py`, `gen_voronoi_map.py`,
`compare_placements.py`, `tests/test_read_jsonc.py`, `tests/test_adaptive_vmax.py`,
`tests/test_aoa_noise.py`, `tests/test_experiment_runner.py`, `tests/test_feature_engineering.py`

### MATLAB moves (16 files into subdirs)

| From | To |
|---|---|
| `src/matlab/generate_simulation_data.m` | `src/matlab/core/generate_simulation_data.m` |
| `src/matlab/run_single_user_sim.m` | `src/matlab/core/run_single_user_sim.m` |
| `src/matlab/AreaGenerator.m` | `src/matlab/lib/AreaGenerator.m` |
| `src/matlab/GeometryUtils.m` | `src/matlab/lib/GeometryUtils.m` |
| `src/matlab/TrafficUtils.m` | `src/matlab/lib/TrafficUtils.m` |
| `src/matlab/read_jsonc.m` | `src/matlab/lib/read_jsonc.m` |
| `src/matlab/run_from_config.m` | `src/matlab/runners/run_from_config.m` |
| `src/matlab/run_voronoi.m` | `src/matlab/runners/run_voronoi.m` |
| `src/matlab/run_voronoi_10x10.m` | `src/matlab/runners/run_voronoi_10x10.m` |
| `src/matlab/run_voronoi_15x15.m` | `src/matlab/runners/run_voronoi_15x15.m` |
| `src/matlab/run_voronoi_20x20.m` | `src/matlab/runners/run_voronoi_20x20.m` |
| `src/matlab/run_multi_bs_10x10.m` | `src/matlab/runners/run_multi_bs_10x10.m` |
| `src/matlab/run_multi_bs_10x10_v2.m` | `src/matlab/runners/run_multi_bs_10x10_v2.m` |
| `src/matlab/run_multi_user_15x15.m` | `src/matlab/runners/run_multi_user_15x15.m` |
| `src/matlab/run_ne_bs_15x15.m` | `src/matlab/runners/run_ne_bs_15x15.m` |
| `src/matlab/run_env_variability_15x15.m` | `src/matlab/runners/run_env_variability_15x15.m` |

---

## Task 1 — Python: Create packages and move files

**Files:**
- Create: `src/python/pipelines/__init__.py`
- Create: `src/python/utils/__init__.py`
- Move (git mv): 5 files listed in the file map above

All commands run from `d:/gilad/projects/Academy/CSI-Location`.

- [ ] **Step 1: Create package directories with `__init__.py`**

```bash
cd "d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/python"
mkdir pipelines
mkdir utils
echo "" > pipelines/__init__.py
echo "" > utils/__init__.py
```

- [ ] **Step 2: Move files with git mv (preserves history)**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
$base = "experiments/09_grid_localization/src/python"
git mv "$base/localization_pipeline.py"            "$base/pipelines/localization_pipeline.py"
git mv "$base/localization_pipeline_regression.py" "$base/pipelines/localization_pipeline_regression.py"
git mv "$base/multi_user_pipeline.py"              "$base/pipelines/multi_user_pipeline.py"
git mv "$base/read_jsonc.py"                       "$base/utils/read_jsonc.py"
git mv "$base/parse_terminal_output.py"            "$base/utils/parse_terminal_output.py"
```

- [ ] **Step 3: Stage the new `__init__.py` files**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
git add experiments/09_grid_localization/src/python/pipelines/__init__.py
git add experiments/09_grid_localization/src/python/utils/__init__.py
```

- [ ] **Step 4: Verify the moves look correct**

```bash
git status --short experiments/09_grid_localization/src/python/
```

Expected: 5 renames (`R` prefix), 2 new `__init__.py` files (`A` prefix). No deletions without corresponding additions.

---

## Task 2 — Python: Fix imports inside the moved pipeline files

**Files:**
- Modify: `src/python/pipelines/localization_pipeline.py:42`
- Modify: `src/python/pipelines/localization_pipeline_regression.py:28`
- Modify: `src/python/pipelines/multi_user_pipeline.py:911,925`

- [ ] **Step 1: Fix `localization_pipeline.py` line 42**

Old:
```python
from read_jsonc import read_jsonc
```
New:
```python
from utils.read_jsonc import read_jsonc
```

- [ ] **Step 2: Fix `localization_pipeline_regression.py` line 28**

Old:
```python
from read_jsonc import read_jsonc
```
New:
```python
from utils.read_jsonc import read_jsonc
```

- [ ] **Step 3: Fix `multi_user_pipeline.py` lines 911 and 925 (both inside `_read_bs_geometry`)**

Old (appears twice):
```python
from read_jsonc import read_jsonc as _rjsonc
```
New (both occurrences):
```python
from utils.read_jsonc import read_jsonc as _rjsonc
```

---

## Task 3 — Python: Fix imports in flat scripts

**Files:** 7 scripts that remain in `src/python/` root.

- [ ] **Step 1: Fix `run_experiment_matrix.py` line 26**

Old:
```python
from localization_pipeline import (
```
New:
```python
from pipelines.localization_pipeline import (
```

- [ ] **Step 2: Fix `analyze_voronoi_cells.py` line 30**

Old:
```python
from localization_pipeline import (
```
New:
```python
from pipelines.localization_pipeline import (
```

- [ ] **Step 3: Fix `analyze_heterogeneous.py` line 33**

Old:
```python
from read_jsonc import read_jsonc
```
New:
```python
from utils.read_jsonc import read_jsonc
```

- [ ] **Step 4: Fix `plot_data_generation.py` line 18**

Old:
```python
from read_jsonc import read_jsonc
```
New:
```python
from utils.read_jsonc import read_jsonc
```

- [ ] **Step 5: Fix `plot_mae_heatmap.py` line 34**

Old:
```python
from multi_user_pipeline import (
```
New:
```python
from pipelines.multi_user_pipeline import (
```

- [ ] **Step 6: Fix `gen_voronoi_map.py` line 20**

Old:
```python
from multi_user_pipeline import (
```
New:
```python
from pipelines.multi_user_pipeline import (
```

- [ ] **Step 7: Fix `compare_placements.py` line 52 (inside `_bs_position` function)**

Old:
```python
from multi_user_pipeline import _read_bs_geometry
```
New:
```python
from pipelines.multi_user_pipeline import _read_bs_geometry
```

---

## Task 4 — Python: Fix imports in tests/

**Files:** 5 test files in `src/python/tests/`. `conftest.py` adds `src/python` to `sys.path` so `pipelines.*` and `utils.*` are importable — no change to `conftest.py` needed.

- [ ] **Step 1: Fix `tests/test_read_jsonc.py` line 12**

Old:
```python
from read_jsonc import read_jsonc
```
New:
```python
from utils.read_jsonc import read_jsonc
```

- [ ] **Step 2: Fix `tests/test_adaptive_vmax.py` line 8**

Old:
```python
from multi_user_pipeline import _adaptive_vmax
```
New:
```python
from pipelines.multi_user_pipeline import _adaptive_vmax
```

- [ ] **Step 3: Fix `tests/test_aoa_noise.py` line 14**

Old:
```python
from multi_user_pipeline import _apply_aoa_noise, AOA_NOISE_STD_DEG, AOA_QUANT_STEP_DEG
```
New:
```python
from pipelines.multi_user_pipeline import _apply_aoa_noise, AOA_NOISE_STD_DEG, AOA_QUANT_STEP_DEG
```

- [ ] **Step 4: Fix `tests/test_experiment_runner.py` lines 21 and 117**

Line 21 old:
```python
from multi_user_pipeline import (
```
Line 21 new:
```python
from pipelines.multi_user_pipeline import (
```

Line 117 old:
```python
from multi_user_pipeline import get_model
```
Line 117 new:
```python
from pipelines.multi_user_pipeline import get_model
```

- [ ] **Step 5: Fix `tests/test_feature_engineering.py` line 17**

Old:
```python
from multi_user_pipeline import (
```
New:
```python
from pipelines.multi_user_pipeline import (
```

---

## Task 5 — Python: Verify and commit

- [ ] **Step 1: Run the full Python test suite**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
.venv/Scripts/python -m pytest experiments/09_grid_localization/src/python/tests/ -v 2>&1
```

Expected: all tests pass. If any test shows `ModuleNotFoundError`, check the import in that specific test file.

- [ ] **Step 2: Smoke-test a flat script with cross-package imports**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
python -u experiments/09_grid_localization/src/python/compare_placements.py 2>&1 | head -10
```

Expected: first few lines show `Center BS : ...`, `NE BS : ...`, `Output : ...` with no import errors.

- [ ] **Step 3: Commit the Python reorganisation**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
git add experiments/09_grid_localization/src/python/
git commit -m "refactor(python): Introduce pipelines/ and utils/ packages

Move importable modules into proper packages with __init__.py.
One-off scripts stay flat at src/python/ root for future grouping.

pipelines/: localization_pipeline, localization_pipeline_regression,
            multi_user_pipeline
utils/:     read_jsonc, parse_terminal_output

Update all internal imports across 12 files. Tests unchanged —
conftest.py already adds src/python to sys.path.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6 — MATLAB: Create subdirectories and move files

All commands from `d:/gilad/projects/Academy/CSI-Location`.

- [ ] **Step 1: Create subdirectories**

```bash
cd "d:/gilad/projects/Academy/CSI-Location/experiments/09_grid_localization/src/matlab"
mkdir core
mkdir lib
mkdir runners
```

- [ ] **Step 2: Move core files**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
$m = "experiments/09_grid_localization/src/matlab"
git mv "$m/generate_simulation_data.m" "$m/core/generate_simulation_data.m"
git mv "$m/run_single_user_sim.m"      "$m/core/run_single_user_sim.m"
```

- [ ] **Step 3: Move lib files**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
$m = "experiments/09_grid_localization/src/matlab"
git mv "$m/AreaGenerator.m"  "$m/lib/AreaGenerator.m"
git mv "$m/GeometryUtils.m"  "$m/lib/GeometryUtils.m"
git mv "$m/TrafficUtils.m"   "$m/lib/TrafficUtils.m"
git mv "$m/read_jsonc.m"     "$m/lib/read_jsonc.m"
```

- [ ] **Step 4: Move all runner files**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
$m = "experiments/09_grid_localization/src/matlab"
git mv "$m/run_from_config.m"            "$m/runners/run_from_config.m"
git mv "$m/run_voronoi.m"                "$m/runners/run_voronoi.m"
git mv "$m/run_voronoi_10x10.m"          "$m/runners/run_voronoi_10x10.m"
git mv "$m/run_voronoi_15x15.m"          "$m/runners/run_voronoi_15x15.m"
git mv "$m/run_voronoi_20x20.m"          "$m/runners/run_voronoi_20x20.m"
git mv "$m/run_multi_bs_10x10.m"         "$m/runners/run_multi_bs_10x10.m"
git mv "$m/run_multi_bs_10x10_v2.m"      "$m/runners/run_multi_bs_10x10_v2.m"
git mv "$m/run_multi_user_15x15.m"       "$m/runners/run_multi_user_15x15.m"
git mv "$m/run_ne_bs_15x15.m"            "$m/runners/run_ne_bs_15x15.m"
git mv "$m/run_env_variability_15x15.m"  "$m/runners/run_env_variability_15x15.m"
```

- [ ] **Step 5: Verify**

```bash
git status --short experiments/09_grid_localization/src/matlab/
```

Expected: 16 renames (`R` prefix), no unexpected deletions.

---

## Task 7 — MATLAB: Fix core/ path setup

**Files:**
- Modify: `src/matlab/core/generate_simulation_data.m:42-46`
- Modify: `src/matlab/core/run_single_user_sim.m:46-49`

### `core/generate_simulation_data.m`

- [ ] **Step 1: Replace lines 42–46**

Old (4 lines):
```matlab
script_dir = fileparts(mfilename('fullpath'));
experiment_root = fileparts(fileparts(script_dir));  % experiments/09_grid_localization
workspace_root = fileparts(fileparts(experiment_root));  % CSI-Location
utils_path = fullfile(workspace_root, 'utils');  % Utils at workspace root
addpath(utils_path);
```

New (6 lines):
```matlab
script_dir      = fileparts(mfilename('fullpath'));               % core/
src_matlab_dir  = fileparts(script_dir);                         % src/matlab/
experiment_root = fileparts(fileparts(src_matlab_dir));          % 09_grid_localization/
workspace_root  = fileparts(fileparts(experiment_root));         % CSI-Location/
utils_path      = fullfile(workspace_root, 'utils');
addpath(utils_path);
addpath(fullfile(src_matlab_dir, 'lib'));  % AreaGenerator, GeometryUtils, TrafficUtils, read_jsonc
```

### `core/run_single_user_sim.m`

- [ ] **Step 2: Replace the path setup block (lines 46–49)**

Old:
```matlab
script_dir = fileparts(mfilename('fullpath'));
utils_path = fullfile(workspace_root, 'utils');
addpath(script_dir);
addpath(utils_path);
```

New:
```matlab
script_dir     = fileparts(mfilename('fullpath'));   % core/
src_matlab_dir = fileparts(script_dir);              % src/matlab/
utils_path     = fullfile(workspace_root, 'utils');
addpath(script_dir);                                 % core/ — so generate_simulation_data is findable
addpath(fullfile(src_matlab_dir, 'lib'));             % AreaGenerator, GeometryUtils, TrafficUtils, read_jsonc
addpath(utils_path);                                 % CSI-Location/utils/ — QuaDRiGa
```

---

## Task 8 — MATLAB: Fix runners/ path setup

Each runner needs: (a) `addpath` to `core/` and `lib/`; and (b) if it derives `experiment_root` or `workspace_root`, insert `src_matlab_dir` as an intermediate step.

### Simple runners — only need addpath (6 files)

These runners call `generate_simulation_data` directly with no path setup of their own: `run_voronoi.m`, `run_voronoi_10x10.m`, `run_voronoi_15x15.m`, `run_voronoi_20x20.m`, `run_multi_bs_10x10.m`, `run_multi_bs_10x10_v2.m`.

- [ ] **Step 1: In each simple runner, add these two lines immediately before the first `global` statement**

```matlab
src_matlab_dir = fileparts(fileparts(mfilename('fullpath')));  % runners/../ = src/matlab
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
```

Apply this to all 6 files: `runners/run_voronoi.m`, `runners/run_voronoi_10x10.m`, `runners/run_voronoi_15x15.m`, `runners/run_voronoi_20x20.m`, `runners/run_multi_bs_10x10.m`, `runners/run_multi_bs_10x10_v2.m`.

### Complex runners — addpath + path derivation fix (4 files)

`run_multi_user_15x15.m`, `run_ne_bs_15x15.m`, `run_env_variability_15x15.m` all have this block (at lines 43–45, 45–47, 49–51 respectively):

```matlab
script_dir     = fileparts(mfilename('fullpath'));
experiment_root = fileparts(fileparts(script_dir));
workspace_root  = fileparts(fileparts(experiment_root));
```

- [ ] **Step 2: Replace that block in each of the three files**

New block (introduce `src_matlab_dir`):
```matlab
script_dir      = fileparts(mfilename('fullpath'));          % runners/
src_matlab_dir  = fileparts(script_dir);                    % src/matlab/
experiment_root = fileparts(fileparts(src_matlab_dir));     % 09_grid_localization/
workspace_root  = fileparts(fileparts(experiment_root));    % CSI-Location/
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
```

Apply to: `runners/run_multi_user_15x15.m`, `runners/run_ne_bs_15x15.m`, `runners/run_env_variability_15x15.m`.

`run_from_config.m` has a similar but slightly different block (lines 39–42):

```matlab
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);
```

- [ ] **Step 3: Replace the `run_from_config.m` path block**

New:
```matlab
script_dir      = fileparts(mfilename('fullpath'));          % runners/
src_matlab_dir  = fileparts(script_dir);                    % src/matlab/
project_root    = fileparts(fileparts(src_matlab_dir));     % 09_grid_localization/
workspace_root  = fileparts(fileparts(project_root));       % CSI-Location/
utils_path      = fullfile(workspace_root, 'utils');
addpath(utils_path);
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
```

---

## Task 9 — MATLAB: Fix tests/ and commit MATLAB changes

**Files:**
- Modify: `src/matlab/tests/TestReadJsonc.m:15-16`
- Modify: `src/matlab/tests/TestGridGeneration.m` (header comment only)

- [ ] **Step 1: Fix `TestReadJsonc.m` lines 14–16**

`read_jsonc.m` moved from `src/matlab/` to `src/matlab/lib/`. Update `addReadJsoncPath`:

Old:
```matlab
function addReadJsoncPath(tc)
    tc.ScriptDir = fullfile(fileparts(mfilename('fullpath')), '..');
    addpath(tc.ScriptDir);
end
```

New:
```matlab
function addReadJsoncPath(tc)
    test_dir       = fileparts(mfilename('fullpath'));    % tests/
    src_matlab_dir = fileparts(test_dir);                 % src/matlab/
    tc.ScriptDir   = fullfile(src_matlab_dir, 'lib');
    addpath(tc.ScriptDir);
end
```

- [ ] **Step 2: Update `cd` instruction in `TestReadJsonc.m` header comment (line 5)**

Old:
```matlab
%   cd experiments/09_grid_localization/src/matlab
%   results = runtests('tests/TestReadJsonc');
```

New:
```matlab
%   cd experiments/09_grid_localization/src/matlab
%   results = runtests('tests/TestReadJsonc');  % run from src/matlab (unchanged)
```

No path change needed — the `cd` instruction stays the same since `tests/` is still in `src/matlab/`.

- [ ] **Step 3: Add `addpath` block to `TestGridGeneration.m` (after the class header comment)**

`TestGridGeneration` has no path setup and replicates logic inline, but adding `core/` and `lib/` to the path makes it robust. Insert after line 11 (the blank line after the run instructions):

```matlab
    methods (TestClassSetup)
        function addPaths(tc)
            test_dir       = fileparts(mfilename('fullpath'));
            src_matlab_dir = fileparts(test_dir);
            addpath(fullfile(src_matlab_dir, 'core'));
            addpath(fullfile(src_matlab_dir, 'lib'));
        end
    end
```

- [ ] **Step 4: Commit the MATLAB reorganisation**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
git add experiments/09_grid_localization/src/matlab/
git commit -m "refactor(matlab): Introduce core/ lib/ runners/ subdirectories

Move simulation engine to core/, reusable classes to lib/,
and all experiment entry points to runners/.

Each runner gains addpath calls to core/ and lib/.
Complex runners (run_multi_user_15x15, run_ne_bs_15x15,
run_env_variability_15x15, run_from_config) get an extra
src_matlab_dir intermediate variable in their path derivation
to account for the extra directory level.

generate_simulation_data.m and run_single_user_sim.m updated
to add lib/ to the MATLAB path alongside CSI-Location/utils/.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 10 — Docs: Update CLAUDE.md, technical_documentation.md, TASKS.md

**Files:**
- Modify: `CLAUDE.md` (run commands + module structure diagram)
- Modify: `docs/Project_documentation/technical_documentation.md` (§2 module listing)
- Modify: `docs/11_04_plan/TASKS.md` (mark MATLAB reorg task done)

- [ ] **Step 1: Update `CLAUDE.md` — Python module structure section**

Find the block under `### Python module structure` and update to:

```markdown
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
```

- [ ] **Step 2: Update `CLAUDE.md` — CLI Patterns section run commands**

Find the CLI examples and update:

Old:
```bash
python localization_pipeline.py --data-dir <path> --model xgboost ...
```
New:
```bash
python pipelines/localization_pipeline.py --data-dir <path> --model xgboost ...
```

Old:
```bash
python multi_user_pipeline.py --data-dir <path> ...
```
New:
```bash
python pipelines/multi_user_pipeline.py --data-dir <path> ...
```

- [ ] **Step 3: Update `CLAUDE.md` — Testing section run command**

Old:
```bash
.venv/Scripts/python -m pytest experiments/09_grid_localization/src/python/tests/ -v
```
This stays the same — tests/ location unchanged.

Find and update the MATLAB run command comment to reflect the new cd path for runners:

Old:
```
# MATLAB — from src/matlab/
results = runtests('tests/TestGridGeneration'); disp(results)
```
Add note that runners are now in `runners/` subfolder:
```
# MATLAB — from src/matlab/ (tests unchanged; runners are in runners/)
results = runtests('tests/TestGridGeneration'); disp(results)
```

- [ ] **Step 4: Update `technical_documentation.md` §2 module structure**

Find the Python module listing under §2 and update file paths to match the new locations (same content as Step 1 above, adapted to the documentation format).

- [ ] **Step 5: Update `docs/11_04_plan/TASKS.md` — mark MATLAB reorg done**

Find:
```markdown
## Deferred Engineering: MATLAB Directory Reorganisation
```

Update its status line to:
```markdown
## Deferred Engineering: MATLAB Directory Reorganisation — ✅ done (May 2026)
```

- [ ] **Step 6: Commit docs**

```bash
cd "d:/gilad/projects/Academy/CSI-Location"
git add CLAUDE.md \
        experiments/09_grid_localization/docs/Project_documentation/technical_documentation.md \
        experiments/09_grid_localization/docs/11_04_plan/TASKS.md
git commit -m "docs: Update paths after src/ reorganisation

Update CLAUDE.md run commands and module listing, technical_documentation.md
§2 file structure, and mark MATLAB directory reorganisation task as complete.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All spec requirements covered — Python package creation (Task 1), import updates in pipelines/ (Task 2), flat scripts (Task 3), tests (Task 4), verify + commit (Task 5), MATLAB moves (Task 6), core/ fixes (Task 7), runners/ fixes (Task 8), tests/ fixes + commit (Task 9), docs (Task 10).
- [x] **No placeholders:** All steps contain exact file paths, line numbers, and code.
- [x] **Type consistency:** No function names invented or cross-referenced; all paths derived from actual file contents inspected before writing this plan.
- [x] **MATLAB path derivation verified:** From `runners/`, `fileparts(fileparts(src_matlab_dir))` correctly resolves to `09_grid_localization/` (the experiment root), matching the intent of the original scripts.
- [x] **`conftest.py` sys.path:** Already adds `src/python` — no change needed; `pipelines.*` and `utils.*` are reachable.
- [x] **Simple vs complex runners distinguished:** 6 simple runners get only addpath; 4 complex runners also get path derivation update.
