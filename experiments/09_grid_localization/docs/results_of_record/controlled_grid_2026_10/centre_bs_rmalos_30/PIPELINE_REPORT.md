# Pipeline Report — centre_bs_rmalos_30

**Generated:** 2026-10-13 12:35:26  
**Python:**    3.11.2  
**Platform:**  Windows 10  

---

## Reproduce This Run

```bash
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py --data-dir results/grid_localization/grid_15x15/sim_data_multi_user_2026-10-13_10-43-34/ --out-dir results/controlled_grid_2026_10/centre_bs_rmalos_30 --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8
```

---

## Run Configuration

| Parameter | Value |
|---|---|
| Data directory | `results/grid_localization/grid_15x15/sim_data_multi_user_2026-10-13_10-43-34/` |
| Output directory | `results\controlled_grid_2026_10\centre_bs_rmalos_30` |
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
| xgboost | BASE | 33.47 | 6.8426 | 3.4213 | 109.66 |
| xgboost | BASE_A | 68.31 | 1.7238 | 0.8619 | 106.28 |
| xgboost | BASE_A_H1 | 71.60 | 1.3928 | 0.6964 | 118.23 |
| xgboost | BASE_A_H2 | 71.44 | 1.3585 | 0.6793 | 133.83 |
| xgboost | BASE_A_H3 | 71.57 | 1.3462 | 0.6731 | 123.84 |
| xgboost | BASE_A_H3_delta | 70.62 | 1.4814 | 0.7407 | 116.9 |
| xgboost | BASE_A_H3_dp | 72.06 | 1.3225 | 0.6612 | 139.17 |
| xgboost | BASE_A_H3_dp_delta | 71.34 | 1.4382 | 0.7191 | 151.53 |
| xgboost | BASE_A_dp | 68.73 | 1.6849 | 0.8424 | 120.32 |
| xgboost | BASE_A_uid | 69.00 | 1.6595 | 0.8298 | 113.84 |
| xgboost | BASE_H1 | 50.08 | 4.0245 | 2.0123 | 105.04 |
| xgboost | BASE_H2 | 50.14 | 3.8987 | 1.9494 | 102.06 |
| xgboost | BASE_H3 | 50.62 | 3.7901 | 1.8950 | 115.97 |
| xgboost | BASE_H3_delta | 48.86 | 4.1511 | 2.0756 | 103.98 |
| xgboost | BASE_H3_dp | 52.76 | 3.1571 | 1.5786 | 107.77 |
| xgboost | BASE_H3_dp_delta | 51.53 | 3.4289 | 1.7145 | 135.43 |
| xgboost | BASE_H3_uid | 52.87 | 3.1576 | 1.5788 | 114.58 |
| xgboost | BASE_dp | 45.22 | 4.2064 | 2.1032 | 99.98 |
| xgboost | BASE_uid | 44.73 | 4.2424 | 2.1212 | 98.79 |
| xgboost | cross_user_BASE_A_H3 | 63.20 | 2.0068 | 1.0034 | 121.5 |
| xgboost | cross_user_BASE_A_dp | 59.66 | 2.4325 | 1.2163 | 91.87 |
| xgboost | cross_user_BASE_A_uid | 17.30 | 8.3564 | 4.1782 | 112.45 |
| xgboost | cross_user_BASE_H3 | 47.06 | 5.1796 | 2.5898 | 81.99 |
| xgboost | cross_user_BASE_H3_dp | 47.01 | 5.1306 | 2.5653 | 108.48 |
| xgboost | cross_user_BASE_H3_uid | 47.29 | 5.1552 | 2.5776 | 85.74 |
| rf | BASE | 43.89 | 5.3439 | 2.6720 | 16.71 |
| rf | BASE_A | 66.66 | 1.7786 | 0.8893 | 16.15 |
| rf | BASE_A_H1 | 69.47 | 1.4336 | 0.7168 | 16.71 |
| rf | BASE_A_H2 | 69.38 | 1.3869 | 0.6934 | 24.62 |
| rf | BASE_A_H3 | 68.98 | 1.3773 | 0.6886 | 30.96 |
| rf | BASE_A_H3_delta | 62.96 | 1.7975 | 0.8987 | 35.54 |
| rf | BASE_A_H3_dp | 69.09 | 1.3480 | 0.6740 | 27.48 |
| rf | BASE_A_H3_dp_delta | 66.58 | 1.5833 | 0.7917 | 29.93 |
| rf | BASE_A_dp | 70.44 | 1.5276 | 0.7638 | 10.87 |
| rf | BASE_A_uid | 68.67 | 1.6818 | 0.8409 | 14.0 |
| rf | BASE_H1 | 55.15 | 3.7740 | 1.8870 | 31.58 |
| rf | BASE_H2 | 56.82 | 3.3553 | 1.6777 | 32.31 |
| rf | BASE_H3 | 55.30 | 3.3241 | 1.6620 | 32.89 |
| rf | BASE_H3_delta | 41.39 | 5.2913 | 2.6456 | 33.13 |
| rf | BASE_H3_dp | 57.71 | 2.7164 | 1.3582 | 32.76 |
| rf | BASE_H3_dp_delta | 52.73 | 3.4297 | 1.7149 | 36.43 |
| rf | BASE_H3_uid | 58.52 | 2.7609 | 1.3804 | 42.6 |
| rf | BASE_dp | 53.53 | 3.6914 | 1.8457 | 15.97 |
| rf | BASE_uid | 55.98 | 3.4412 | 1.7206 | 14.76 |
| rf | cross_user_BASE_A_H3 | 62.33 | 1.8430 | 0.9215 | 23.16 |
| rf | cross_user_BASE_A_dp | 60.37 | 2.2787 | 1.1394 | 8.35 |
| rf | cross_user_BASE_A_uid | 60.20 | 2.3454 | 1.1727 | 9.97 |
| rf | cross_user_BASE_H3 | 50.18 | 4.8808 | 2.4404 | 25.82 |
| rf | cross_user_BASE_H3_dp | 50.65 | 4.6705 | 2.3353 | 24.97 |
| rf | cross_user_BASE_H3_uid | 50.81 | 5.0147 | 2.5074 | 30.38 |

### Learning Curve — XGBOOST (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 33.47 | 6.8426 | 3.4213 |
| 1 | 50.08 | 4.0245 | 2.0123 |
| 2 | 50.14 | 3.8987 | 1.9494 |
| 3 | 50.62 | 3.7901 | 1.8950 |
| 4 | 50.78 | 3.7502 | 1.8751 |

### Learning Curve — RF (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 43.89 | 5.3439 | 2.6720 |
| 1 | 55.15 | 3.7740 | 1.8870 |
| 2 | 56.82 | 3.3553 | 1.6777 |
| 3 | 55.30 | 3.3241 | 1.6620 |
| 4 | 56.70 | 3.2659 | 1.6329 |
