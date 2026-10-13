# Pipeline Report — ne_bs_mixed_30

**Generated:** 2026-10-13 21:03:27  
**Python:**    3.11.2  
**Platform:**  Windows 10  

---

## Reproduce This Run

```bash
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py --data-dir results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_11-23-43/ --out-dir results/controlled_grid_2026_10/ne_bs_mixed_30 --sinr-dependent-aoa --models xgboost rf --history 3 --n-jobs 8
```

---

## Run Configuration

| Parameter | Value |
|---|---|
| Data directory | `results/grid_localization/grid_15x15/sim_data_ne_bs_2026-10-13_11-23-43/` |
| Output directory | `results\controlled_grid_2026_10\ne_bs_mixed_30` |
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
| xgboost | BASE | 31.62 | 7.3661 | 3.6831 | 171.46 |
| xgboost | BASE_A | 49.59 | 4.6107 | 2.3053 | 176.35 |
| xgboost | BASE_A_H1 | 57.70 | 3.3547 | 1.6773 | 8887.78 |
| xgboost | BASE_A_H2 | 58.10 | 3.1943 | 1.5971 | 324.52 |
| xgboost | BASE_A_H3 | 58.36 | 3.0641 | 1.5321 | 191.49 |
| xgboost | BASE_A_H3_delta | 57.60 | 3.3789 | 1.6895 | 283.19 |
| xgboost | BASE_A_H3_dp | 61.84 | 2.6393 | 1.3197 | 209.17 |
| xgboost | BASE_A_H3_dp_delta | 61.25 | 2.8756 | 1.4378 | 350.34 |
| xgboost | BASE_A_dp | 55.37 | 3.8014 | 1.9007 | 184.77 |
| xgboost | BASE_A_uid | 59.11 | 3.2990 | 1.6495 | 3368.95 |
| xgboost | BASE_H1 | 55.77 | 3.8800 | 1.9400 | 372.96 |
| xgboost | BASE_H2 | 56.57 | 3.6505 | 1.8253 | 428.02 |
| xgboost | BASE_H3 | 57.34 | 3.5468 | 1.7734 | 555.57 |
| xgboost | BASE_H3_delta | 55.84 | 3.8505 | 1.9252 | 178.17 |
| xgboost | BASE_H3_dp | 61.99 | 2.8144 | 1.4072 | 161.71 |
| xgboost | BASE_H3_dp_delta | 61.18 | 2.9757 | 1.4879 | 224.28 |
| xgboost | BASE_H3_uid | 64.66 | 2.4779 | 1.2389 | 179.47 |
| xgboost | BASE_dp | 54.92 | 4.0831 | 2.0416 | 159.25 |
| xgboost | BASE_uid | 57.54 | 3.6266 | 1.8133 | 125.15 |
| xgboost | cross_user_BASE_A_H3 | 50.92 | 4.0775 | 2.0388 | 144.42 |
| xgboost | cross_user_BASE_A_dp | 45.49 | 5.2084 | 2.6042 | 125.34 |
| xgboost | cross_user_BASE_A_uid | 49.61 | 4.6073 | 2.3037 | 118.76 |
| xgboost | cross_user_BASE_H3 | 50.01 | 4.5059 | 2.2530 | 92.4 |
| xgboost | cross_user_BASE_H3_dp | 52.12 | 4.2608 | 2.1304 | 118.62 |
| xgboost | cross_user_BASE_H3_uid | 54.56 | 3.9709 | 1.9854 | 114.74 |
| rf | BASE | 52.34 | 4.9270 | 2.4635 | 16.8 |
| rf | BASE_A | 54.64 | 4.2450 | 2.1225 | 18.26 |
| rf | BASE_A_H1 | 60.29 | 3.1157 | 1.5578 | 18.98 |
| rf | BASE_A_H2 | 62.94 | 2.7121 | 1.3560 | 24.39 |
| rf | BASE_A_H3 | 63.35 | 2.6205 | 1.3103 | 32.53 |
| rf | BASE_A_H3_delta | 53.09 | 3.7719 | 1.8859 | 34.85 |
| rf | BASE_A_H3_dp | 64.96 | 2.2923 | 1.1462 | 27.57 |
| rf | BASE_A_H3_dp_delta | 59.90 | 2.9614 | 1.4807 | 28.52 |
| rf | BASE_A_dp | 57.09 | 3.7923 | 1.8961 | 11.42 |
| rf | BASE_A_uid | 63.48 | 3.0231 | 1.5116 | 14.73 |
| rf | BASE_H1 | 63.72 | 3.2101 | 1.6050 | 31.32 |
| rf | BASE_H2 | 65.35 | 2.8331 | 1.4165 | 31.52 |
| rf | BASE_H3 | 63.77 | 2.7849 | 1.3925 | 31.47 |
| rf | BASE_H3_delta | 54.02 | 3.8220 | 1.9110 | 32.96 |
| rf | BASE_H3_dp | 67.80 | 2.2622 | 1.1311 | 34.6 |
| rf | BASE_H3_dp_delta | 64.75 | 2.6001 | 1.3001 | 34.1 |
| rf | BASE_H3_uid | 70.61 | 1.9733 | 0.9866 | 40.98 |
| rf | BASE_dp | 62.02 | 3.4852 | 1.7426 | 15.6 |
| rf | BASE_uid | 65.46 | 2.9496 | 1.4748 | 13.0 |
| rf | cross_user_BASE_A_H3 | 53.46 | 3.8757 | 1.9379 | 25.75 |
| rf | cross_user_BASE_A_dp | 46.41 | 5.0863 | 2.5431 | 10.42 |
| rf | cross_user_BASE_A_uid | 52.18 | 4.4901 | 2.2451 | 12.27 |
| rf | cross_user_BASE_H3 | 53.30 | 4.1445 | 2.0722 | 26.87 |
| rf | cross_user_BASE_H3_dp | 55.09 | 3.9879 | 1.9940 | 26.78 |
| rf | cross_user_BASE_H3_uid | 57.94 | 3.6931 | 1.8465 | 32.82 |

### Learning Curve — XGBOOST (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 31.62 | 7.3661 | 3.6831 |
| 1 | 55.77 | 3.8800 | 1.9400 |
| 2 | 56.57 | 3.6505 | 1.8253 |
| 3 | 57.34 | 3.5468 | 1.7734 |
| 4 | 57.60 | 3.5084 | 1.7542 |

### Learning Curve — RF (h = 0 … 4)

| h | Accuracy (%) | MAE (m) | MPE (pts) |
|---|---|---|---|
| 0 | 52.34 | 4.9270 | 2.4635 |
| 1 | 63.72 | 3.2101 | 1.6050 |
| 2 | 65.35 | 2.8331 | 1.4165 |
| 3 | 63.77 | 2.7849 | 1.3925 |
| 4 | 64.55 | 2.8054 | 1.4027 |
