# Pipeline Report — centre_bs

**Generated:** 2026-10-13 05:03:14  
**Python:**    3.11.2  
**Platform:**  Windows 10  

---

## Reproduce This Run

```bash
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py --data-dir results/grid_localization/grid_15x15/sim_data_multi_user_2026-10-13_01-02-45/ --out-dir results/controlled_grid_2026_10/centre_bs --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8
```

---

## Run Configuration

| Parameter | Value |
|---|---|
| Data directory | `results/grid_localization/grid_15x15/sim_data_multi_user_2026-10-13_01-02-45/` |
| Output directory | `results\controlled_grid_2026_10\centre_bs` |
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
| xgboost | BASE | 13.83 | 10.3995 | 5.1998 | 192.93 |
| xgboost | BASE_A | 63.85 | 1.9703 | 0.9851 | 284.22 |
| xgboost | BASE_A_H1 | 67.26 | 1.4994 | 0.7497 | 226.93 |
| xgboost | BASE_A_H2 | 67.52 | 1.4131 | 0.7066 | 227.3 |
| xgboost | BASE_A_H3 | 67.46 | 1.3728 | 0.6864 | 263.86 |
| xgboost | BASE_A_H3_delta | 65.90 | 1.5863 | 0.7932 | 240.43 |
| xgboost | BASE_A_H3_dp | 68.42 | 1.3174 | 0.6587 | 239.02 |
| xgboost | BASE_A_H3_dp_delta | 67.37 | 1.4656 | 0.7328 | 227.77 |
| xgboost | BASE_A_dp | 65.41 | 1.8335 | 0.9167 | 219.18 |
| xgboost | BASE_A_uid | 65.40 | 1.8353 | 0.9176 | 276.02 |
| xgboost | BASE_H1 | 26.62 | 7.9288 | 3.9644 | 264.59 |
| xgboost | BASE_H2 | 27.51 | 7.4859 | 3.7429 | 177.07 |
| xgboost | BASE_H3 | 28.24 | 7.2447 | 3.6224 | 192.7 |
| xgboost | BASE_H3_delta | 25.85 | 7.8597 | 3.9299 | 227.58 |
| xgboost | BASE_H3_dp | 33.75 | 5.5306 | 2.7653 | 196.64 |
| xgboost | BASE_H3_dp_delta | 31.83 | 5.9903 | 2.9951 | 194.79 |
| xgboost | BASE_H3_uid | 35.28 | 5.1504 | 2.5752 | 184.34 |
| xgboost | BASE_dp | 25.88 | 7.3399 | 3.6700 | 165.3 |
| xgboost | BASE_uid | 27.73 | 6.7311 | 3.3655 | 189.06 |
| xgboost | cross_user_BASE_A_H3 | 61.60 | 1.9788 | 0.9894 | 254.92 |
| xgboost | cross_user_BASE_A_dp | 58.12 | 2.6343 | 1.3172 | 112.41 |
| xgboost | cross_user_BASE_A_uid | 58.47 | 2.5966 | 1.2983 | 191.92 |
| xgboost | cross_user_BASE_H3 | 27.05 | 7.9141 | 3.9571 | 156.59 |
| xgboost | cross_user_BASE_H3_dp | 30.14 | 6.6230 | 3.3115 | 184.11 |
| xgboost | cross_user_BASE_H3_uid | 31.66 | 6.7945 | 3.3972 | 151.9 |
| rf | BASE | 22.65 | 9.1799 | 4.5899 | 16.6 |
| rf | BASE_A | 64.78 | 1.9245 | 0.9623 | 17.24 |
| rf | BASE_A_H1 | 67.82 | 1.4738 | 0.7369 | 16.03 |
| rf | BASE_A_H2 | 67.46 | 1.3846 | 0.6923 | 26.58 |
| rf | BASE_A_H3 | 67.34 | 1.3458 | 0.6729 | 36.87 |
| rf | BASE_A_H3_delta | 64.50 | 1.6709 | 0.8354 | 36.41 |
| rf | BASE_A_H3_dp | 67.85 | 1.2903 | 0.6451 | 31.18 |
| rf | BASE_A_H3_dp_delta | 66.27 | 1.5027 | 0.7513 | 27.36 |
| rf | BASE_A_dp | 67.26 | 1.7258 | 0.8629 | 12.11 |
| rf | BASE_A_uid | 67.10 | 1.7525 | 0.8763 | 13.51 |
| rf | BASE_H1 | 32.14 | 7.2179 | 3.6089 | 31.32 |
| rf | BASE_H2 | 34.34 | 6.4749 | 3.2374 | 33.51 |
| rf | BASE_H3 | 34.32 | 6.1280 | 3.0640 | 32.26 |
| rf | BASE_H3_delta | 27.94 | 7.2419 | 3.6210 | 34.8 |
| rf | BASE_H3_dp | 39.72 | 4.6633 | 2.3317 | 33.53 |
| rf | BASE_H3_dp_delta | 35.72 | 5.3326 | 2.6663 | 36.77 |
| rf | BASE_H3_uid | 41.75 | 4.3105 | 2.1553 | 43.28 |
| rf | BASE_dp | 30.58 | 6.8081 | 3.4041 | 16.44 |
| rf | BASE_uid | 32.79 | 6.2222 | 3.1111 | 12.69 |
| rf | cross_user_BASE_A_H3 | 61.31 | 1.7829 | 0.8914 | 23.46 |
| rf | cross_user_BASE_A_dp | 58.18 | 2.5502 | 1.2751 | 8.3 |
| rf | cross_user_BASE_A_uid | 59.43 | 2.6623 | 1.3311 | 13.92 |
| rf | cross_user_BASE_H3 | 30.86 | 7.2688 | 3.6344 | 24.73 |
| rf | cross_user_BASE_H3_dp | 33.73 | 6.1538 | 3.0769 | 25.58 |
| rf | cross_user_BASE_H3_uid | 35.48 | 6.7021 | 3.3511 | 29.83 |

### Learning Curve — XGBOOST (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 13.83 | 10.3995 | 5.1998 |
| 1 | 26.62 | 7.9288 | 3.9644 |
| 2 | 27.51 | 7.4859 | 3.7429 |
| 3 | 28.24 | 7.2447 | 3.6224 |
| 4 | 28.54 | 7.0612 | 3.5306 |

### Learning Curve — RF (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 22.65 | 9.1799 | 4.5899 |
| 1 | 32.14 | 7.2179 | 3.6089 |
| 2 | 34.34 | 6.4749 | 3.2374 |
| 3 | 34.32 | 6.1280 | 3.0640 |
| 4 | 34.75 | 6.1390 | 3.0695 |
