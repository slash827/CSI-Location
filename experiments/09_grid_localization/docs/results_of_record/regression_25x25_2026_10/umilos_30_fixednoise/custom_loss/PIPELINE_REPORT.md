# Multi-User 3D Regression Pipeline Report

**Generated:** 2026-10-16 01:18:32
**Data directory:** `sim_data_ne_bs_2026-10-15_09-40-11`
**BS position:** `[116.0, 116.0, 10.0]`
**Grid spacing:** `4.0m`

## Overall Regression Results

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |
|---|---|---|---|---|---|---|---|
| xgboost_custom | BASE | 29.322 | 7.330 | 15.970 | 13.560 | 1.165 | 5.6 |
| xgboost_custom | BASE_H3 | 16.731 | 4.183 | 9.009 | 7.756 | 0.621 | 6.21 |
| xgboost_custom | BASE_H3_dp | 14.679 | 3.670 | 8.079 | 6.684 | 0.539 | 6.24 |
| xgboost_custom | BASE_A | 59.974 | 14.993 | 56.474 | 4.537 | 0.802 | 7.56 |
| xgboost_custom | BASE_A_H3 | 11.292 | 2.823 | 8.245 | 3.791 | 0.593 | 11.25 |
| xgboost_custom | BASE_A_H3_dp | 11.996 | 2.999 | 8.556 | 4.325 | 0.607 | 10.98 |

## Per-User Results

| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |
|---|---|---|---|---|---|---|---|
| xgboost_custom | BASE | U1 | 30.493 | 7.623 | 17.442 | 14.421 | 1.308 |
| xgboost_custom | BASE | U2 | 26.692 | 6.673 | 16.607 | 11.154 | 1.107 |
| xgboost_custom | BASE | U3 | 31.586 | 7.896 | 15.701 | 14.835 | 1.073 |
| xgboost_custom | BASE | U4 | 29.804 | 7.451 | 15.030 | 14.098 | 1.116 |
| xgboost_custom | BASE | U5 | 28.034 | 7.009 | 15.070 | 13.295 | 1.221 |
| xgboost_custom | BASE_H3 | U1 | 16.744 | 4.186 | 9.289 | 8.028 | 0.708 |
| xgboost_custom | BASE_H3 | U2 | 14.063 | 3.516 | 8.454 | 5.727 | 0.528 |
| xgboost_custom | BASE_H3 | U3 | 21.881 | 5.470 | 11.688 | 10.147 | 0.759 |
| xgboost_custom | BASE_H3 | U4 | 16.898 | 4.224 | 8.284 | 8.227 | 0.633 |
| xgboost_custom | BASE_H3 | U5 | 14.068 | 3.517 | 7.332 | 6.650 | 0.477 |
| xgboost_custom | BASE_H3_dp | U1 | 15.952 | 3.988 | 8.567 | 7.765 | 0.609 |
| xgboost_custom | BASE_H3_dp | U2 | 12.967 | 3.242 | 7.825 | 5.392 | 0.485 |
| xgboost_custom | BASE_H3_dp | U3 | 17.466 | 4.367 | 10.072 | 7.571 | 0.628 |
| xgboost_custom | BASE_H3_dp | U4 | 14.791 | 3.698 | 8.309 | 6.702 | 0.596 |
| xgboost_custom | BASE_H3_dp | U5 | 12.218 | 3.054 | 5.620 | 5.988 | 0.378 |
| xgboost_custom | BASE_A | U1 | 71.983 | 17.996 | 69.905 | 3.465 | 0.896 |
| xgboost_custom | BASE_A | U2 | 78.811 | 19.703 | 76.828 | 3.540 | 0.915 |
| xgboost_custom | BASE_A | U3 | 19.737 | 4.934 | 10.659 | 8.878 | 0.645 |
| xgboost_custom | BASE_A | U4 | 56.767 | 14.192 | 54.612 | 3.461 | 0.808 |
| xgboost_custom | BASE_A | U5 | 72.573 | 18.143 | 70.364 | 3.340 | 0.748 |
| xgboost_custom | BASE_A_H3 | U1 | 9.715 | 2.429 | 7.850 | 2.829 | 0.619 |
| xgboost_custom | BASE_A_H3 | U2 | 10.087 | 2.522 | 8.312 | 2.718 | 0.577 |
| xgboost_custom | BASE_A_H3 | U3 | 17.814 | 4.454 | 10.058 | 7.839 | 0.629 |
| xgboost_custom | BASE_A_H3 | U4 | 10.182 | 2.545 | 8.263 | 2.923 | 0.635 |
| xgboost_custom | BASE_A_H3 | U5 | 8.662 | 2.166 | 6.745 | 2.647 | 0.502 |
| xgboost_custom | BASE_A_H3_dp | U1 | 10.800 | 2.700 | 8.343 | 3.603 | 0.624 |
| xgboost_custom | BASE_A_H3_dp | U2 | 11.333 | 2.833 | 8.943 | 3.571 | 0.615 |
| xgboost_custom | BASE_A_H3_dp | U3 | 17.727 | 4.432 | 9.837 | 7.864 | 0.618 |
| xgboost_custom | BASE_A_H3_dp | U4 | 11.430 | 2.857 | 9.159 | 3.556 | 0.673 |
| xgboost_custom | BASE_A_H3_dp | U5 | 8.691 | 2.173 | 6.497 | 3.029 | 0.505 |
