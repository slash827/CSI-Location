# Multi-User 3D Regression Pipeline Report

**Generated:** 2026-10-16 14:45:50
**Data directory:** `sim_data_ne_bs_2026-10-16_01-32-21`
**BS position:** `[116.0, 116.0, 10.0]`
**Grid spacing:** `4.0m`

## Overall Regression Results

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |
|---|---|---|---|---|---|---|---|
| xgboost_custom | BASE | 33.190 | 8.298 | 19.692 | 14.150 | 1.423 | 4.99 |
| xgboost_custom | BASE_H3 | 25.486 | 6.371 | 15.760 | 10.659 | 1.128 | 5.48 |
| xgboost_custom | BASE_H3_dp | 21.597 | 5.399 | 13.123 | 9.067 | 0.922 | 5.73 |
| xgboost_custom | BASE_A | 17.754 | 4.439 | 13.889 | 4.905 | 0.992 | 5.66 |
| xgboost_custom | BASE_A_H3 | 15.364 | 3.841 | 12.065 | 4.400 | 0.855 | 6.72 |
| xgboost_custom | BASE_A_H3_dp | 14.507 | 3.627 | 11.189 | 4.410 | 0.806 | 6.68 |

## Per-User Results

| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |
|---|---|---|---|---|---|---|---|
| xgboost_custom | BASE | U1 | 32.435 | 8.109 | 20.538 | 13.290 | 1.507 |
| xgboost_custom | BASE | U2 | 36.422 | 9.106 | 23.532 | 15.474 | 1.692 |
| xgboost_custom | BASE | U3 | 32.572 | 8.143 | 16.171 | 14.370 | 1.109 |
| xgboost_custom | BASE | U4 | 31.276 | 7.819 | 16.651 | 13.854 | 1.275 |
| xgboost_custom | BASE | U5 | 33.247 | 8.312 | 21.569 | 13.764 | 1.530 |
| xgboost_custom | BASE_H3 | U1 | 23.205 | 5.801 | 15.353 | 8.985 | 1.129 |
| xgboost_custom | BASE_H3 | U2 | 29.341 | 7.335 | 19.986 | 11.583 | 1.395 |
| xgboost_custom | BASE_H3 | U3 | 25.189 | 6.297 | 14.014 | 10.897 | 0.991 |
| xgboost_custom | BASE_H3 | U4 | 21.629 | 5.407 | 11.760 | 10.021 | 0.814 |
| xgboost_custom | BASE_H3 | U5 | 28.064 | 7.016 | 17.686 | 11.807 | 1.313 |
| xgboost_custom | BASE_H3_dp | U1 | 20.851 | 5.213 | 13.098 | 8.455 | 0.974 |
| xgboost_custom | BASE_H3_dp | U2 | 23.892 | 5.973 | 15.975 | 9.286 | 1.041 |
| xgboost_custom | BASE_H3_dp | U3 | 20.782 | 5.196 | 12.085 | 8.979 | 0.788 |
| xgboost_custom | BASE_H3_dp | U4 | 19.869 | 4.967 | 11.102 | 8.840 | 0.740 |
| xgboost_custom | BASE_H3_dp | U5 | 22.589 | 5.647 | 13.357 | 9.776 | 1.069 |
| xgboost_custom | BASE_A | U1 | 16.335 | 4.084 | 14.024 | 3.804 | 1.046 |
| xgboost_custom | BASE_A | U2 | 18.630 | 4.657 | 16.773 | 3.411 | 1.130 |
| xgboost_custom | BASE_A | U3 | 24.844 | 6.211 | 13.995 | 10.747 | 0.923 |
| xgboost_custom | BASE_A | U4 | 12.133 | 3.033 | 10.154 | 2.886 | 0.747 |
| xgboost_custom | BASE_A | U5 | 16.827 | 4.207 | 14.501 | 3.679 | 1.115 |
| xgboost_custom | BASE_A_H3 | U1 | 14.178 | 3.545 | 12.400 | 3.144 | 0.883 |
| xgboost_custom | BASE_A_H3 | U2 | 15.329 | 3.832 | 13.755 | 3.032 | 0.953 |
| xgboost_custom | BASE_A_H3 | U3 | 21.588 | 5.397 | 12.458 | 9.418 | 0.817 |
| xgboost_custom | BASE_A_H3 | U4 | 11.220 | 2.805 | 9.212 | 3.086 | 0.693 |
| xgboost_custom | BASE_A_H3 | U5 | 14.508 | 3.627 | 12.498 | 3.319 | 0.929 |
| xgboost_custom | BASE_A_H3_dp | U1 | 13.058 | 3.264 | 11.264 | 3.105 | 0.816 |
| xgboost_custom | BASE_A_H3_dp | U2 | 13.954 | 3.489 | 12.119 | 3.340 | 0.873 |
| xgboost_custom | BASE_A_H3_dp | U3 | 21.317 | 5.329 | 12.242 | 9.336 | 0.805 |
| xgboost_custom | BASE_A_H3_dp | U4 | 11.258 | 2.814 | 9.253 | 3.154 | 0.690 |
| xgboost_custom | BASE_A_H3_dp | U5 | 12.948 | 3.237 | 11.066 | 3.114 | 0.847 |
