# Pipeline Report — centre_bs_nlos_30

**Generated:** 2026-10-14 00:38:50  
**Python:**    3.11.2  
**Platform:**  Windows 10  

---

## Reproduce This Run

```bash
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py --data-dir results/grid_localization/grid_15x15/sim_data_multi_user_2026-10-13_15-47-39/ --out-dir results/controlled_grid_2026_10/centre_bs_nlos_30 --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8 --run-only BASE BASE_H3 BASE_dp BASE_H3_dp BASE_A BASE_A_H3 BASE_A_dp BASE_A_H3_dp
```

---

## Run Configuration

| Parameter | Value |
|---|---|
| Data directory | `results/grid_localization/grid_15x15/sim_data_multi_user_2026-10-13_15-47-39/` |
| Output directory | `results\controlled_grid_2026_10\centre_bs_nlos_30` |
| Models | xgboost, rf |
| Primary history depth | 3 |
| Train/test split | 80 / 20 chronological per user |
| Hyperparameter tuning | No (defaults) |
| Run-only filter | BASE, BASE_H3, BASE_dp, BASE_H3_dp, BASE_A, BASE_A_H3, BASE_A_dp, BASE_A_H3_dp |
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
| xgboost | BASE | 14.43 | 10.2124 | 5.1062 | 108.3 |
| xgboost | BASE_A | 63.92 | 1.9946 | 0.9973 | 80.05 |
| xgboost | BASE_A_H3 | 68.16 | 1.3854 | 0.6927 | 94.06 |
| xgboost | BASE_A_H3_dp | 68.89 | 1.3460 | 0.6730 | 114.31 |
| xgboost | BASE_A_dp | 65.41 | 1.8678 | 0.9339 | 93.11 |
| xgboost | BASE_H3 | 29.61 | 7.0284 | 3.5142 | 107.96 |
| xgboost | BASE_H3_dp | 35.16 | 5.3639 | 2.6819 | 108.62 |
| xgboost | BASE_dp | 26.83 | 7.3198 | 3.6599 | 93.23 |
| rf | BASE | 23.86 | 9.0181 | 4.5091 | 14.15 |
| rf | BASE_A | 64.83 | 1.9738 | 0.9869 | 17.68 |
| rf | BASE_A_H3 | 67.25 | 1.3849 | 0.6925 | 31.06 |
| rf | BASE_A_H3_dp | 67.92 | 1.3051 | 0.6525 | 24.72 |
| rf | BASE_A_dp | 67.53 | 1.7582 | 0.8791 | 11.09 |
| rf | BASE_H3 | 35.36 | 5.9549 | 2.9774 | 27.42 |
| rf | BASE_H3_dp | 40.81 | 4.5104 | 2.2552 | 31.4 |
| rf | BASE_dp | 31.93 | 6.6987 | 3.3494 | 14.24 |
