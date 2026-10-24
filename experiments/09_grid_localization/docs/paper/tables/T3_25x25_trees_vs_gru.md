**T3_25x25_trees_vs_gru.** 25×25 regression (five pooled device profiles, NE BS, fixed 4° AoA noise): mean 3D position error. Trees at h = 0, 3, 7, 15 with parameters tuned at h = 3 (single runs); CNN single run; GRU mean ± standard deviation over three seeds. Constant guess 37.3 m.

| Propagation | AoA | Best tree, any depth (m) | CNN h = 15 (m) | GRU h = 15 (m) | GRU gain over best tree (m) |
|---|---|---|---|---|---|
| UMi LOS | no | 13.7 (XGBoost, h = 3) | 14.2 | 12.4 ± 0.2 | 1.3 |
| UMi LOS | yes | 8.2 (RF, h = 0) | 8.0 | 6.6 ± 0.1 | 1.7 |
| uniform NLOS | no | 21.7 (XGBoost, h = 15) | 17.2 | 16.7 ± 0.1 | 5.0 |
| uniform NLOS | yes | 11.3 (XGBoost, h = 15) | 8.9 | 8.0 ± 0.0 | 3.3 |
| mixed | no | 19.1 (XGBoost, h = 15) | 17.4 | 16.7 ± 0.1 | 2.3 |
| mixed | yes | 10.8 (XGBoost, h = 15) | 9.5 | 8.7 ± 0.0 | 2.1 |
