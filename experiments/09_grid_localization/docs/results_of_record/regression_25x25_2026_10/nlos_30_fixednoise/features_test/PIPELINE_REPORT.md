# Multi-User 3D Regression Pipeline Report

**Generated:** 2026-10-16 14:57:48
**Data directory:** `sim_data_ne_bs_2026-10-16_01-32-21`
**BS position:** `[116.0, 116.0, 10.0]`
**Grid spacing:** `4.0m`

## Overall Regression Results

| Model | Experiment | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) | Train time (s) |
|---|---|---|---|---|---|---|---|
| xgboost | BASE_A_H3_dp | 11.627 | 2.907 | 8.715 | 3.611 | 0.627 | 7.93 |
| rf | BASE_A_H3_dp | 12.408 | 3.102 | 9.579 | 3.570 | 0.688 | 117.75 |
| xgboost | BASE_A_H3_dp_HYBRID | 13.506 | 3.377 | 10.379 | 3.956 | 0.756 | 9.39 |
| rf | BASE_A_H3_dp_HYBRID | 13.218 | 3.304 | 10.150 | 3.837 | 0.727 | 119.79 |
| xgboost | BASE_A_H1_dp_HYBRID | 13.706 | 3.426 | 10.459 | 4.016 | 0.756 | 6.99 |
| rf | BASE_A_H1_dp_HYBRID | 13.243 | 3.311 | 10.213 | 3.776 | 0.732 | 62.21 |
| xgboost | BASE_A_H2_dp_HYBRID | 13.409 | 3.352 | 10.266 | 3.943 | 0.744 | 7.47 |
| rf | BASE_A_H2_dp_HYBRID | 13.197 | 3.299 | 10.157 | 3.801 | 0.729 | 90.83 |

## Per-User Results

| Model | Experiment | User | 3D MAE (m) | MPE (pts) | Dist MAE (m) | Az MAE (°) | El MAE (°) |
|---|---|---|---|---|---|---|---|
| xgboost | BASE_A_H3_dp | U1 | 9.537 | 2.384 | 8.049 | 2.270 | 0.595 |
| xgboost | BASE_A_H3_dp | U2 | 10.647 | 2.662 | 9.142 | 2.410 | 0.634 |
| xgboost | BASE_A_H3_dp | U3 | 19.506 | 4.877 | 11.238 | 8.560 | 0.733 |
| xgboost | BASE_A_H3_dp | U4 | 8.470 | 2.117 | 6.810 | 2.398 | 0.519 |
| xgboost | BASE_A_H3_dp | U5 | 9.976 | 2.494 | 8.338 | 2.416 | 0.654 |
| rf | BASE_A_H3_dp | U1 | 10.690 | 2.673 | 9.264 | 2.306 | 0.676 |
| rf | BASE_A_H3_dp | U2 | 12.369 | 3.092 | 11.036 | 2.399 | 0.755 |
| rf | BASE_A_H3_dp | U3 | 19.954 | 4.989 | 11.419 | 8.742 | 0.729 |
| rf | BASE_A_H3_dp | U4 | 8.315 | 2.079 | 6.903 | 2.109 | 0.546 |
| rf | BASE_A_H3_dp | U5 | 10.708 | 2.677 | 9.272 | 2.292 | 0.733 |
| xgboost | BASE_A_H3_dp_HYBRID | U1 | 11.193 | 2.798 | 9.740 | 2.392 | 0.721 |
| xgboost | BASE_A_H3_dp_HYBRID | U2 | 12.787 | 3.197 | 11.401 | 2.507 | 0.791 |
| xgboost | BASE_A_H3_dp_HYBRID | U3 | 22.285 | 5.571 | 12.696 | 9.831 | 0.832 |
| xgboost | BASE_A_H3_dp_HYBRID | U4 | 9.775 | 2.444 | 8.134 | 2.528 | 0.644 |
| xgboost | BASE_A_H3_dp_HYBRID | U5 | 11.492 | 2.873 | 9.923 | 2.521 | 0.790 |
| rf | BASE_A_H3_dp_HYBRID | U1 | 11.295 | 2.824 | 9.776 | 2.457 | 0.718 |
| rf | BASE_A_H3_dp_HYBRID | U2 | 12.809 | 3.202 | 11.391 | 2.525 | 0.775 |
| rf | BASE_A_H3_dp_HYBRID | U3 | 21.528 | 5.382 | 12.182 | 9.485 | 0.777 |
| rf | BASE_A_H3_dp_HYBRID | U4 | 9.148 | 2.287 | 7.655 | 2.272 | 0.596 |
| rf | BASE_A_H3_dp_HYBRID | U5 | 11.309 | 2.827 | 9.744 | 2.448 | 0.769 |
| xgboost | BASE_A_H1_dp_HYBRID | U1 | 11.383 | 2.846 | 9.836 | 2.449 | 0.739 |
| xgboost | BASE_A_H1_dp_HYBRID | U2 | 12.764 | 3.191 | 11.294 | 2.536 | 0.774 |
| xgboost | BASE_A_H1_dp_HYBRID | U3 | 22.943 | 5.736 | 13.058 | 10.036 | 0.855 |
| xgboost | BASE_A_H1_dp_HYBRID | U4 | 9.833 | 2.458 | 8.152 | 2.517 | 0.615 |
| xgboost | BASE_A_H1_dp_HYBRID | U5 | 11.604 | 2.901 | 9.955 | 2.545 | 0.796 |
| rf | BASE_A_H1_dp_HYBRID | U1 | 11.224 | 2.806 | 9.758 | 2.380 | 0.718 |
| rf | BASE_A_H1_dp_HYBRID | U2 | 12.729 | 3.182 | 11.372 | 2.434 | 0.772 |
| rf | BASE_A_H1_dp_HYBRID | U3 | 21.723 | 5.431 | 12.334 | 9.499 | 0.791 |
| rf | BASE_A_H1_dp_HYBRID | U4 | 9.017 | 2.254 | 7.581 | 2.185 | 0.577 |
| rf | BASE_A_H1_dp_HYBRID | U5 | 11.524 | 2.881 | 10.020 | 2.380 | 0.803 |
| xgboost | BASE_A_H2_dp_HYBRID | U1 | 11.072 | 2.768 | 9.606 | 2.385 | 0.717 |
| xgboost | BASE_A_H2_dp_HYBRID | U2 | 12.603 | 3.151 | 11.189 | 2.502 | 0.774 |
| xgboost | BASE_A_H2_dp_HYBRID | U3 | 22.368 | 5.592 | 12.725 | 9.836 | 0.831 |
| xgboost | BASE_A_H2_dp_HYBRID | U4 | 9.631 | 2.408 | 8.011 | 2.491 | 0.619 |
| xgboost | BASE_A_H2_dp_HYBRID | U5 | 11.373 | 2.843 | 9.796 | 2.500 | 0.777 |
| rf | BASE_A_H2_dp_HYBRID | U1 | 11.240 | 2.810 | 9.744 | 2.424 | 0.717 |
| rf | BASE_A_H2_dp_HYBRID | U2 | 12.773 | 3.193 | 11.378 | 2.489 | 0.776 |
| rf | BASE_A_H2_dp_HYBRID | U3 | 21.497 | 5.374 | 12.182 | 9.443 | 0.779 |
| rf | BASE_A_H2_dp_HYBRID | U4 | 9.097 | 2.274 | 7.633 | 2.232 | 0.593 |
| rf | BASE_A_H2_dp_HYBRID | U5 | 11.380 | 2.845 | 9.846 | 2.415 | 0.781 |
