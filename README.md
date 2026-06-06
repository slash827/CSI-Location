# CSI-Based Indoor Localization — Transition Feature Study

Research project proving that **movement history (transition features) improves indoor localization accuracy** across all tested conditions. MATLAB + QuaDRiGa for channel simulation; Python + scikit-learn/XGBoost for ML.

---

## Key Results

Main experiment: multi-user, 15×15 grid (225 cells, 2 m spacing), mixed Voronoi environment (highway / shopping / residential / park), 5 heterogeneous devices.

| Feature Set | XGBoost Acc | XGBoost MAE |
|---|---|---|
| BASE (static RSS+SINR) | 25.7% | 8.56 m |
| BASE_H3 (+ history h=3) | 48.9% | 4.64 m |
| BASE_A_H3 (+ AoA) | 83.2% | 0.40 m |
| BASE_A_H3_dp (+ device params) | **84.2%** | **0.37 m** |

History alone adds **+23 pp** regardless of BS placement. Full technical results in `experiments/09_grid_localization/docs/Project_documentation/technical_documentation.md`.

---

## Project Structure

```
CSI-Location/
├── experiments/
│   ├── 01_basics/                  # QuaDRiGa fundamentals (tutorial)
│   ├── 02_single_ue_analysis/      # RSS/SINR/CQI metrics (tutorial)
│   ├── 03_ue_movement/             # Moving UE trajectory simulation
│   ├── 04_data_generation_LOS/     # Dataset generation, LOS scenario
│   ├── 05_data_generation_NLOS/    # Dataset generation, NLOS scenario
│   ├── 06_urban_scenario/          # Urban multi-path experiments
│   ├── 07_csi_distribution/        # CSI feature distribution analysis
│   ├── 08_static_vs_walk/          # Early static vs transition comparison
│   └── 09_grid_localization/       # MAIN EXPERIMENT — see below
│       ├── configs/                # JSONC experiment configs
│       ├── src/
│       │   ├── matlab/             # QuaDRiGa simulation pipeline
│       │   └── python/             # ML pipeline (train/eval/report)
│       ├── docs/                   # Technical and research documentation
│       ├── requirements.txt
│       └── TASKS.md
├── utils/                          # Shared MATLAB utilities
│   ├── ExperimentUtils.m           # Channel setup, FFT, file I/O helpers
│   └── CSIMetrics.m                # RSS / SINR / CQI computation
├── results/                        # gitignored — local only
└── docs/                           # Project-level guides and references
```

---

## Prerequisites

**MATLAB** (simulation)
- QuaDRiGa v2.8.1 — add to MATLAB path:
  ```matlab
  addpath(genpath('path/to/QuaDRiGa'));
  savepath;
  ```

**Python** (ML pipeline)
```bash
cd experiments/09_grid_localization
pip install -r requirements.txt
```

---

## Main Experiment (09_grid_localization)

All significant ML work lives here. Full documentation:
- `experiments/09_grid_localization/docs/Project_documentation/technical_documentation.md` — system design, feature engineering, all results
- `experiments/09_grid_localization/docs/Project_documentation/research_documentation.md` — research narrative

### Run simulation (MATLAB)
```matlab
% Edit configs/multi_user_voronoi_15x15_config.jsonc first
cd experiments/09_grid_localization/src/matlab/runners
run_multi_user_voronoi_15x15
```

### Run ML pipeline (Python)
```powershell
python experiments\09_grid_localization\src\python\pipelines\multi_user_pipeline.py `
  --data-dir results\grid_localization\grid_15x15\sim_data_<timestamp> `
  --out-dir results\multi_user_voronoi_15x15 `
  --models rf xgboost `
  --history 3
```

### Run tests
```bash
python -m pytest experiments/09_grid_localization/src/python/tests/ -v
```

---

## Learning Path (experiments 01–08)

Experiments 01–08 are exploratory/tutorial work that preceded the main experiment.

| Experiment | Focus |
|---|---|
| 01_basics | QuaDRiGa setup, CSI matrix structure |
| 02_single_ue_analysis | RSS/SINR/CQI extraction, parameter effects |
| 03_ue_movement | Moving UE, trajectory simulation |
| 04–05_data_generation | Dataset generation under LOS / NLOS |
| 06_urban_scenario | Urban multi-path |
| 07_csi_distribution | Feature distribution analysis |
| 08_static_vs_walk | Early static vs history comparison (Gaussian classifier) |

---

## Results Directory

`results/` is gitignored. Key subdirectories after running the main experiment:

```
results/
├── grid_localization/          # Raw simulation data (.mat files)
├── multi_user_voronoi_15x15/  # Center-BS ML results + plots
│   └── csvs/results_summary.csv
└── ne_bs_voronoi_15x15/       # NE-corner BS results + plots
    └── csvs/results_summary.csv
```

---

*Last updated: 2026-06-06*
