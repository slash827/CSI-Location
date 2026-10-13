# Pipeline Report — centre_bs_mixed_30

**Generated:** 2026-10-13 21:02:36  
**Python:**    3.11.2  
**Platform:**  Windows 10  

---

## Reproduce This Run

```bash
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py --data-dir results/grid_localization/grid_15x15/sim_data_multi_user_2026-10-13_11-23-48/ --out-dir results/controlled_grid_2026_10/centre_bs_mixed_30 --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8
```

---

## Run Configuration

| Parameter | Value |
|---|---|
| Data directory | `results/grid_localization/grid_15x15/sim_data_multi_user_2026-10-13_11-23-48/` |
| Output directory | `results\controlled_grid_2026_10\centre_bs_mixed_30` |
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
| xgboost | BASE | 31.72 | 8.0604 | 4.0302 | 167.47 |
| xgboost | BASE_A | 75.51 | 1.4335 | 0.7168 | 172.73 |
| xgboost | BASE_A_H1 | 78.45 | 1.0515 | 0.5258 | 8867.42 |
| xgboost | BASE_A_H2 | 78.30 | 1.0101 | 0.5050 | 516.29 |
| xgboost | BASE_A_H3 | 78.59 | 0.9997 | 0.4999 | 181.16 |
| xgboost | BASE_A_H3_delta | 77.72 | 1.1028 | 0.5514 | 259.52 |
| xgboost | BASE_A_H3_dp | 79.54 | 0.9301 | 0.4651 | 203.49 |
| xgboost | BASE_A_H3_dp_delta | 78.97 | 1.0294 | 0.5147 | 378.4 |
| xgboost | BASE_A_dp | 77.34 | 1.3270 | 0.6635 | 176.07 |
| xgboost | BASE_A_uid | 78.12 | 1.3060 | 0.6530 | 3206.66 |
| xgboost | BASE_H1 | 57.98 | 4.0484 | 2.0242 | 366.76 |
| xgboost | BASE_H2 | 58.91 | 3.7786 | 1.8893 | 432.01 |
| xgboost | BASE_H3 | 59.11 | 3.7654 | 1.8827 | 559.45 |
| xgboost | BASE_H3_delta | 58.24 | 3.9471 | 1.9736 | 179.5 |
| xgboost | BASE_H3_dp | 66.67 | 2.4639 | 1.2320 | 176.66 |
| xgboost | BASE_H3_dp_delta | 65.79 | 2.6337 | 1.3168 | 231.11 |
| xgboost | BASE_H3_uid | 68.88 | 2.1530 | 1.0765 | 167.39 |
| xgboost | BASE_dp | 59.21 | 3.8419 | 1.9209 | 158.31 |
| xgboost | BASE_uid | 61.85 | 3.3351 | 1.6675 | 124.66 |
| xgboost | cross_user_BASE_A_H3 | 68.52 | 1.5410 | 0.7705 | 153.54 |
| xgboost | cross_user_BASE_A_dp | 66.28 | 2.0094 | 1.0047 | 123.86 |
| xgboost | cross_user_BASE_A_uid | 66.73 | 2.1484 | 1.0742 | 111.0 |
| xgboost | cross_user_BASE_H3 | 52.12 | 4.8677 | 2.4339 | 91.38 |
| xgboost | cross_user_BASE_H3_dp | 55.50 | 4.2109 | 2.1055 | 115.44 |
| xgboost | cross_user_BASE_H3_uid | 57.81 | 3.8900 | 1.9450 | 107.65 |
| rf | BASE | 53.50 | 5.2149 | 2.6074 | 15.9 |
| rf | BASE_A | 77.06 | 1.2512 | 0.6256 | 16.34 |
| rf | BASE_A_H1 | 78.56 | 0.9805 | 0.4902 | 17.02 |
| rf | BASE_A_H2 | 77.44 | 1.0107 | 0.5053 | 24.09 |
| rf | BASE_A_H3 | 76.39 | 1.0369 | 0.5184 | 33.59 |
| rf | BASE_A_H3_delta | 75.20 | 1.1946 | 0.5973 | 33.17 |
| rf | BASE_A_H3_dp | 77.07 | 1.0083 | 0.5042 | 26.73 |
| rf | BASE_A_H3_dp_delta | 76.87 | 1.1086 | 0.5543 | 28.42 |
| rf | BASE_A_dp | 79.62 | 1.0922 | 0.5461 | 10.91 |
| rf | BASE_A_uid | 80.31 | 1.0981 | 0.5491 | 12.9 |
| rf | BASE_H1 | 65.34 | 3.3091 | 1.6546 | 31.4 |
| rf | BASE_H2 | 67.61 | 2.8108 | 1.4054 | 31.15 |
| rf | BASE_H3 | 66.52 | 2.7567 | 1.3784 | 30.69 |
| rf | BASE_H3_delta | 58.97 | 3.6675 | 1.8337 | 31.83 |
| rf | BASE_H3_dp | 71.83 | 1.9221 | 0.9611 | 33.8 |
| rf | BASE_H3_dp_delta | 67.32 | 2.4283 | 1.2142 | 34.02 |
| rf | BASE_H3_uid | 74.18 | 1.6737 | 0.8369 | 41.79 |
| rf | BASE_dp | 65.67 | 3.2083 | 1.6041 | 14.57 |
| rf | BASE_uid | 68.72 | 2.6921 | 1.3460 | 13.84 |
| rf | cross_user_BASE_A_H3 | 69.16 | 1.4059 | 0.7030 | 25.34 |
| rf | cross_user_BASE_A_dp | 67.02 | 1.8946 | 0.9473 | 8.98 |
| rf | cross_user_BASE_A_uid | 69.10 | 1.8234 | 0.9117 | 11.13 |
| rf | cross_user_BASE_H3 | 55.65 | 4.3616 | 2.1808 | 23.9 |
| rf | cross_user_BASE_H3_dp | 57.96 | 3.9132 | 1.9566 | 26.46 |
| rf | cross_user_BASE_H3_uid | 60.42 | 3.6637 | 1.8318 | 34.39 |

### Learning Curve — XGBOOST (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 31.72 | 8.0604 | 4.0302 |
| 1 | 57.98 | 4.0484 | 2.0242 |
| 2 | 58.91 | 3.7786 | 1.8893 |
| 3 | 59.11 | 3.7654 | 1.8827 |
| 4 | 59.63 | 3.6585 | 1.8292 |

### Learning Curve — RF (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 53.50 | 5.2149 | 2.6074 |
| 1 | 65.34 | 3.3091 | 1.6546 |
| 2 | 67.61 | 2.8108 | 1.4054 |
| 3 | 66.52 | 2.7567 | 1.3784 |
| 4 | 66.88 | 2.7932 | 1.3966 |
