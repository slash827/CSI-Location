# Tasks — Next Advisor Meeting

## Experiment Naming Convention

| Index | Name | Features | h | AoA | Extra |
|-------|------|----------|---|-----|-------|
| E1  | `BASE`        | RSS+SINR     | 0 | No  | — |
| E2  | `BASE_dp`     | RSS+SINR     | 0 | No  | device params |
| E3  | `BASE_uid`    | RSS+SINR     | 0 | No  | user ID |
| E4  | `BASE_H`      | RSS+SINR     | 3 | No  | — |
| E5  | `BASE_H_dp`   | RSS+SINR     | 3 | No  | device params |
| E6  | `BASE_H_uid`  | RSS+SINR     | 3 | No  | user ID |
| E7  | `BASE_A`      | RSS+SINR+AoA | 0 | Yes | — |
| E8  | `BASE_A_dp`   | RSS+SINR+AoA | 0 | Yes | device params |
| E9  | `BASE_A_uid`  | RSS+SINR+AoA | 0 | Yes | user ID |
| E10 | `BASE_A_H`    | RSS+SINR+AoA | 3 | Yes | — |
| E11 | `BASE_A_H_dp` | RSS+SINR+AoA | 3 | Yes | device params |

**Legend:**
- `BASE` — RSS+SINR only (single serving BS)
- `A` — AoA azimuth + elevation (4° Gaussian noise + 5° quantization applied)
- `H` — History: absolute value stacking, h=3
- `dp` — device params: n_antennas, antenna_gain_db, ue_height
- `uid` — user_id as integer feature (oracle device identity)

**Mapping from old names (for updating existing files):**

| Old | New index | New name |
|-----|-----------|----------|
| E1 | E1  | `BASE` |
| E2 | E4  | `BASE_H` |
| E3 | E5  | `BASE_H_dp` |
| E4 | E6  | `BASE_H_uid` |
| E5 | E7  | `BASE_A` |
| E6 | E10 | `BASE_A_H` |
| E7 | E11 | `BASE_A_H_dp` |

---

## Task 1: Rename Existing Experiments Throughout Codebase ✅ DONE

Update all references from old E1–E7 to new names across:
- `results/multi_user_voronoi_15x15/results_summary.csv` ✅
- `results/multi_user_voronoi_15x15/per_user_breakdown.csv` ✅
- `results/multi_user_voronoi_15x15/per_cell_breakdown.csv` ✅
- `src/python/multi_user_pipeline.py` ✅
- `docs/research_documentation.md` ✅
- `docs/PRESENTATION_SLIDES.md` ✅

---

## Task 2: Add Missing Static Baseline Experiments (E2, E3, E8, E9) ✅ DONE

Currently there are no static (h=0) experiments that include device information.
Without them it is impossible to isolate the contribution of transition history
from the contribution of device knowledge.

New experiments to run (both RF and XGBoost):

| Index | Name | Adds over E1 |
|-------|------|--------------|
| E2 | `BASE_dp`   | device params, no history |
| E3 | `BASE_uid`  | user ID, no history |
| E8 | `BASE_A_dp`  | device params, no history, with AoA |
| E9 | `BASE_A_uid` | user ID, no history, with AoA |

Results appended to `results_summary.csv` for both XGBoost and RF. Documented in `research_documentation.md` §8.8.

**The clean isolation this enables:**

```
Effect of history alone:      BASE   → BASE_H      (E1 → E4)
Effect of device info alone:  BASE   → BASE_dp     (E1 → E2)  ← new
Effect of both:               BASE   → BASE_H_dp   (E1 → E5)

Same with AoA:
Effect of history alone:      BASE_A → BASE_A_H    (E7 → E10)
Effect of device info alone:  BASE_A → BASE_A_dp   (E7 → E8)  ← new
Effect of both:               BASE_A → BASE_A_H_dp (E7 → E11)
```

---

## Task 3: A/B Comparison — Absolute Values vs. Deltas ✅ DONE

Test when delta representation outperforms absolute value stacking.

**Hypothesis:** With scarce data or heterogeneous users, deltas outperform
absolute values because relative changes are consistent across devices with
different RSS offsets. At high data volumes, absolute values perform comparably
or better.

Run delta variants of the four core transition experiments:

| Delta name | Absolute equivalent |
|------------|---------------------|
| `BASE_H_delta`     | `BASE_H` (E4) |
| `BASE_H_dp_delta`  | `BASE_H_dp` (E5) |
| `BASE_A_H_delta`   | `BASE_A_H` (E10) |
| `BASE_A_H_dp_delta`| `BASE_A_H_dp` (E11) |

**Data volume sweep** — run `BASE_H` vs `BASE_H_delta` at 4 training fractions:
10%, 25%, 50%, 100% of training samples per user.

Results: all 4 delta variants run for XGBoost + RF; `data_volume_sweep.csv` saved.
Documented in `research_documentation.md` §8.9. Key finding: absolute outperforms delta
at every data volume; device-specific offsets are useful fingerprints, not noise.

---

## Task 4: Environmental Variability Experiment ⚠️ INCOMPLETE

Run U1 (Flagship A: 4 antennas, 0 dB, 1.5m) three times on the same 15×15
Voronoi grid with different QuaDRiGa seeds to simulate day-to-day variability.

- Train on runs 1 + 2, test on run 3 (unseen environment realization)
- Compare: `BASE` (E1) vs `BASE_H` (E4) vs `BASE_H_delta`
- Also run the same models on a single-run split as reference

Note: Check whether QuaDRiGa supports scenario-level variability beyond seed
variation. Use if available.

**Status:** MATLAB script `run_env_variability_15x15.m` was created with the correct
logic (3 runs × channel seeds 101/102/103, fixed walk seed=100). However, the script
was **never executed in MATLAB** — no simulation data exists under
`results/grid_localization/grid_15x15/sim_data_env_variability_*/`.
Python `run_env_variability()` function exists in `multi_user_pipeline.py`.
Decision: deprioritised in favour of the NE-BS placement experiment (April 2026 plan).

---

## Task 5: Research Documentation ✅ DONE

Send Dudi a link to `docs/research_documentation.md` after Task 1 renaming is done.
Do not rewrite before receiving his feedback.

All sections (8.1–8.9 + §9 Key Findings) written and verified against actual CSV results.
"Last Updated" field to be updated to April 2026 once NE-BS results are added.
