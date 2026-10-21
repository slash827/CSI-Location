# 25x25 regression, mean 3D error (m): trees (tuned with h=3 parameters) vs GRU/CNN

One run each, fixed 4 deg AoA noise, chronological split, 30 % training subsample, NE BS, 3.0 GHz. Trees: multi_user_pipeline_regression.py; GRU/CNN: regression25_sequence.py (150 epochs max, validation block from training data).

| set | AoA | model | h=0 | h=3 | h=7 | h=15 |
|---|---|---|---|---|---|---|
| mixed | no | cnn | 29.0 | 23.7 | 19.7 | 17.4 |
| mixed | no | gru | 28.7 | 23.0 | 19.2 | 16.7 |
| mixed | no | rf | 24.3 | 23.2 | 23.3 | 23.5 |
| mixed | no | xgboost | 29.9 | 20.5 | 19.6 | 19.1 |
| mixed | yes | cnn | 17.0 | 11.7 | 9.9 | 9.5 |
| mixed | yes | gru | 16.7 | 11.3 | 9.5 | 8.7 |
| mixed | yes | rf | 13.3 | 12.4 | 12.3 | 12.2 |
| mixed | yes | xgboost | 16.2 | 11.3 | 10.9 | 10.8 |
| nlos | no | cnn | 31.6 | 26.0 | 21.5 | 17.2 |
| nlos | no | gru | 31.2 | 25.2 | 21.0 | 16.9 |
| nlos | no | rf | 29.3 | 26.6 | 26.3 | 26.0 |
| nlos | no | xgboost | 33.3 | 24.5 | 22.8 | 21.7 |
| nlos | yes | cnn | 18.3 | 11.7 | 10.2 | 8.9 |
| nlos | yes | gru | 17.8 | 11.7 | 9.2 | 8.0 |
| nlos | yes | rf | 16.0 | 13.3 | 12.8 | 12.5 |
| nlos | yes | xgboost | 18.0 | 12.5 | 11.7 | 11.3 |
| umilos | no | cnn | 28.2 | 21.3 | 16.7 | 14.2 |
| umilos | no | gru | 26.2 | 19.6 | 15.6 | 12.3 |
| umilos | no | rf | 14.5 | 17.1 | 17.9 | 18.7 |
| umilos | no | xgboost | 29.4 | 13.7 | 14.0 | 14.4 |
| umilos | yes | cnn | 15.1 | 9.5 | 7.9 | 8.0 |
| umilos | yes | gru | 14.1 | 8.8 | 7.3 | 6.7 |
| umilos | yes | rf | 8.2 | 9.4 | 9.5 | 9.6 |
| umilos | yes | xgboost | 12.5 | 8.4 | 8.6 | 8.9 |

## GRU at h = 15: three seeds and a 400-epoch cap (2026-10-21)

| set | AoA | seed 0 / 1 / 2 (150 epochs) | mean | 400-epoch cap, seed 0 | best tree (any h) |
|---|---|---|---|---|---|
| umilos | no | 12.3 / 12.3 / 12.7 | 12.4 | 11.5 | 13.7 (XGBoost h=3) |
| umilos | yes | 6.7 / 6.5 / 6.5 | 6.6 | 6.3 | 8.2 (RF h=0) |
| nlos | no | 16.9 / 16.6 / 16.6 | 16.7 | 16.8 | 21.7 (XGBoost h=15) |
| nlos | yes | 8.0 / 8.0 / 7.9 | 8.0 | 7.7 | 11.3 (XGBoost h=15) |
| mixed | no | 16.7 / 16.8 / 16.7 | 16.7 | 16.3 | 19.1 (XGBoost h=15) |
| mixed | yes | 8.7 / 8.7 / 8.7 | 8.7 | 8.3 | 10.8 (XGBoost h=15) |

Seed spread is at most 0.4 m; the gap to the best tree is 1.3 to 5.0 m. The longer cap lowers the error by up to 0.9 m.
