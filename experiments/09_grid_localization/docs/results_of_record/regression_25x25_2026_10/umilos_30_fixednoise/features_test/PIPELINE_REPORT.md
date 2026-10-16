# Multi-User 3D Regression Pipeline Report

**Generated:** 2026-10-16 01:32:15
**Data directory:** `sim_data_ne_bs_2026-10-15_09-40-11`
**BS position:** `[116.0, 116.0, 10.0]`
**Grid spacing:** `4.0m`

## Overall Regression Results

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |
|---|---|---|---|---|---|---|---|
| xgboost | BASE_A_H3_dp | 7.988 | 1.997 | 5.471 | 2.924 | 0.389 | 18.61 |
| rf | BASE_A_H3_dp | 8.847 | 2.212 | 6.218 | 3.085 | 0.453 | 131.92 |
| xgboost | BASE_A_H3_dp_HYBRID | 9.630 | 2.408 | 6.775 | 3.362 | 0.476 | 11.11 |
| rf | BASE_A_H3_dp_HYBRID | 8.389 | 2.097 | 5.914 | 2.905 | 0.423 | 147.61 |
| xgboost | BASE_A_H1_dp_HYBRID | 8.972 | 2.243 | 6.085 | 3.263 | 0.421 | 11.11 |
| rf | BASE_A_H1_dp_HYBRID | 8.143 | 2.036 | 5.728 | 2.832 | 0.408 | 62.18 |
| xgboost | BASE_A_H2_dp_HYBRID | 9.270 | 2.318 | 6.426 | 3.289 | 0.450 | 7.13 |
| rf | BASE_A_H2_dp_HYBRID | 8.306 | 2.076 | 5.859 | 2.877 | 0.419 | 86.93 |

## Per-User Results

| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |
|---|---|---|---|---|---|---|---|
| xgboost | BASE_A_H3_dp | U1 | 6.782 | 1.696 | 5.196 | 2.133 | 0.391 |
| xgboost | BASE_A_H3_dp | U2 | 6.989 | 1.747 | 5.352 | 2.155 | 0.362 |
| xgboost | BASE_A_H3_dp | U3 | 13.407 | 3.352 | 7.501 | 5.972 | 0.478 |
| xgboost | BASE_A_H3_dp | U4 | 7.095 | 1.774 | 5.423 | 2.266 | 0.420 |
| xgboost | BASE_A_H3_dp | U5 | 5.666 | 1.417 | 3.880 | 2.093 | 0.292 |
| rf | BASE_A_H3_dp | U1 | 7.342 | 1.835 | 5.920 | 2.110 | 0.464 |
| rf | BASE_A_H3_dp | U2 | 7.676 | 1.919 | 6.109 | 2.110 | 0.402 |
| rf | BASE_A_H3_dp | U3 | 15.827 | 3.957 | 8.513 | 7.177 | 0.516 |
| rf | BASE_A_H3_dp | U4 | 7.591 | 1.898 | 6.255 | 2.065 | 0.510 |
| rf | BASE_A_H3_dp | U5 | 5.800 | 1.450 | 4.293 | 1.963 | 0.371 |
| xgboost | BASE_A_H3_dp_HYBRID | U1 | 7.841 | 1.960 | 6.313 | 2.216 | 0.474 |
| xgboost | BASE_A_H3_dp_HYBRID | U2 | 8.207 | 2.052 | 6.651 | 2.231 | 0.445 |
| xgboost | BASE_A_H3_dp_HYBRID | U3 | 17.455 | 4.364 | 9.599 | 7.858 | 0.602 |
| xgboost | BASE_A_H3_dp_HYBRID | U4 | 8.367 | 2.092 | 6.806 | 2.337 | 0.519 |
| xgboost | BASE_A_H3_dp_HYBRID | U5 | 6.280 | 1.570 | 4.505 | 2.168 | 0.342 |
| rf | BASE_A_H3_dp_HYBRID | U1 | 7.271 | 1.818 | 5.862 | 2.068 | 0.454 |
| rf | BASE_A_H3_dp_HYBRID | U2 | 7.274 | 1.819 | 5.834 | 1.955 | 0.376 |
| rf | BASE_A_H3_dp_HYBRID | U3 | 14.466 | 3.617 | 7.671 | 6.639 | 0.454 |
| rf | BASE_A_H3_dp_HYBRID | U4 | 7.501 | 1.875 | 6.214 | 2.022 | 0.503 |
| rf | BASE_A_H3_dp_HYBRID | U5 | 5.433 | 1.358 | 3.990 | 1.842 | 0.331 |
| xgboost | BASE_A_H1_dp_HYBRID | U1 | 7.506 | 1.876 | 5.868 | 2.214 | 0.434 |
| xgboost | BASE_A_H1_dp_HYBRID | U2 | 7.268 | 1.817 | 5.632 | 2.144 | 0.370 |
| xgboost | BASE_A_H1_dp_HYBRID | U3 | 16.594 | 4.149 | 8.955 | 7.516 | 0.556 |
| xgboost | BASE_A_H1_dp_HYBRID | U4 | 7.840 | 1.960 | 6.200 | 2.324 | 0.470 |
| xgboost | BASE_A_H1_dp_HYBRID | U5 | 5.650 | 1.413 | 3.769 | 2.116 | 0.275 |
| rf | BASE_A_H1_dp_HYBRID | U1 | 7.089 | 1.772 | 5.720 | 2.013 | 0.440 |
| rf | BASE_A_H1_dp_HYBRID | U2 | 6.967 | 1.742 | 5.570 | 1.873 | 0.350 |
| rf | BASE_A_H1_dp_HYBRID | U3 | 14.124 | 3.531 | 7.501 | 6.498 | 0.445 |
| rf | BASE_A_H1_dp_HYBRID | U4 | 7.256 | 1.814 | 5.990 | 1.974 | 0.489 |
| rf | BASE_A_H1_dp_HYBRID | U5 | 5.277 | 1.319 | 3.858 | 1.803 | 0.314 |
| xgboost | BASE_A_H2_dp_HYBRID | U1 | 7.782 | 1.946 | 6.184 | 2.236 | 0.461 |
| xgboost | BASE_A_H2_dp_HYBRID | U2 | 7.532 | 1.883 | 5.983 | 2.135 | 0.400 |
| xgboost | BASE_A_H2_dp_HYBRID | U3 | 16.845 | 4.211 | 9.175 | 7.613 | 0.572 |
| xgboost | BASE_A_H2_dp_HYBRID | U4 | 8.135 | 2.034 | 6.524 | 2.337 | 0.495 |
| xgboost | BASE_A_H2_dp_HYBRID | U5 | 6.057 | 1.514 | 4.264 | 2.122 | 0.320 |
| rf | BASE_A_H2_dp_HYBRID | U1 | 7.223 | 1.806 | 5.825 | 2.053 | 0.450 |
| rf | BASE_A_H2_dp_HYBRID | U2 | 7.198 | 1.800 | 5.770 | 1.937 | 0.371 |
| rf | BASE_A_H2_dp_HYBRID | U3 | 14.308 | 3.577 | 7.604 | 6.567 | 0.450 |
| rf | BASE_A_H2_dp_HYBRID | U4 | 7.418 | 1.855 | 6.142 | 2.004 | 0.498 |
| rf | BASE_A_H2_dp_HYBRID | U5 | 5.383 | 1.346 | 3.955 | 1.824 | 0.327 |
