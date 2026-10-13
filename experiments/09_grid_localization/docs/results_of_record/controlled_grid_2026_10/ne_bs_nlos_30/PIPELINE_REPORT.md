# Pipeline Report — ne_bs_nlos_30

**Generated:** 2026-10-14 00:28:47  
**Python:**    3.11.2  
**Platform:**  Windows 10  

---

## Reproduce This Run

```bash
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_15-47-28/ --out-dir results/controlled_grid_2026_10/ne_bs_nlos_30 --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8 --run-only BASE BASE_H3 BASE_dp BASE_H3_dp BASE_A BASE_A_H3 BASE_A_dp BASE_A_H3_dp
```

---

## Run Configuration

| Parameter | Value |
|---|---|
| Data directory | `results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_15-47-28/` |
| Output directory | `results\controlled_grid_2026_10\ne_bs_nlos_30` |
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
| xgboost | BASE | 12.58 | 10.3612 | 5.1806 | 182.24 |
| xgboost | BASE_A | 24.23 | 6.7231 | 3.3615 | 100.06 |
| xgboost | BASE_A_H3 | 32.05 | 4.8492 | 2.4246 | 129.59 |
| xgboost | BASE_A_H3_dp | 35.03 | 4.1253 | 2.0626 | 136.52 |
| xgboost | BASE_A_dp | 27.82 | 5.6450 | 2.8225 | 106.9 |
| xgboost | BASE_H3 | 25.82 | 7.3593 | 3.6797 | 196.04 |
| xgboost | BASE_H3_dp | 30.56 | 5.7430 | 2.8715 | 211.12 |
| xgboost | BASE_dp | 22.65 | 7.3009 | 3.6504 | 249.11 |
| rf | BASE | 20.10 | 9.0223 | 4.5111 | 16.43 |
| rf | BASE_A | 27.13 | 6.4968 | 3.2484 | 16.19 |
| rf | BASE_A_H3 | 35.22 | 4.4668 | 2.2334 | 31.14 |
| rf | BASE_A_H3_dp | 37.15 | 3.7579 | 1.8789 | 26.37 |
| rf | BASE_A_dp | 29.49 | 5.5442 | 2.7721 | 10.62 |
| rf | BASE_H3 | 29.37 | 6.6815 | 3.3407 | 30.71 |
| rf | BASE_H3_dp | 34.29 | 5.2102 | 2.6051 | 33.24 |
| rf | BASE_dp | 26.79 | 6.9499 | 3.4749 | 14.89 |
