# Hyperparameter Tuning Notes — Multi-User 15×15 Pipeline

## Summary

RF hyperparameters were tuned with Optuna (30 trials, 30% subsample). XGBoost tuning was attempted but produced invalid params and was abandoned. XGBoost uses library defaults.

---

## RF Tuning (Succeeded)

**Tool:** Optuna 4.x, TPE sampler  
**Config:** 30 trials, 30% of training data (~86K samples from 360K total), 5-fold CV  
**Objective:** maximize validation accuracy  

**Best params found:**
```json
{
  "n_estimators": 150,
  "max_depth": 16,
  "min_samples_leaf": 5
}
```

**Impact:** BASE experiment accuracy improved from **43.5% → 45.9%** (+2.4 pp). Gains compound across experiments with history and AoA features.

**Stored in:** `results/multi_user_voronoi_15x15/tuning/tuned_params.json`

These params are reused for NE-BS runs — they control model complexity (depth, leaf size, tree count), which is not data-distribution-specific. Tuning per placement is unnecessary.

---

## XGBoost Tuning (Failed — Use Defaults)

**What happened:** Optuna found `learning_rate=0.29` as optimal on the 30% subsample (86K samples). When applied to the full 360K training set, accuracy collapsed to **4.5%** (random-chance level for 225 classes).

**Root cause:** Optimal XGBoost learning rate scales with dataset size and number of boosting rounds. A fast learning rate works on small data (few rounds needed to fit) but causes overshooting on large data. The 70% holdout was not representative of full-training dynamics.

**Fix:** Removed the XGBoost entry from `tuned_params.json`. XGBoost defaults (`learning_rate=0.1`, `n_estimators=100`, etc.) were already validated and give ~83% accuracy with AoA+history features.

**Lesson:** When tuning XGBoost on a fraction of the data, either (a) use a matching number of `n_estimators` that was optimized at that scale, or (b) use a fixed `learning_rate=0.1` and tune only tree structure params.

---

## Reproducing Tuning

```bash
# From project root
python experiments/09_grid_localization/src/python/pipelines/multi_user_pipeline.py \
  --data-dir results/grid_localization/grid_15x15/sim_data_multi_user_2026-03-02_19-41-39 \
  --out-dir results/multi_user_voronoi_15x15 \
  --models rf \
  --tune-hyperparams --tune-trials 30 --tune-fraction 0.30 \
  --run-only BASE
```

Note: requires `pip install optuna` — not included in default requirements.
