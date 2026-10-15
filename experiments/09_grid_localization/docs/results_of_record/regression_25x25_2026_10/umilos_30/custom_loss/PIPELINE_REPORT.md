# Multi-User 3D Regression Pipeline Report

**Generated:** 2026-10-15 23:12:32
**Data directory:** `sim_data_ne_bs_2026-10-15_09-40-11`
**BS position:** `[116.0, 116.0, 10.0]`
**Grid spacing:** `4.0m`

## Overall Regression Results

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |
|---|---|---|---|---|---|---|---|
| xgboost_custom | BASE | 29.320 | 7.330 | 15.969 | 13.557 | 1.165 | 4.02 |
| xgboost_custom | BASE_H3 | 16.769 | 4.192 | 9.040 | 7.751 | 0.619 | 4.5 |
| xgboost_custom | BASE_H3_dp | 14.585 | 3.646 | 8.022 | 6.637 | 0.535 | 4.6 |
| xgboost_custom | BASE_A | 15.235 | 3.809 | 8.746 | 6.504 | 0.590 | 4.65 |
| xgboost_custom | BASE_A_H3 | 13.294 | 3.324 | 8.247 | 5.355 | 0.575 | 5.61 |
| xgboost_custom | BASE_A_H3_dp | 12.850 | 3.212 | 7.860 | 5.235 | 0.539 | 5.58 |

## Per-User Results

| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |
|---|---|---|---|---|---|---|---|
| xgboost_custom | BASE | U1 | 30.514 | 7.628 | 17.456 | 14.421 | 1.309 |
| xgboost_custom | BASE | U2 | 26.698 | 6.674 | 16.638 | 11.136 | 1.112 |
| xgboost_custom | BASE | U3 | 31.588 | 7.897 | 15.703 | 14.830 | 1.074 |
| xgboost_custom | BASE | U4 | 29.820 | 7.455 | 15.044 | 14.107 | 1.116 |
| xgboost_custom | BASE | U5 | 27.981 | 6.995 | 15.005 | 13.294 | 1.215 |
| xgboost_custom | BASE_H3 | U1 | 16.493 | 4.123 | 9.136 | 7.938 | 0.699 |
| xgboost_custom | BASE_H3 | U2 | 13.978 | 3.494 | 8.514 | 5.653 | 0.533 |
| xgboost_custom | BASE_H3 | U3 | 22.057 | 5.514 | 11.732 | 10.214 | 0.755 |
| xgboost_custom | BASE_H3 | U4 | 17.137 | 4.284 | 8.442 | 8.259 | 0.635 |
| xgboost_custom | BASE_H3 | U5 | 14.182 | 3.546 | 7.375 | 6.692 | 0.473 |
| xgboost_custom | BASE_H3_dp | U1 | 15.611 | 3.903 | 8.374 | 7.597 | 0.596 |
| xgboost_custom | BASE_H3_dp | U2 | 13.340 | 3.335 | 8.025 | 5.530 | 0.492 |
| xgboost_custom | BASE_H3_dp | U3 | 17.573 | 4.393 | 10.074 | 7.636 | 0.626 |
| xgboost_custom | BASE_H3_dp | U4 | 14.447 | 3.612 | 8.034 | 6.595 | 0.581 |
| xgboost_custom | BASE_H3_dp | U5 | 11.954 | 2.988 | 5.602 | 5.829 | 0.378 |
| xgboost_custom | BASE_A | U1 | 16.991 | 4.248 | 9.737 | 7.588 | 0.731 |
| xgboost_custom | BASE_A | U2 | 7.249 | 1.812 | 6.223 | 1.615 | 0.404 |
| xgboost_custom | BASE_A | U3 | 20.162 | 5.040 | 10.944 | 9.050 | 0.677 |
| xgboost_custom | BASE_A | U4 | 18.281 | 4.570 | 9.915 | 8.258 | 0.732 |
| xgboost_custom | BASE_A | U5 | 13.495 | 3.374 | 6.912 | 6.011 | 0.407 |
| xgboost_custom | BASE_A_H3 | U1 | 14.162 | 3.541 | 8.812 | 5.832 | 0.677 |
| xgboost_custom | BASE_A_H3 | U2 | 6.847 | 1.712 | 5.781 | 1.639 | 0.380 |
| xgboost_custom | BASE_A_H3 | U3 | 17.897 | 4.474 | 10.322 | 7.815 | 0.652 |
| xgboost_custom | BASE_A_H3 | U4 | 15.083 | 3.771 | 9.065 | 6.385 | 0.694 |
| xgboost_custom | BASE_A_H3 | U5 | 12.482 | 3.120 | 7.254 | 5.103 | 0.473 |
| xgboost_custom | BASE_A_H3_dp | U1 | 13.895 | 3.474 | 8.618 | 5.716 | 0.624 |
| xgboost_custom | BASE_A_H3_dp | U2 | 6.110 | 1.527 | 5.021 | 1.573 | 0.325 |
| xgboost_custom | BASE_A_H3_dp | U3 | 17.951 | 4.488 | 10.196 | 7.909 | 0.648 |
| xgboost_custom | BASE_A_H3_dp | U4 | 14.660 | 3.665 | 9.136 | 6.041 | 0.680 |
| xgboost_custom | BASE_A_H3_dp | U5 | 11.635 | 2.909 | 6.329 | 4.937 | 0.420 |
