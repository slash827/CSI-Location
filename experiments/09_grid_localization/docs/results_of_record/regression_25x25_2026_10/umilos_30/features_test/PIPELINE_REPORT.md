# Multi-User 3D Regression Pipeline Report

**Generated:** 2026-10-15 23:21:16
**Data directory:** `sim_data_ne_bs_2026-10-15_09-40-11`
**BS position:** `[116.0, 116.0, 10.0]`
**Grid spacing:** `4.0m`

## Overall Regression Results

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |
|---|---|---|---|---|---|---|---|
| xgboost | BASE_A_H3_dp | 10.665 | 2.666 | 6.293 | 4.504 | 0.441 | 5.81 |
| rf | BASE_A_H3_dp | 12.254 | 3.063 | 7.500 | 4.940 | 0.505 | 89.03 |
| xgboost | BASE_A_H3_dp_HYBRID | 13.025 | 3.256 | 7.868 | 5.341 | 0.542 | 6.43 |
| rf | BASE_A_H3_dp_HYBRID | 12.473 | 3.118 | 7.461 | 5.122 | 0.490 | 91.63 |
| xgboost | BASE_A_H1_dp_HYBRID | 12.608 | 3.152 | 7.228 | 5.423 | 0.496 | 4.59 |
| rf | BASE_A_H1_dp_HYBRID | 12.299 | 3.075 | 7.160 | 5.178 | 0.474 | 47.94 |
| xgboost | BASE_A_H2_dp_HYBRID | 12.757 | 3.189 | 7.498 | 5.361 | 0.516 | 5.16 |
| rf | BASE_A_H2_dp_HYBRID | 12.433 | 3.108 | 7.406 | 5.122 | 0.487 | 65.2 |

## Per-User Results

| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |
|---|---|---|---|---|---|---|---|
| xgboost | BASE_A_H3_dp | U1 | 11.681 | 2.920 | 6.918 | 5.068 | 0.504 |
| xgboost | BASE_A_H3_dp | U2 | 5.476 | 1.369 | 4.510 | 1.390 | 0.300 |
| xgboost | BASE_A_H3_dp | U3 | 14.583 | 3.646 | 8.066 | 6.522 | 0.515 |
| xgboost | BASE_A_H3_dp | U4 | 12.129 | 3.032 | 7.123 | 5.352 | 0.549 |
| xgboost | BASE_A_H3_dp | U5 | 9.457 | 2.364 | 4.847 | 4.189 | 0.337 |
| rf | BASE_A_H3_dp | U1 | 15.032 | 3.758 | 9.380 | 6.077 | 0.649 |
| rf | BASE_A_H3_dp | U2 | 3.923 | 0.981 | 3.211 | 0.990 | 0.192 |
| rf | BASE_A_H3_dp | U3 | 14.970 | 3.743 | 8.115 | 6.708 | 0.483 |
| rf | BASE_A_H3_dp | U4 | 16.117 | 4.029 | 10.651 | 6.163 | 0.809 |
| rf | BASE_A_H3_dp | U5 | 11.228 | 2.807 | 6.144 | 4.763 | 0.391 |
| xgboost | BASE_A_H3_dp_HYBRID | U1 | 14.135 | 3.534 | 8.604 | 5.911 | 0.620 |
| xgboost | BASE_A_H3_dp_HYBRID | U2 | 6.680 | 1.670 | 5.765 | 1.452 | 0.368 |
| xgboost | BASE_A_H3_dp_HYBRID | U3 | 18.206 | 4.551 | 9.879 | 8.255 | 0.619 |
| xgboost | BASE_A_H3_dp_HYBRID | U4 | 14.902 | 3.725 | 9.368 | 6.141 | 0.710 |
| xgboost | BASE_A_H3_dp_HYBRID | U5 | 11.202 | 2.801 | 5.725 | 4.947 | 0.393 |
| rf | BASE_A_H3_dp_HYBRID | U1 | 16.549 | 4.137 | 10.186 | 6.771 | 0.685 |
| rf | BASE_A_H3_dp_HYBRID | U2 | 2.756 | 0.689 | 2.251 | 0.696 | 0.138 |
| rf | BASE_A_H3_dp_HYBRID | U3 | 14.267 | 3.567 | 7.578 | 6.476 | 0.440 |
| rf | BASE_A_H3_dp_HYBRID | U4 | 17.232 | 4.308 | 11.210 | 6.660 | 0.819 |
| rf | BASE_A_H3_dp_HYBRID | U5 | 11.565 | 2.891 | 6.082 | 5.007 | 0.369 |
| xgboost | BASE_A_H1_dp_HYBRID | U1 | 14.245 | 3.561 | 8.099 | 6.382 | 0.588 |
| xgboost | BASE_A_H1_dp_HYBRID | U2 | 5.761 | 1.440 | 4.938 | 1.262 | 0.319 |
| xgboost | BASE_A_H1_dp_HYBRID | U3 | 17.821 | 4.455 | 9.594 | 8.103 | 0.595 |
| xgboost | BASE_A_H1_dp_HYBRID | U4 | 14.601 | 3.650 | 8.561 | 6.452 | 0.647 |
| xgboost | BASE_A_H1_dp_HYBRID | U5 | 10.613 | 2.653 | 4.946 | 4.913 | 0.333 |
| rf | BASE_A_H1_dp_HYBRID | U1 | 16.561 | 4.140 | 9.760 | 7.055 | 0.664 |
| rf | BASE_A_H1_dp_HYBRID | U2 | 2.707 | 0.677 | 2.208 | 0.684 | 0.134 |
| rf | BASE_A_H1_dp_HYBRID | U3 | 13.834 | 3.458 | 7.347 | 6.290 | 0.427 |
| rf | BASE_A_H1_dp_HYBRID | U4 | 17.071 | 4.268 | 10.810 | 6.830 | 0.793 |
| rf | BASE_A_H1_dp_HYBRID | U5 | 11.321 | 2.830 | 5.676 | 5.033 | 0.351 |
| xgboost | BASE_A_H2_dp_HYBRID | U1 | 14.102 | 3.526 | 8.254 | 6.104 | 0.597 |
| xgboost | BASE_A_H2_dp_HYBRID | U2 | 6.149 | 1.537 | 5.287 | 1.356 | 0.341 |
| xgboost | BASE_A_H2_dp_HYBRID | U3 | 17.764 | 4.441 | 9.593 | 8.079 | 0.598 |
| xgboost | BASE_A_H2_dp_HYBRID | U4 | 14.787 | 3.697 | 9.008 | 6.294 | 0.684 |
| xgboost | BASE_A_H2_dp_HYBRID | U5 | 10.981 | 2.745 | 5.350 | 4.972 | 0.362 |
| rf | BASE_A_H2_dp_HYBRID | U1 | 16.552 | 4.138 | 10.101 | 6.815 | 0.680 |
| rf | BASE_A_H2_dp_HYBRID | U2 | 2.773 | 0.693 | 2.265 | 0.699 | 0.139 |
| rf | BASE_A_H2_dp_HYBRID | U3 | 14.097 | 3.524 | 7.487 | 6.406 | 0.434 |
| rf | BASE_A_H2_dp_HYBRID | U4 | 17.243 | 4.311 | 11.168 | 6.697 | 0.816 |
| rf | BASE_A_H2_dp_HYBRID | U5 | 11.503 | 2.876 | 6.009 | 4.996 | 0.366 |
