# Multi-User 3D Regression Pipeline Report

**Generated:** 2026-10-16 20:11:18
**Data directory:** `sim_data_ne_bs_2026-10-16_14-57-54`
**BS position:** `[116.0, 116.0, 10.0]`
**Grid spacing:** `4.0m`

## Overall Regression Results

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |
|---|---|---|---|---|---|---|---|
| xgboost | BASE_A_H3_dp | 10.849 | 2.712 | 8.072 | 3.370 | 0.572 | 6.99 |
| rf | BASE_A_H3_dp | 11.750 | 2.938 | 8.874 | 3.540 | 0.615 | 114.08 |
| xgboost | BASE_A_H3_dp_HYBRID | 12.664 | 3.166 | 9.577 | 3.814 | 0.672 | 8.67 |
| rf | BASE_A_H3_dp_HYBRID | 12.181 | 3.045 | 9.214 | 3.651 | 0.638 | 113.56 |
| xgboost | BASE_A_H1_dp_HYBRID | 12.589 | 3.147 | 9.483 | 3.769 | 0.668 | 6.67 |
| rf | BASE_A_H1_dp_HYBRID | 11.957 | 2.989 | 9.083 | 3.526 | 0.629 | 58.08 |
| xgboost | BASE_A_H2_dp_HYBRID | 12.451 | 3.113 | 9.408 | 3.737 | 0.665 | 6.59 |
| rf | BASE_A_H2_dp_HYBRID | 12.098 | 3.025 | 9.159 | 3.611 | 0.634 | 78.76 |

## Per-User Results

| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |
|---|---|---|---|---|---|---|---|
| xgboost | BASE_A_H3_dp | U1 | 10.354 | 2.588 | 8.847 | 2.356 | 0.593 |
| xgboost | BASE_A_H3_dp | U2 | 8.617 | 2.154 | 7.008 | 2.326 | 0.518 |
| xgboost | BASE_A_H3_dp | U3 | 17.681 | 4.420 | 10.266 | 7.539 | 0.700 |
| xgboost | BASE_A_H3_dp | U4 | 11.228 | 2.807 | 9.750 | 2.410 | 0.704 |
| xgboost | BASE_A_H3_dp | U5 | 6.366 | 1.591 | 4.488 | 2.217 | 0.346 |
| rf | BASE_A_H3_dp | U1 | 11.242 | 2.810 | 9.850 | 2.306 | 0.630 |
| rf | BASE_A_H3_dp | U2 | 8.281 | 2.070 | 6.946 | 2.053 | 0.503 |
| rf | BASE_A_H3_dp | U3 | 20.671 | 5.168 | 11.953 | 8.983 | 0.819 |
| rf | BASE_A_H3_dp | U4 | 12.361 | 3.090 | 11.030 | 2.337 | 0.767 |
| rf | BASE_A_H3_dp | U5 | 6.195 | 1.549 | 4.590 | 2.019 | 0.354 |
| xgboost | BASE_A_H3_dp_HYBRID | U1 | 11.821 | 2.955 | 10.390 | 2.447 | 0.689 |
| xgboost | BASE_A_H3_dp_HYBRID | U2 | 9.664 | 2.416 | 8.108 | 2.421 | 0.584 |
| xgboost | BASE_A_H3_dp_HYBRID | U3 | 21.942 | 5.486 | 12.717 | 9.395 | 0.863 |
| xgboost | BASE_A_H3_dp_HYBRID | U4 | 12.754 | 3.189 | 11.345 | 2.508 | 0.819 |
| xgboost | BASE_A_H3_dp_HYBRID | U5 | 7.139 | 1.785 | 5.325 | 2.303 | 0.405 |
| rf | BASE_A_H3_dp_HYBRID | U1 | 11.840 | 2.960 | 10.397 | 2.410 | 0.664 |
| rf | BASE_A_H3_dp_HYBRID | U2 | 8.180 | 2.045 | 6.853 | 2.034 | 0.496 |
| rf | BASE_A_H3_dp_HYBRID | U3 | 21.598 | 5.399 | 12.512 | 9.345 | 0.861 |
| rf | BASE_A_H3_dp_HYBRID | U4 | 13.055 | 3.264 | 11.664 | 2.445 | 0.818 |
| rf | BASE_A_H3_dp_HYBRID | U5 | 6.231 | 1.558 | 4.643 | 2.021 | 0.349 |
| xgboost | BASE_A_H1_dp_HYBRID | U1 | 12.086 | 3.022 | 10.527 | 2.536 | 0.701 |
| xgboost | BASE_A_H1_dp_HYBRID | U2 | 9.686 | 2.421 | 8.049 | 2.442 | 0.593 |
| xgboost | BASE_A_H1_dp_HYBRID | U3 | 21.096 | 5.274 | 12.257 | 8.943 | 0.829 |
| xgboost | BASE_A_H1_dp_HYBRID | U4 | 13.196 | 3.299 | 11.674 | 2.585 | 0.847 |
| xgboost | BASE_A_H1_dp_HYBRID | U5 | 6.879 | 1.720 | 4.907 | 2.341 | 0.370 |
| rf | BASE_A_H1_dp_HYBRID | U1 | 11.728 | 2.932 | 10.333 | 2.339 | 0.664 |
| rf | BASE_A_H1_dp_HYBRID | U2 | 8.027 | 2.007 | 6.728 | 1.972 | 0.487 |
| rf | BASE_A_H1_dp_HYBRID | U3 | 20.944 | 5.236 | 12.161 | 8.986 | 0.834 |
| rf | BASE_A_H1_dp_HYBRID | U4 | 13.007 | 3.252 | 11.666 | 2.373 | 0.822 |
| rf | BASE_A_H1_dp_HYBRID | U5 | 6.079 | 1.520 | 4.526 | 1.962 | 0.336 |
| xgboost | BASE_A_H2_dp_HYBRID | U1 | 11.862 | 2.966 | 10.408 | 2.444 | 0.697 |
| xgboost | BASE_A_H2_dp_HYBRID | U2 | 9.542 | 2.385 | 7.984 | 2.391 | 0.586 |
| xgboost | BASE_A_H2_dp_HYBRID | U3 | 21.167 | 5.292 | 12.264 | 9.043 | 0.834 |
| xgboost | BASE_A_H2_dp_HYBRID | U4 | 12.778 | 3.195 | 11.336 | 2.511 | 0.821 |
| xgboost | BASE_A_H2_dp_HYBRID | U5 | 6.908 | 1.727 | 5.049 | 2.294 | 0.388 |
| rf | BASE_A_H2_dp_HYBRID | U1 | 11.779 | 2.945 | 10.355 | 2.382 | 0.663 |
| rf | BASE_A_H2_dp_HYBRID | U2 | 8.111 | 2.028 | 6.797 | 2.010 | 0.493 |
| rf | BASE_A_H2_dp_HYBRID | U3 | 21.408 | 5.352 | 12.394 | 9.243 | 0.851 |
| rf | BASE_A_H2_dp_HYBRID | U4 | 13.004 | 3.251 | 11.633 | 2.418 | 0.816 |
| rf | BASE_A_H2_dp_HYBRID | U5 | 6.188 | 1.547 | 4.615 | 2.004 | 0.346 |
