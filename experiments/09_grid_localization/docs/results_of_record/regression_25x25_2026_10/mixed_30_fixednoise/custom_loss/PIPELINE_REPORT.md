# Multi-User 3D Regression Pipeline Report

**Generated:** 2026-10-16 20:00:15
**Data directory:** `sim_data_ne_bs_2026-10-16_14-57-54`
**BS position:** `[116.0, 116.0, 10.0]`
**Grid spacing:** `4.0m`

## Overall Regression Results

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |
|---|---|---|---|---|---|---|---|
| xgboost_custom | BASE | 29.775 | 7.444 | 15.507 | 13.979 | 1.158 | 3.73 |
| xgboost_custom | BASE_H3 | 21.715 | 5.429 | 11.509 | 10.127 | 0.829 | 4.84 |
| xgboost_custom | BASE_H3_dp | 19.634 | 4.908 | 10.671 | 9.042 | 0.756 | 5.68 |
| xgboost_custom | BASE_A | 15.208 | 3.802 | 11.518 | 4.522 | 0.819 | 4.78 |
| xgboost_custom | BASE_A_H3 | 13.896 | 3.474 | 10.700 | 4.113 | 0.743 | 6.13 |
| xgboost_custom | BASE_A_H3_dp | 15.487 | 3.872 | 11.435 | 5.039 | 0.765 | 5.96 |

## Per-User Results

| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |
|---|---|---|---|---|---|---|---|
| xgboost_custom | BASE | U1 | 30.998 | 7.750 | 17.004 | 13.807 | 1.219 |
| xgboost_custom | BASE | U2 | 28.330 | 7.083 | 13.472 | 14.158 | 1.048 |
| xgboost_custom | BASE | U3 | 32.242 | 8.060 | 17.866 | 14.445 | 1.278 |
| xgboost_custom | BASE | U4 | 32.084 | 8.021 | 19.068 | 14.210 | 1.466 |
| xgboost_custom | BASE | U5 | 25.221 | 6.305 | 10.126 | 13.274 | 0.779 |
| xgboost_custom | BASE_H3 | U1 | 23.015 | 5.754 | 13.112 | 10.159 | 0.895 |
| xgboost_custom | BASE_H3 | U2 | 20.389 | 5.097 | 9.972 | 10.281 | 0.772 |
| xgboost_custom | BASE_H3 | U3 | 23.569 | 5.892 | 12.915 | 10.401 | 0.892 |
| xgboost_custom | BASE_H3 | U4 | 24.724 | 6.181 | 14.420 | 11.266 | 1.076 |
| xgboost_custom | BASE_H3 | U5 | 16.880 | 4.220 | 7.127 | 8.526 | 0.508 |
| xgboost_custom | BASE_H3_dp | U1 | 21.700 | 5.425 | 12.025 | 9.711 | 0.810 |
| xgboost_custom | BASE_H3_dp | U2 | 17.961 | 4.490 | 9.491 | 8.858 | 0.702 |
| xgboost_custom | BASE_H3_dp | U3 | 20.096 | 5.024 | 11.918 | 8.454 | 0.802 |
| xgboost_custom | BASE_H3_dp | U4 | 23.847 | 5.962 | 13.694 | 10.775 | 1.007 |
| xgboost_custom | BASE_H3_dp | U5 | 14.564 | 3.641 | 6.229 | 7.413 | 0.458 |
| xgboost_custom | BASE_A | U1 | 14.742 | 3.686 | 12.667 | 3.244 | 0.845 |
| xgboost_custom | BASE_A | U2 | 13.067 | 3.267 | 10.626 | 3.487 | 0.806 |
| xgboost_custom | BASE_A | U3 | 23.884 | 5.971 | 14.188 | 9.894 | 0.970 |
| xgboost_custom | BASE_A | U4 | 15.779 | 3.945 | 13.871 | 3.167 | 1.009 |
| xgboost_custom | BASE_A | U5 | 8.567 | 2.142 | 6.237 | 2.816 | 0.465 |
| xgboost_custom | BASE_A_H3 | U1 | 13.474 | 3.369 | 11.677 | 3.050 | 0.776 |
| xgboost_custom | BASE_A_H3 | U2 | 12.130 | 3.033 | 10.289 | 2.963 | 0.733 |
| xgboost_custom | BASE_A_H3 | U3 | 20.635 | 5.159 | 12.207 | 8.650 | 0.825 |
| xgboost_custom | BASE_A_H3 | U4 | 14.300 | 3.575 | 12.480 | 3.123 | 0.876 |
| xgboost_custom | BASE_A_H3 | U5 | 8.940 | 2.235 | 6.846 | 2.777 | 0.508 |
| xgboost_custom | BASE_A_H3_dp | U1 | 14.777 | 3.694 | 12.134 | 3.907 | 0.786 |
| xgboost_custom | BASE_A_H3_dp | U2 | 13.768 | 3.442 | 10.774 | 4.229 | 0.721 |
| xgboost_custom | BASE_A_H3_dp | U3 | 21.044 | 5.261 | 12.449 | 8.885 | 0.844 |
| xgboost_custom | BASE_A_H3_dp | U4 | 16.726 | 4.181 | 13.716 | 4.385 | 0.921 |
| xgboost_custom | BASE_A_H3_dp | U5 | 11.121 | 2.780 | 8.105 | 3.789 | 0.553 |
