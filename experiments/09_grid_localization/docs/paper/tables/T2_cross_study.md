**T2_cross_study.** Mean position error of the best model without history (h = 0) and with history (any depth tested), against always guessing the mean position. Grid: XGBoost, RF single run, CNN and GRU three seeds, h up to 15. 25×25: GRU at h = 15 three seeds, others single run. Macro: XGBoost and RF only (first seed of the error audit); the seven-family result is in Section 7.

| Study | Setting | AoA | Best snapshot (m) | Best with history (m) | Constant guess (m) | Error reduction |
|---|---|---|---|---|---|---|
| 15×15 grid, mixed | BS centre | no | 5.21 (RF) | 1.24 (GRU, h = 15) | 10.9 | 76 % |
| 15×15 grid, mixed | BS centre | yes | 1.25 (RF) | 0.60 (GRU, h = 15) | 10.9 | 52 % |
| 15×15 grid, mixed | BS corner | no | 4.93 (RF) | 1.42 (GRU, h = 15) | 10.9 | 71 % |
| 15×15 grid, mixed | BS corner | yes | 4.25 (RF) | 1.30 (GRU, h = 15) | 10.9 | 69 % |
| 25×25 regression | UMi LOS | no | 14.5 (RF) | 12.4 (GRU, h = 15) | 37.3 | 14 % |
| 25×25 regression | UMi LOS | yes | 8.2 (RF) | 6.6 (GRU, h = 15) | 37.3 | 20 % |
| 25×25 regression | uniform NLOS | no | 29.3 (RF) | 16.7 (GRU, h = 15) | 37.3 | 43 % |
| 25×25 regression | uniform NLOS | yes | 16.0 (RF) | 8.0 (GRU, h = 15) | 37.3 | 50 % |
| 25×25 regression | mixed | no | 24.3 (RF) | 16.7 (GRU, h = 15) | 37.3 | 31 % |
| 25×25 regression | mixed | yes | 13.3 (RF) | 8.7 (GRU, h = 15) | 37.3 | 35 % |
| Macro cell, uniform NLOS | multi-antenna | yes | 18.7 (RF) | 15.4 (XGBoost, h = 5) | 37.1 | 18 % |
| Macro cell, uniform NLOS | single-antenna | no | 34.7 (XGBoost) | 33.1 (RF, h = 5) | 33.6 | 5 % |
