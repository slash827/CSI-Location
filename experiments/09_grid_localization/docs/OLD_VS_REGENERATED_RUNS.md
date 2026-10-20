# Earlier controlled-grid results against the regenerated ones

Written 2026-10-14 (table row for the 25×25 regression updated 2026-10-20) to explain to the instructors why the 15×15 controlled-grid numbers they saw earlier differ from the current ones. The detailed numbers are in `PLAN_AND_CHECKLIST.md` §7 and in `docs/results_of_record/controlled_grid_2026_10/comparison_sets.md`.

## 1. Short version

- The 15×15 results shown before (centre BS about 80 % exact cell with AoA, NE BS about 86 % with history) came from simulations made on 2026-06-12. Those simulations cannot be regenerated from the repository: the committed code and configuration of that date give the same walk and the same angles for the centre BS, but different RSS and SINR, and a different walk for the NE BS (section 3).
- Two defects of the generator were found while trying. The configured carrier frequency was never passed to QuaDRiGa (it ran at 2.6 GHz), and the Voronoi cells never changed the propagation scenario (each walk used the scenario of its first cell). Both are fixed.
- The controlled grid was therefore regenerated under three documented propagation settings (RMa LOS, mixed per-cell UMi LOS/NLOS, uniform UMi NLOS) at 3.0 GHz, with the configuration copied into each simulation folder. The conclusion that history helps holds in every set; the absolute accuracies are lower than the June ones, and the June NE numbers are not reproduced by any setting.

## 2. Which earlier result sets are affected

| Earlier result | What changed | Status |
|---|---|---|
| 15×15 centre BS, June (`multi_user_voronoi_15x15_optimal`) | Not reproducible; the no-AoA numbers are matched by the RMa LOS set (BASE_H3 XGBoost 51.0 % against 50.6 %), the AoA numbers are lower now (82.4 % against 71.6 %) | Superseded by the regenerated sets |
| 15×15 NE BS, June (`ne_bs_voronoi_15x15_optimal`) | Not reproducible; BASE_H3 XGBoost 86.0 % in June against 48.6 % (RMa LOS), 57.3 % (mixed), 25.8 % (NLOS) now, and 60.9 % in the May run | Superseded; the June NE values should not be quoted |
| 15×15 May run (`multi_user_voronoi_15x15`, `ne_bs_voronoi_15x15`) | Older simulations (March and April), 2.6 GHz, tuned Random Forest | Kept as history; not regenerated |
| Single-user grid-size sweeps (3×3 to 20×20), 7×7 depth sweep | Generated at 2.6 GHz although the configs say 3.0 GHz | Not regenerated; the carrier effect was shown to be small (NLOS at 3.0 and 3.5 GHz agree within about 1 pp) |
| 25×25 regression (five pooled device profiles, earlier called single-user) | 2.6 GHz; June runs used fixed 4° AoA noise, while the controlled-grid pipelines use SINR-dependent noise | Regenerated 2026-10-15/16 at 3.0 GHz under UMi LOS, uniform NLOS and mixed propagation. With the same fixed noise the AoA gap to June closes (`technical_documentation_revised.md` §6.4, `PLAN_AND_CHECKLIST.md` §9–§13) |
| Macro-cell study (300 users), B6 blocked LOS, all `followup_2026_10` results | Their runners set the carrier from the config (3.0 GHz) | Unaffected |

## 3. What the reproduction attempt showed

Method: the repository as of commit `6c1c02a` (2026-06-06, the last commit before the June runs), its original configs, the original generator (2.6 GHz by default), user 1 with walk seed 100, both placements, compared with the June files.

- Centre BS: grid point, x, y and the clean AoA values are bit-identical to the June file. RSS is not (per-cell map correlation 0.51, mean difference 1.9 dB, standard deviation 4.7 dB), and SINR is uncorrelated (correlation −0.14, mean 10 dB lower).
- NE BS: the walk itself differs (other grid points, positions and angles).
- Running the old and the current code on the same short walk gives identical results, so the generator is deterministic and the difference is a difference in settings.
- Settings known to differ between June and the regeneration: carrier (2.6 against 3.0 GHz), cell layout (June `auto_generate` with seed 42, now explicit cells), scenario (June the first automatic cell, RMa LOS; now uniform or per cell), NE interferer positions ([19,−10] and [−10,19] in June, [−11,19] and [19,−11] now). None of these explains the centre RSS and SINR difference, so the June files were most likely made from a working tree with uncommitted changes.

## 4. What to say about the 20–30 m errors

They belong to the macro regression study, not to the 15×15 classification study. With multi-antenna devices the error is 19.0 m without and 15.4 m with history, against 37.1 m for always guessing the mean training position; single-antenna devices are at 34.7 m against a constant guess of 33.6 m. The metric audit (`tests/test_error_metrics.py`, `error_audit_grid.py`) shows that MAE equals (1 − accuracy) times the mean error of the wrong predictions, so an 80 % exact-cell result cannot coincide with a 30 m MAE in the same experiment.
