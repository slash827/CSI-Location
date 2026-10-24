**T5_grid_baselines.** 15×15 grid, mixed propagation, BS beyond the corner, RSS and SINR only: mean position error with clean history and with imperfect history (each older report missing with probability 0.3; reports at random gaps with mean 2 steps). Learned models are trained with the same imperfection; CNN three seeds, GRU two, others single run. The HMM filter is causal (past reports only). On this grid every step moves to a neighbouring cell, which suits a motion model.

| Model | Use of history | Regular (m) | 30 % missing (m) | Uneven gaps, mean 2 (m) |
|---|---|---|---|---|
| RF, current report only | no | 4.93 | 4.90 | 4.93 |
| XGBoost, 10 older reports | learned (window) | 3.45 | 4.07 | 3.93 |
| 1D-CNN, 10 older reports | learned (sequence) | 2.49 | 3.38 | 3.01 |
| GRU, 10 older reports | learned (sequence) | 1.59 | 2.06 | 1.99 |
| RF + HMM filter, generic motion (2 m) | motion model | 0.93 | 1.16 | 1.41 |
| RF + HMM filter, learned motion | motion model | 0.71 | 0.98 | 1.27 |
