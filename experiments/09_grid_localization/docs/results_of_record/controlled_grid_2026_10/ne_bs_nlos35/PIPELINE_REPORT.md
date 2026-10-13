# Pipeline Report — ne_bs

**Generated:** 2026-10-13 05:14:20  
**Python:**    3.11.2  
**Platform:**  Windows 10  

---

## Reproduce This Run

```bash
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_01-02-42/ --out-dir results/controlled_grid_2026_10/ne_bs --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8
```

---

## Run Configuration

| Parameter | Value |
|---|---|
| Data directory | `results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_01-02-42/` |
| Output directory | `results\controlled_grid_2026_10\ne_bs` |
| Models | xgboost, rf |
| Primary history depth | 3 |
| Train/test split | 80 / 20 chronological per user |
| Hyperparameter tuning | No (defaults) |
| Total samples | 450,005 |
| Users | 5 |
| Grid classes | 225 |
| Grid spacing (m) | 2.0 |

---

## Hyperparameters (defaults — no tuning)

### RF

| Parameter | Value |
|---|---|
| `n_estimators` | 50 |
| `max_depth` | 15 |
| `min_samples_leaf` | 20 |
| `max_features` | sqrt |

### XGBoost

| Parameter | Value |
|---|---|
| `n_estimators` | 50 |
| `max_depth` | 5 |
| `learning_rate` | 0.15 |
| `subsample` | 0.8 |
| `colsample_bytree` | 0.8 |

---

## Results Summary

| Model | Experiment | Accuracy (%) | MAE (m) | MPE (pts) | Train time (s) |
|---|---|---|---|---|---|
| xgboost | BASE | 11.31 | 10.4940 | 5.2470 | 190.19 |
| xgboost | BASE_A | 23.24 | 6.7432 | 3.3716 | 293.41 |
| xgboost | BASE_A_H1 | 29.61 | 5.4477 | 2.7238 | 207.22 |
| xgboost | BASE_A_H2 | 30.38 | 5.0747 | 2.5373 | 231.98 |
| xgboost | BASE_A_H3 | 30.88 | 4.8631 | 2.4315 | 272.95 |
| xgboost | BASE_A_H3_delta | 28.10 | 5.6095 | 2.8047 | 244.76 |
| xgboost | BASE_A_H3_dp | 33.37 | 4.1932 | 2.0966 | 246.84 |
| xgboost | BASE_A_H3_dp_delta | 31.02 | 4.7848 | 2.3924 | 230.39 |
| xgboost | BASE_A_dp | 26.29 | 5.7642 | 2.8821 | 205.24 |
| xgboost | BASE_A_uid | 27.86 | 5.5411 | 2.7705 | 278.71 |
| xgboost | BASE_H1 | 23.10 | 8.0623 | 4.0311 | 262.66 |
| xgboost | BASE_H2 | 24.28 | 7.5919 | 3.7960 | 184.61 |
| xgboost | BASE_H3 | 24.65 | 7.4227 | 3.7113 | 193.93 |
| xgboost | BASE_H3_delta | 22.28 | 7.9624 | 3.9812 | 222.57 |
| xgboost | BASE_H3_dp | 29.40 | 5.8494 | 2.9247 | 197.84 |
| xgboost | BASE_H3_dp_delta | 27.07 | 6.3368 | 3.1684 | 199.07 |
| xgboost | BASE_H3_uid | 30.71 | 5.5688 | 2.7844 | 218.17 |
| xgboost | BASE_dp | 21.75 | 7.5216 | 3.7608 | 164.49 |
| xgboost | BASE_uid | 23.35 | 7.0603 | 3.5302 | 189.82 |
| xgboost | cross_user_BASE_A_H3 | 29.30 | 5.7841 | 2.8920 | 265.46 |
| xgboost | cross_user_BASE_A_dp | 23.40 | 6.7508 | 3.3754 | 173.54 |
| xgboost | cross_user_BASE_A_uid | 24.71 | 7.0058 | 3.5029 | 204.16 |
| xgboost | cross_user_BASE_H3 | 23.59 | 8.1699 | 4.0850 | 147.92 |
| xgboost | cross_user_BASE_H3_dp | 26.04 | 7.0282 | 3.5141 | 191.61 |
| xgboost | cross_user_BASE_H3_uid | 27.35 | 6.8970 | 3.4485 | 169.61 |
| rf | BASE | 18.82 | 9.1972 | 4.5986 | 21.19 |
| rf | BASE_A | 25.96 | 6.4957 | 3.2479 | 16.78 |
| rf | BASE_A_H1 | 31.67 | 5.2464 | 2.6232 | 16.57 |
| rf | BASE_A_H2 | 33.70 | 4.7228 | 2.3614 | 24.35 |
| rf | BASE_A_H3 | 34.29 | 4.5140 | 2.2570 | 31.57 |
| rf | BASE_A_H3_delta | 26.58 | 5.8650 | 2.9325 | 33.07 |
| rf | BASE_A_H3_dp | 36.15 | 3.7971 | 1.8985 | 26.21 |
| rf | BASE_A_H3_dp_delta | 30.16 | 4.8244 | 2.4122 | 27.95 |
| rf | BASE_A_dp | 28.05 | 5.6482 | 2.8241 | 11.11 |
| rf | BASE_A_uid | 30.37 | 5.3548 | 2.6774 | 13.19 |
| rf | BASE_H1 | 26.73 | 7.6274 | 3.8137 | 42.07 |
| rf | BASE_H2 | 28.47 | 7.0044 | 3.5022 | 39.74 |
| rf | BASE_H3 | 28.51 | 6.7337 | 3.3669 | 40.38 |
| rf | BASE_H3_delta | 21.34 | 7.7664 | 3.8832 | 32.87 |
| rf | BASE_H3_dp | 33.16 | 5.2777 | 2.6388 | 37.64 |
| rf | BASE_H3_dp_delta | 29.19 | 5.8438 | 2.9219 | 34.47 |
| rf | BASE_H3_uid | 34.41 | 5.1384 | 2.5692 | 41.9 |
| rf | BASE_dp | 25.36 | 7.1973 | 3.5987 | 19.25 |
| rf | BASE_uid | 26.93 | 6.7848 | 3.3924 | 17.89 |
| rf | cross_user_BASE_A_H3 | 31.02 | 5.6907 | 2.8453 | 24.74 |
| rf | cross_user_BASE_A_dp | 24.33 | 6.7103 | 3.3551 | 9.25 |
| rf | cross_user_BASE_A_uid | 26.45 | 6.7347 | 3.3673 | 10.83 |
| rf | cross_user_BASE_H3 | 26.18 | 7.8023 | 3.9011 | 23.55 |
| rf | cross_user_BASE_H3_dp | 28.54 | 6.7588 | 3.3794 | 27.06 |
| rf | cross_user_BASE_H3_uid | 29.32 | 6.9176 | 3.4588 | 32.41 |

### Learning Curve — XGBOOST (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 11.31 | 10.4940 | 5.2470 |
| 1 | 23.10 | 8.0623 | 4.0311 |
| 2 | 24.28 | 7.5919 | 3.7960 |
| 3 | 24.65 | 7.4227 | 3.7113 |
| 4 | 25.15 | 7.2585 | 3.6293 |

### Learning Curve — RF (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 18.82 | 9.1972 | 4.5986 |
| 1 | 26.73 | 7.6274 | 3.8137 |
| 2 | 28.47 | 7.0044 | 3.5022 |
| 3 | 28.51 | 6.7337 | 3.3669 |
| 4 | 29.03 | 6.6903 | 3.3451 |
