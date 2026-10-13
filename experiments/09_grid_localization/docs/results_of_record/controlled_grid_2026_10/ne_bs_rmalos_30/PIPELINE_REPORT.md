# Pipeline Report — ne_bs_rmalos_30

**Generated:** 2026-10-13 12:31:04  
**Python:**    3.11.2  
**Platform:**  Windows 10  

---

## Reproduce This Run

```bash
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_10-43-29/ --out-dir results/controlled_grid_2026_10/ne_bs_rmalos_30 --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8
```

---

## Run Configuration

| Parameter | Value |
|---|---|
| Data directory | `results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_10-43-29/` |
| Output directory | `results\controlled_grid_2026_10\ne_bs_rmalos_30` |
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
| xgboost | BASE | 31.42 | 6.0325 | 3.0163 | 59.86 |
| xgboost | BASE_A | 45.97 | 3.3895 | 1.6948 | 108.31 |
| xgboost | BASE_A_H1 | 52.33 | 2.7117 | 1.3558 | 120.81 |
| xgboost | BASE_A_H2 | 52.60 | 2.5773 | 1.2886 | 126.19 |
| xgboost | BASE_A_H3 | 52.57 | 2.5069 | 1.2534 | 123.79 |
| xgboost | BASE_A_H3_delta | 51.22 | 2.8425 | 1.4212 | 124.76 |
| xgboost | BASE_A_H3_dp | 52.76 | 2.4695 | 1.2347 | 141.96 |
| xgboost | BASE_A_H3_dp_delta | 51.74 | 2.7945 | 1.3973 | 155.49 |
| xgboost | BASE_A_dp | 46.41 | 3.3208 | 1.6604 | 124.12 |
| xgboost | BASE_A_uid | 46.58 | 3.2993 | 1.6496 | 107.2 |
| xgboost | BASE_H1 | 47.99 | 3.6954 | 1.8477 | 102.98 |
| xgboost | BASE_H2 | 48.26 | 3.5422 | 1.7711 | 98.43 |
| xgboost | BASE_H3 | 48.61 | 3.4783 | 1.7392 | 110.0 |
| xgboost | BASE_H3_delta | 46.97 | 3.7991 | 1.8995 | 103.44 |
| xgboost | BASE_H3_dp | 49.81 | 3.2962 | 1.6481 | 105.51 |
| xgboost | BASE_H3_dp_delta | 48.66 | 3.5317 | 1.7658 | 119.51 |
| xgboost | BASE_H3_uid | 49.96 | 3.2725 | 1.6362 | 116.41 |
| xgboost | BASE_dp | 42.33 | 4.2390 | 2.1195 | 62.39 |
| xgboost | BASE_uid | 41.55 | 4.2848 | 2.1424 | 103.81 |
| xgboost | cross_user_BASE_A_H3 | 47.59 | 3.8013 | 1.9007 | 118.55 |
| xgboost | cross_user_BASE_A_dp | 41.84 | 4.3746 | 2.1873 | 88.15 |
| xgboost | cross_user_BASE_A_uid | 42.15 | 4.3840 | 2.1920 | 112.28 |
| xgboost | cross_user_BASE_H3 | 45.20 | 4.4049 | 2.2025 | 85.66 |
| xgboost | cross_user_BASE_H3_dp | 45.34 | 4.3213 | 2.1607 | 122.11 |
| xgboost | cross_user_BASE_H3_uid | 45.76 | 4.4807 | 2.2404 | 83.47 |
| rf | BASE | 50.47 | 3.8831 | 1.9416 | 15.6 |
| rf | BASE_A | 54.07 | 2.9406 | 1.4703 | 16.01 |
| rf | BASE_A_H1 | 56.81 | 2.4279 | 1.2140 | 17.46 |
| rf | BASE_A_H2 | 58.09 | 2.2511 | 1.1256 | 23.36 |
| rf | BASE_A_H3 | 58.17 | 2.1968 | 1.0984 | 31.47 |
| rf | BASE_A_H3_delta | 50.62 | 2.9461 | 1.4730 | 31.94 |
| rf | BASE_A_H3_dp | 57.10 | 2.1959 | 1.0979 | 27.3 |
| rf | BASE_A_H3_dp_delta | 51.36 | 2.8326 | 1.4163 | 27.53 |
| rf | BASE_A_dp | 52.04 | 3.0597 | 1.5299 | 10.73 |
| rf | BASE_A_uid | 53.26 | 2.9831 | 1.4916 | 13.93 |
| rf | BASE_H1 | 56.52 | 3.1362 | 1.5681 | 29.01 |
| rf | BASE_H2 | 56.86 | 2.9282 | 1.4641 | 28.7 |
| rf | BASE_H3 | 55.39 | 2.9248 | 1.4624 | 28.79 |
| rf | BASE_H3_delta | 46.68 | 3.8141 | 1.9070 | 30.64 |
| rf | BASE_H3_dp | 56.65 | 2.7499 | 1.3749 | 32.05 |
| rf | BASE_H3_dp_delta | 51.82 | 3.2417 | 1.6209 | 35.92 |
| rf | BASE_H3_uid | 57.50 | 2.7803 | 1.3901 | 38.25 |
| rf | BASE_dp | 52.40 | 3.5605 | 1.7802 | 14.53 |
| rf | BASE_uid | 52.34 | 3.5519 | 1.7759 | 12.25 |
| rf | cross_user_BASE_A_H3 | 50.66 | 3.6983 | 1.8491 | 25.11 |
| rf | cross_user_BASE_A_dp | 45.91 | 4.2716 | 2.1358 | 10.04 |
| rf | cross_user_BASE_A_uid | 47.11 | 4.4543 | 2.2272 | 10.47 |
| rf | cross_user_BASE_H3 | 48.78 | 4.1746 | 2.0873 | 23.95 |
| rf | cross_user_BASE_H3_dp | 49.30 | 4.1059 | 2.0529 | 27.27 |
| rf | cross_user_BASE_H3_uid | 50.38 | 4.1735 | 2.0868 | 32.47 |

### Learning Curve — XGBOOST (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 31.42 | 6.0325 | 3.0163 |
| 1 | 47.99 | 3.6954 | 1.8477 |
| 2 | 48.26 | 3.5422 | 1.7711 |
| 3 | 48.61 | 3.4783 | 1.7392 |
| 4 | 48.89 | 3.4586 | 1.7293 |

### Learning Curve — RF (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 50.47 | 3.8831 | 1.9416 |
| 1 | 56.52 | 3.1362 | 1.5681 |
| 2 | 56.86 | 2.9282 | 1.4641 |
| 3 | 55.39 | 2.9248 | 1.4624 |
| 4 | 55.78 | 2.9701 | 1.4851 |
