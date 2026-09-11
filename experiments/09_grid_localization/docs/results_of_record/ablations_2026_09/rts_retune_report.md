# Kalman/RTS Re-tune Across Model Families

- Dataset: `sim_data_300users_2026-07-25_11-46-11`
- History depth: h=5, seed=42
- Test: 29,569 windows over 47 unseen users

| Model | Raw MAE | RTS @ notebook default (Q=0.5, R=15) | Best RTS | Best (Q, R) |
| :--- | ---: | ---: | ---: | :---: |
| knn_h5 | 23.983 m | 21.501 m (+10.35%) | 21.330 m (+11.06%) | Q=1.0, R=15.0 |
| random_forest_h5 | 19.416 m | 19.759 m (-1.77%) | 18.933 m (+2.49%) | Q=4.0, R=25.0 |
| xgboost_h5 | 19.434 m | 19.366 m (+0.35%) | 18.588 m (+4.35%) | Q=2.0, R=15.0 |
| cnn_h5 | 19.076 m | 19.095 m (-0.10%) | 18.380 m (+3.65%) | Q=4.0, R=40.0 |
| gru_h5 | 19.258 m | 19.296 m (-0.20%) | 18.543 m (+3.72%) | Q=2.0, R=15.0 |
| cnn_attn_h5 | 18.857 m | 18.714 m (+0.76%) | 17.964 m (+4.74%) | Q=4.0, R=40.0 |
