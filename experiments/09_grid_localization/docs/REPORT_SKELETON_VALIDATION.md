# Validation of `REPORT_SKELETON.md`

First pass 2026-10-09 (checked every claim against the files of record). Second pass 2026-10-12 (ran the experiments needed to settle what the first pass left open). This version replaces the first.

## How this was checked

- **Pass 1.** Every number in the skeleton was re-read or recomputed from the JSON / `.npz` files under `docs/results_of_record/`, the code and the configs. Nothing was re-trained.
- **Pass 2.** New runs, all under `docs/results_of_record/followup_2026_10/` (see `MANIFEST.md`):
  - `history_mechanism_followup.py`: the diagnostic protocol (unseen-user split, XGBoost and Random Forest at master-benchmark hyperparameters, h=5 windows, conditions paired by sample and by seed) with **20 seeds** on the uniform-NLOS, mixed and blocked-LOS datasets; extra conditions; error stratified by region, range band, real LOS and window type; and a sweep of the AoA impairment (10 seeds each).
  - `history_mechanism_deep.py`: the channel test on the 1D-CNN and the GRU, 5 seeds, uniform NLOS.
- **Intervals.** All pass-2 intervals are Student-t 95% over seed-paired differences. The skeleton's "±" values come from `ci95()` = `1.96·s/√n` with n = 5, which is 1.42× narrower than the t interval. No conclusion in C1 flips, but the report should state which interval it uses.
- **Verdict labels.** **Supported** / **Supported, caveat** / **Overstated** / **Contradicted** / **Interpretation** (not measured) / **Not verifiable here**.

## What changed between the two passes

| Pass-1 open point | Pass-2 result |
|---|---|
| "LOS advantage" might be geometry, not propagation | **Confirmed geometry.** The LOS-region minus NLOS-region gap is the same on both datasets (difference −0.16 ± 0.28 m). |
| Mechanism "bearing turns more slowly with range" untested | **Rejected.** The gain is the averaging of per-sample AoA measurement error, mostly in elevation. With error-free AoA the gain is zero. |
| C2 "inferred for the neural models" | **Now measured.** 1D-CNN and GRU show the same channel pattern. |
| Single-antenna gain on mixed data "unexplained" | **Robust (20/20 seeds) and partly explained:** it is tied to LOS/NLOS state and to boundary-crossing windows. |
| P3 "not supported" vs "inconclusive" | **No consistent range trend at 20 seeds.** "Rises with range" on mixed data did not replicate. |
| B6 pooled device groups | **Split.** Multi-antenna +6.3 m (36%); single-antenna no detectable gain. |

---

## Part A. What the follow-up runs establish

These are the claims the report can now make. Each is followed by the evidence.

### A1. The multi-antenna history gain is the averaging of AoA measurement error

Uniform NLOS, multi-antenna, gain over `snap` in metres (Student-t 95%). 20 seeds for the first row, 10 for the others. Source: `followup_2026_10/uniform_nlos/` and `followup_2026_10/aoa_impairment/`.

| AoA impairment | Model | h=0 error | Full history | Elevation history | Azimuth history | Window mean of angle channels |
|---|---|---|---|---|---|---|
| **4° noise + 5° quantization (as in the report)** | XGBoost | 18.74 m | +3.15 ± 0.12 | +2.72 ± 0.13 | +0.63 ± 0.08 | +3.38 ± 0.19 |
| | Random Forest | 18.76 m | +2.75 ± 0.08 | +2.24 ± 0.12 | +0.77 ± 0.05 | +3.61 ± 0.19 |
| **None (exact AoA)** | XGBoost | 2.32 m | +0.00 ± 0.11 | −0.02 ± 0.17 | +0.06 ± 0.11 | +0.03 ± 0.10 |
| | Random Forest | 1.58 m | −1.02 ± 0.03 | −0.70 ± 0.04 | −0.65 ± 0.04 | −0.37 ± 0.03 |
| 5° quantization only | XGBoost | 14.20 m | +1.89 ± 0.17 | +1.06 ± 0.19 | +0.97 ± 0.15 | +1.60 ± 0.20 |
| | Random Forest | 14.00 m | +2.34 ± 0.06 | +1.04 ± 0.10 | +1.35 ± 0.14 | +2.18 ± 0.14 |
| 4° noise only | XGBoost | 18.54 m | +3.13 ± 0.31 | +2.84 ± 0.31 | +0.66 ± 0.06 | +3.46 ± 0.36 |
| | Random Forest | 18.43 m | +3.07 ± 0.15 | +2.57 ± 0.21 | +0.90 ± 0.08 | +3.61 ± 0.31 |
| 8° noise + 5° quantization | XGBoost | 21.72 m | +2.39 ± 0.14 | +1.33 ± 0.20 | +1.07 ± 0.14 | +2.52 ± 0.18 |
| | Random Forest | 21.61 m | +1.82 ± 0.09 | +0.51 ± 0.12 | +1.04 ± 0.10 | +2.56 ± 0.17 |

What this shows:

1. **With exact AoA there is nothing for history to add.** Multi-antenna error falls to about 2 m and the gain is zero (XGBoost) or negative (Random Forest, where the extra columns only dilute the split candidates).
2. **An order-free mean is enough.** `angle_mean` appends only the mean of each angle channel over the six steps to the snapshot. It matches or beats the full ordered angle history in every row. Paired, on uniform NLOS: `angle_hist` is 0.22 ± 0.11 m *worse* than `angle_mean` for XGBoost and 0.55 ± 0.08 m worse for Random Forest.
3. **Time order contributes little.** Shuffling the lagged steps costs 0.23 ± 0.05 m (XGBoost) and 0.40 ± 0.02 m (Random Forest) out of about 3 m.
4. **Elevation carries most of it.** Elevation history alone gives 86% (XGBoost) and 82% (Random Forest) of the full gain; azimuth history gives 20% and 28%. The BS is 8.5 m above the UE, so elevation encodes range, and that is why the radial error is what improves.
5. **The ~15 m multi-antenna error is the impairment model.** Quantization to 5° alone produces 14.2 m; 4° noise alone produces 18.5 m; exact AoA gives 2 m.

**Consequence for the skeleton.** C2's explanation "a sequence of bearings constrains distance because the bearing turns more slowly with range (dθ/dt = v⊥/r)" is **rejected**, and the title option "How Angle Sequences Recover Range" is not supported in that sense. The measured statement is: *history lets the model average several noisy, coarsely quantized angle reports, and because elevation maps to range, the averaging shows up as lower range error.*

### A2. The size of the gain depends on the AoA error being independent from one report to the next

Same pipeline, 4° noise + 5° quantization, but the noise follows an AR(1) process along each walk with lag-1 correlation ρ (10 seeds). Source: `followup_2026_10/aoa_impairment/corr_rho*/`.

| ρ | XGBoost full | XGBoost elevation | XGBoost azimuth | Random Forest full |
|---|---|---|---|---|
| 0 (independent, as in the report) | +3.10 ± 0.23 (17%) | +2.69 ± 0.25 | +0.63 ± 0.15 | +2.75 ± 0.14 (15%) |
| 0.5 | +1.79 ± 0.13 (10%) | +1.27 ± 0.10 | +0.49 ± 0.13 | +1.87 ± 0.12 (10%) |
| 0.9 | +0.98 ± 0.14 (5%) | +0.25 ± 0.09 | +0.69 ± 0.12 | +1.15 ± 0.12 (6%) |
| 0.99 | +1.16 ± 0.16 (6%) | +0.03 ± 0.09 | +0.92 ± 0.14 | +1.26 ± 0.16 (7%) |

- The elevation part disappears once the error persists across the window. That is the part that needed independent errors.
- About 1 m (5–7%) survives even at ρ = 0.99. It sits in azimuth and matches the quantization-only row of A1: as the user moves, the true angle crosses quantization boundaries, so the window resolves the angle more finely than one 5° report. This part does not depend on independent noise.
- h=0 error is the same in all four rows (18.4–18.8 m), so only the gain changes.

**Consequence.** The headline "14.7–20.8%" is specific to an impairment model with independent per-report error. The report must state this assumption with the headline, and should give the range: about 17% with independent error, about 6% when the error is persistent. Which end real hardware is nearer to was not studied.

### A3. The channel result holds for the neural models

Uniform NLOS, 5 seeds, multi-antenna gain over `snap`. Channels without history are held at their current value across the window. Source: `followup_2026_10/neural_uniform_nlos/`.

| Model | RSS history | Angle history | Window mean of angles | Full |
|---|---|---|---|---|
| 1D-CNN | +0.17 ± 0.20 | +3.11 ± 0.72 | +3.04 ± 0.77 | +3.07 ± 0.55 |
| GRU | +0.19 ± 0.14 | +3.43 ± 0.79 | +2.99 ± 0.90 | +3.19 ± 0.60 |

- Angle history alone equals full history (paired difference 0.04 ± 0.26 m CNN, 0.23 ± 0.48 m GRU). RSS history adds under 0.2 m.
- Radial error falls 17.1 → 14.0 m (CNN) and 17.4 → 14.3 m (GRU); tangential moves 5.4 → 5.1 and 5.2 → 4.8 m.
- Single-antenna: no condition clears its interval.
- For the GRU the ordered angle history is 0.44 ± 0.22 m better than the window mean; for the CNN there is no difference. A small order effect for the GRU, consistent with the ≤ 0.4 m found for the trees.
- Caveat: checkpoints are selected on test MAE, as everywhere in `model_zoo.train_deep`, identically for every condition.

So C2 is now **established for XGBoost, Random Forest, k-NN (5 seeds), 1D-CNN and GRU**. CNN+attention and the mask-aware CNN were not run.

### A4. Line-of-sight propagation does not change the history gain

The two macro-cell datasets share walks and user ids, so a seed gives the same test users in both. Multi-antenna gain in metres, 20 seeds; "LOS regions" are Highway and Park, "NLOS regions" are Shopping and Residential. On the mixed dataset the real per-sample LOS flag coincides exactly with this geometric label. Source: `followup_2026_10/mixed_propagation/region_gain_did_vs_uniform.json`.

| Model, condition | Uniform NLOS: LOS regions | NLOS regions | Gap | Mixed: LOS regions | NLOS regions | Gap | Mixed − uniform gap |
|---|---|---|---|---|---|---|---|
| XGBoost, full | +3.56 ± 0.17 | +1.75 ± 0.16 | +1.81 ± 0.27 | +3.10 ± 0.19 | +1.55 ± 0.13 | +1.54 ± 0.24 | −0.27 ± 0.25 |
| XGBoost, angle history | +3.57 ± 0.18 | +1.76 ± 0.20 | +1.81 ± 0.29 | +3.04 ± 0.20 | +1.40 ± 0.14 | +1.65 ± 0.25 | −0.16 ± 0.28 |
| Random Forest, full | +3.08 ± 0.10 | +1.62 ± 0.14 | +1.45 ± 0.19 | +2.69 ± 0.09 | +1.25 ± 0.09 | +1.44 ± 0.12 | −0.01 ± 0.18 |
| Random Forest, angle history | +3.43 ± 0.15 | +1.83 ± 0.15 | +1.60 ± 0.20 | +2.69 ± 0.13 | +1.16 ± 0.07 | +1.52 ± 0.14 | −0.08 ± 0.17 |

- The regional gap exists with no LOS anywhere, and making the propagation real does not widen it. If anything the gain in the LOS regions is slightly *smaller* with real LOS.
- The gap is range and geometry. XGBoost full-history gain by region and range band on uniform NLOS: Park below 40 m +10.8 m, Park 40–80 m +4.5 m, Park 80–120 m +1.2 m, Highway 80–120 m +1.8 m, Highway ≥ 120 m +5.5 m, Shopping 40–80 m +1.1 m, Shopping 80–120 m +1.3 m. The "LOS regions" simply contain the short-range and long-range bands where the gain is largest.

**Consequence.** C2's fourth bullet, `fig_los_nlos_channels` as a propagation result, `CONTINUE_HERE.md` §6.4 ("RE-CONFIRMED") and the corresponding `MANIFEST.md` row are wrong and have been corrected. The earlier "+15.9% vs +8.7%" is a true description of two *regions*; it says nothing about LOS.

### A5. Without an angle, history gives no detectable gain on uniform NLOS

Single-antenna gain over `snap`, 20 seeds (3–11 single-antenna test users per seed).

| Model | RSS history | Full history |
|---|---|---|
| XGBoost | +0.02 ± 0.37 (11/20 seeds positive) | −0.18 ± 0.34 (11/20) |
| Random Forest | +0.29 ± 0.44 (12/20) | +0.42 ± 0.39 (12/20) |
| 1D-CNN (5 seeds) | +1.03 ± 1.50 | −0.46 ± 2.01 |
| GRU (5 seeds) | −0.02 ± 1.78 | −0.51 ± 0.97 |

- XGBoost: any gain is below about 0.4 m (1% of 36 m).
- Random Forest full history just clears its interval (+0.42 ± 0.39 m, 1.1%), with only 12 of 20 seeds positive. Report it as "at most about 1%", not as a clean zero.
- Single-antenna error structure (XGBoost, 20 seeds): radial RMS 25.5 m, tangential RMS 30.4 m; the radial share of squared error is 41 ± 2%; predicted range correlates 0.51 ± 0.06 with true range; radial bias −9.7 m. For multi-antenna devices the radial share is 92% at h=0 and 90% at h=5 and the range correlation rises from 0.60 to 0.75.

### A6. The single-antenna gain on mixed data is real, and tied to propagation state

Mixed dataset, single-antenna, 20 seeds. Source: `followup_2026_10/mixed_propagation/` and `mixed_propagation_los_flag/`.

| Condition | XGBoost | Random Forest |
|---|---|---|
| RSS history | +1.28 ± 0.29 (20/20 seeds) | +1.41 ± 0.36 (20/20) |
| Full history | +1.14 ± 0.29 (19/20) | +1.28 ± 0.37 (20/20) |
| Angle history | −0.07 ± 0.25 | −1.13 ± 0.34 |
| Snapshot + true LOS flag (oracle, no history) | +3.27 ± 0.49 (20/20) | +3.04 ± 0.44 (20/20) |
| RSS history + true LOS flag | +4.28 ± 0.45 | +3.81 ± 0.48 |
| **RSS history on top of the flag** | **+1.01 ± 0.27** | **+0.77 ± 0.25** |

RSS history on top of the flag, by window type (14% of single-antenna windows cross an LOS/NLOS boundary):

| Window | XGBoost | Random Forest |
|---|---|---|
| Crosses a boundary | +2.61 ± 0.48 | +3.92 ± 0.43 |
| Entirely LOS | +0.79 ± 0.29 | +0.34 ± 0.34 |
| Entirely NLOS | +0.63 ± 0.44 | −0.03 ± 0.24 |

- The gain replicates in every seed for both tree models. It is not a small-sample artifact.
- A single-antenna snapshot cannot tell LOS from NLOS (the two differ by about 17 dB at equal range). Telling the model which it is is worth about 3 m. Without the flag, RSS history gains 0.9–2.1 m even in windows that are entirely LOS or entirely NLOS, which is consistent with history helping the model infer the state.
- Once the flag is given, the remaining benefit of RSS history is concentrated in boundary-crossing windows (+2.6 to +3.9 m), where the RSS step marks a known place on the map. For Random Forest nothing is left elsewhere; for XGBoost about 0.7 m is.
- **Supported:** the gain exists, it is absent on uniform NLOS, and it is linked to LOS/NLOS state and to boundary crossings. **Interpretation:** that the mechanism is "state inference plus a boundary landmark". The skeleton's "one-split lead points to windows that cross an LOS/NLOS boundary" is half right: crossings matter most, but the gain is also present in windows that do not cross.
- The neural models were not tested for this (the mixed seed repeats show no gain for them).

### A7. In the blocked-LOS corridor, the gain is azimuth averaging and is not specific to blockage

20 seeds, XGBoost. Source: `followup_2026_10/blocked_los/`.

| Group | Stretch | h=0 error | Full history | Window mean of angles | Azimuth history | Elevation history |
|---|---|---|---|---|---|---|
| Multi-antenna | blocked | 17.42 m | +6.29 ± 0.18 (36%) | +6.51 ± 0.18 | — | — |
| Multi-antenna | unblocked | 17.21 m | +6.66 ± 0.15 (39%) | +6.89 ± 0.12 | — | — |
| Multi-antenna | whole walk | | +6.54 ± 0.12 | +6.77 ± 0.11 | +6.54 ± 0.12 | −0.01 ± 0.03 |
| Single-antenna | blocked | 25.17 m | +0.47 ± 0.54 | −0.15 ± 0.48 | | |
| Single-antenna | unblocked | 56.75 m | +0.29 ± 0.36 | −0.00 ± 0.51 | | |

Multi-antenna gain in the blocked stretch by strip width (full history):

| Width (m) | 5 | 10 | 20 | 40 | 80 | 100 | 120 | 150 |
|---|---|---|---|---|---|---|---|---|
| Gain (m) | 5.2 ± 1.0 | 5.6 ± 2.1 | 5.7 ± 0.8 | 6.0 ± 0.7 | 6.0 ± 0.6 | 5.3 ± 0.3 | 6.1 ± 0.4 | 7.7 ± 0.3 |
| Gain (%) | 30 | 32 | 33 | 35 | 35 | 32 | 35 | 41 |

- The gain is the same inside and outside the blocked stretch, so the corridor shows nothing special about blockage.
- All of it is azimuth (the BS stands 500 m off, so 5° of azimuth is tens of metres across), and the window mean recovers all of it. Same mechanism as A1.
- Single-antenna devices gain nothing detectable.
- No rise-and-fall with width. The only width that stands out is 150 m (+7.7 m), the widest tested.
- Random Forest gives the same picture (+6.13 ± 0.18 blocked, +6.16 ± 0.12 unblocked).

### A8. The RSS-history gain has no consistent range trend (P3)

`rss_hist` gain over `snap` by range band, 20 seeds:

| Dataset, group | Model | < 40 m | 40–80 m | 80–120 m | ≥ 120 m |
|---|---|---|---|---|---|
| Uniform NLOS, multi | XGBoost | +0.93 ± 0.58 | +0.63 ± 0.21 | −0.15 ± 0.11 | +0.70 ± 0.28 |
| Uniform NLOS, multi | Random Forest | −1.39 ± 0.43 | +0.43 ± 0.18 | −0.42 ± 0.13 | −0.37 ± 0.32 |
| Mixed, multi | XGBoost | +0.82 ± 0.32 | +0.63 ± 0.13 | +0.11 ± 0.07 | +0.77 ± 0.18 |
| Mixed, single | XGBoost | +1.76 ± 1.11 | +0.90 ± 0.71 | +1.34 ± 0.30 | +1.48 ± 0.91 |
| Mixed, single | Random Forest | +1.90 ± 1.62 | +1.15 ± 0.62 | +1.40 ± 0.38 | +1.63 ± 0.76 |

- XGBoost: highest below 40 m, lowest at 80–120 m, back up beyond 120 m. Random Forest: the opposite sign below 40 m. No monotonic decline in either.
- The 5-seed "rises with range (+0.4 → +2.4 m)" for single-antenna devices on mixed data did not replicate: at 20 seeds it is flat at 0.9–1.8 m.
- The angle-history gain is U-shaped in range for both models and both datasets (XGBoost, uniform: +11.0, +3.8, +1.7, +5.4 m). The < 40 m part is elevation (+11.0 of +11.0 m); beyond 120 m azimuth contributes +1.4 m and elevation +4.4 m. The rise beyond 120 m is no longer unexplained in kind: it is the same averaging, applied where the h=0 error is largest (28 m).

### A9. The h=0 baseline already holds one step of change

`pure_snap` vs `snap`, multi-antenna, 20 seeds: XGBoost −0.56 ± 0.16 m (uniform), −0.56 ± 0.11 m (mixed); Random Forest −0.37 ± 0.08 m, −0.44 ± 0.06 m. Against full-history gains of 3.15, 2.75, 2.75 and 2.36 m in the same order, that is 18%, 20%, 14% and 19%.

---

## Part B. Verdict on each skeleton claim

### C1. History lowers error in every model family, for devices that report an angle

| Bullet | Verdict | Notes |
|---|---|---|
| Gain 2.75–4.06 m (14.7–20.8%) in all seven families | **Supported, caveat** | Exact (`seed_repeats_all_models_summary.json`, per-run `multi_mae`, 5 seeds; positive in all 35 seed-pairs). Replicated at 20 seeds for XGBoost (+3.15 ± 0.12, 16.8%) and Random Forest (+2.75 ± 0.08, 14.6%). **Holds for the report's AoA impairment (independent 4° error + 5° quantization); see A1, A2.** |
| CIs ±0.13–0.85 m | **Supported, caveat** | That is the 1.96 interval. Student-t: ±0.18–1.20 m. |
| Overall 2.38–3.24 m (11.0–14.7%) | **Supported** | `verdict` block. |
| Replicated under mixed propagation (11–15%, multi 2.3–3.9 m) | **Supported** | 11.37–15.43%; multi +2.34 to +3.89 m. |
| Not a tuning artifact (XGBoost ≤ 0.44 m, RF < 0.07 m) | **Supported, caveat** | Exact. Quote the tuned-vs-tuned XGBoost gain (2.83 m against 2.92 m default) since that is the actual argument. Seed 42 only, tree models only. |
| Ranks 1–6 within 0.47 m, overlapping CIs | **Supported** | 0.465 m. On mixed data 0.36 m. |
| XGBoost trains in 4 s | **Supported** | 3.9 s. |
| Predicts 1000 positions in 1.7 ms | **Overstated** | One timing. The same script on the mixed dataset recorded 8.3 ms. Say "a few milliseconds". |
| "The tie holds a fortiori" | **Interpretation** | Test-set checkpoint selection favours the deep models, so "classical models are not worse" is conservative. It does not strengthen "deep models are not better". |

### C2. The gain comes from the angle channels, and it mainly fixes range error

| Bullet | Verdict | Notes |
|---|---|---|
| Header: "established for XGBoost, RF, k-NN; inferred for the neural models" | **Update** | Now established for 1D-CNN and GRU as well (A3). |
| Angle history alone matches or beats full history | **Supported** | 20 seeds, paired `full` − `angle_hist`: XGBoost +0.01 ± 0.06 m (uniform), −0.08 ± 0.04 m (mixed); Random Forest +0.31 ± 0.09 m (angle better), −0.02 ± 0.05 m. On mixed XGBoost full history is 0.08 m better, so "matches" (to within 0.1 m), not "beats", there. |
| RSS history gives at most +0.3 m; makes k-NN worse (−2.27 m) | **Supported, caveat** | Multi-antenna only. 20 seeds: XGBoost +0.23 ± 0.09 (uniform), +0.38 ± 0.07 (mixed); Random Forest −0.22 ± 0.11, +0.14 ± 0.04. Write "at most about +0.4 m". −2.27 m is uniform NLOS; on mixed k-NN is −0.48 m. |
| Radial 17.3 → 14.1 m, tangential 5.0 → 4.6 m | **Supported** | 20 seeds: 17.21 → 14.06 and 4.96 → 4.61 (XGBoost). Same for RF, CNN, GRU. |
| "A sequence of bearings constrains distance because the bearing turns more slowly with range (dθ/dt = v⊥/r)" | **Contradicted** | A1: order-free mean suffices; elevation, not bearing, carries it; no gain with exact AoA. |
| LOS advantage is in the angle channel | **Contradicted as a propagation claim** | A4. The individual numbers are correct, but the same gap exists with no LOS. |
| Range explanation for RSS history not supported | **Supported** | A8. |

### C3. Without an angle, history doesn't help at macro range

| Bullet | Verdict | Notes |
|---|---|---|
| Multi-antenna devices (~15 m) are range-limited; 90% of error variance radial | **Supported** | 20 seeds: radial share of squared error 92% at h=0, 90% at h=5 (XGBoost); RF 93% / 92%. |
| "About 5× better than the RSS-only bound σ_r ≈ 68 m" | **Overstated** | 67.94 m is right (`pathloss_fit_summary.json`), but it is a standard deviation compared with a mean absolute error. Radial RMS at h=5 is 17.5 m, so **about 4×**. Also call it a single-snapshot RSS ranging resolution, not a bound. |
| Single-antenna (~35 m): tangential 25.3 m > radial 20.1 m; history changes neither | **Supported** | 20 seeds: radial 21.0 → 21.1, tangential 25.2 → 25.3. |
| "Placed at about the right distance but the wrong bearing" | **Contradicted** | A5: radial error is larger than for multi-antenna devices (21 m vs 14 m), range correlation 0.51, radial bias −10 m. Say "error is dominated by the bearing component (about 60% of squared error) and the range component is also worse". |
| Single-antenna null on uniform NLOS, −1.39 to +0.32 m, XGBoost 0.06 ± 0.18 | **Supported, caveat** | Exact (5 seeds). At 20 seeds XGBoost −0.18 ± 0.34; Random Forest +0.42 ± 0.39, marginal. "No detectable gain; at most about 1%." |
| 5–10 single-antenna test users per split | **Supported** | 3–11 over the 20 seeds. |
| Supporting evidence: single-user 25×25, RF gets worse with history | **Contradicted (selective)** | Tech doc §7.4.3–7.4.4: RF 14.0 → 16.3 m and 13.8 → 17.3 m, **but XGBoost in the same tables, also without AoA, goes 29.2 → 13.4 m and 29.8 → 14.8 m**. Single-user, single-seed, no JSON of record. Drop the bullet or show both models. |
| Open exception on mixed data, ~1.5 m | **Supported; now partly explained** | A6. Replace "unexplained" and the "one-split lead" sentence with the A6 result. |

### Supporting: the controlled grid

Source: `technical_documentation.md` §7.1–7.3 only; there is no JSON of record. Single seed.

| Bullet | Verdict |
|---|---|
| History helps without AoA at short range in every configuration; RF +8.5 pp centre, +5.9 pp corner | **Supported** (XGBoost +22.4 / +28.8 pp; grid sweep +9.2 to +21.8 pp) |
| Corner BS removes almost all of AoA's added value (XGBoost +31.4 → +2.3 pp) | **Supported** (RF +25.7 → +1.7 pp) |

Open question raised by Part A: the controlled-grid gain without AoA may be the same averaging effect applied to RSS/SINR. It was not tested.

### Take-aways

| # | Verdict | Corrected statement |
|---|---|---|
| 1 | **Contradicted in part** | "Helps every family" ✔. "Only for devices that report an angle" fails on mixed data for the tree models (A6). |
| 2 | **Contradicted in part** | "What that buys is better range estimates" ✔. "What history reads is how the bearing moves" ✘: it averages angle measurement error, mainly elevation (A1). |
| 3 | **Supported** | ~19 m overall; ~15–16 m and ~35–37 m by group. |
| 4 | **Supported, caveat** | 14–20% for the tree models, multi-antenna (A9). Untested for the deep models. |
| 5 | **Supported, re-scoped** | Multi-antenna gain 30–41% at every width; no rise-and-fall. But the gain is equal outside the blocked stretch, single-antenna devices gain nothing, and it is azimuth averaging (A7). The corridor is not evidence about blockage. |

### Mechanism diagnostic

| Item | Verdict | Notes |
|---|---|---|
| "Predictions fixed on 2026-10-04 before the diagnostic ran" | **Not verifiable here** | Nothing in the repository records P1–P3 before 2026-10-07. Keep the dated original. |
| P1 confirmed | **Supported** | A1, A3. The "and/or `ray_hist`" branch did not occur (ray history +0.25 / −0.01 m). |
| P2 confirmed on uniform NLOS, fails on mixed | **Supported** | A5, A6. |
| P3 not supported | **Supported at 20 seeds**, with one correction | A8. Delete "the single-antenna RSS-only gain *rises* with range (+0.4 → +2.4 m)": not replicated. |
| "History mainly reduces radial error" | **Supported** | |
| "h=0 baseline … worth 0.4–0.5 m" | **Supported** | 0.37–0.56 m (A9). |
| "Angle-only gain ~10 m below 40 m … rises to 5.5 m beyond 120 m; unexplained" | **Supported; now explained** | A8, last bullet. |

### Fidelity notes

| Note | Verdict |
|---|---|
| Macro-cell AoA impairment is 4° Gaussian + 5° quantization | **Supported** (`utils/csi_dataset.py`). **Add:** the error is drawn independently per sample, and the history gain depends on that (A2). This is now the most important fidelity note in the report. |
| "h=0" is the current measurement plus first differences | **Supported** |
| Deep models early-stop on test MAE | **Supported** |
| Controlled grid single-seed; configurations 2–3 pp apart | First half **Supported**; "2–3 pp" not traced |
| "Error grows with range" not shown by per-group data | **Supported, caveat**: not for multi-antenna devices (22.5, 21.3, 14.4, 28.2 m at h=0); single-antenna error does rise above 40 m |
| Mixed-dataset per-region path-loss fits unstable (γ = 6.9) | **Supported** (Residential γ = 6.92; pooled LOS 2.58, NLOS 3.60) |

### Setup facts and figure captions

| Statement | Verdict |
|---|---|
| 15×15 at 3.5 GHz; sweeps and macro cell at 3.0 GHz; 25×25 at 4 m spacing | **Supported** (configs) |
| 28 m grid, 96 m macro cell, 21–157 m from the BS | **Supported** |
| Macro interferers [−60, 53], [53, −60] hard-coded; config values not read | **Supported** (`run_multi_user_300_25x25.m`) |
| Users 250 and 27 "chosen by rule" | **Supported**: median single- and multi-antenna test users by h=5 XGBoost error, seed 42. State the rule in the caption. |
| `fig_error_cdf`: "the two error populations barely overlap" | **Contradicted.** Histogram overlap is 63% at h=0 and 52% at h=5 (XGBoost, seed 42). Say "clearly separated medians (17 m vs 31 m)". |
| `fig_history_gain_ci`: every multi CI above zero, every single CI crosses zero | **Supported** on uniform NLOS only |
| `fig_los_nlos_channels` | Numbers correct; must be shown beside the uniform-NLOS control or dropped (A4) |

---

## Part C. Claims the report can make as they now stand

1. **History lowers multi-antenna error by 2.8–4.1 m (15–21%) in all seven model families** on uniform NLOS, and by 2.3–3.9 m under mixed propagation, with five steps (20 m) of history, under the report's AoA impairment model. Model family barely matters.
2. **The gain comes entirely from the angle channels** in XGBoost, Random Forest, k-NN, the 1D-CNN and the GRU. RSS history adds at most about 0.4 m.
3. **The gain is the averaging of angle measurement error.** An order-free mean of the window recovers all of it, elevation carries more than 80% of it, and with exact AoA it is zero. Because elevation maps to range, it appears as lower range error (radial 17.2 → 14.1 m; tangential 5.0 → 4.6 m).
4. **Its size depends on the error model:** about 17% when the AoA error is independent between reports, about 6% when the error persists across the window. The persistent part comes from the user's motion across quantization steps.
5. **Without an angle there is no detectable gain on uniform NLOS** (XGBoost −0.2 ± 0.3 m; at most about 1% for any model).
6. **Under mixed propagation the tree models do gain about 1.3 m for single-antenna devices** (20/20 seeds). A single-antenna snapshot cannot tell LOS from NLOS; an oracle flag is worth about 3 m, and RSS history recovers part of that and adds most where the window crosses a boundary.
7. **LOS propagation does not change the multi-antenna history gain.** Regional differences are range and geometry.
8. **The two device groups fail differently:** multi-antenna error is 90% radial; single-antenna error is about 60% tangential with a worse radial component as well.
9. **The blocked-LOS corridor shows a 30–41% multi-antenna gain at every strip width, the same outside the blocked stretch,** and nothing for single-antenna devices.
10. **The stored "no history" input already contains one step of change,** worth 0.4–0.6 m (14–20% of the gain) for the tree models.

## Part D. What remains open or unverifiable

- **How correlated real AoA errors are.** The report's headline sits between the ρ = 0 and ρ ≈ 1 rows of A2, and nothing here says where. This is the main limitation to state.
- **CNN+attention and the mask-aware CNN** were not run through the channel test.
- **The single-antenna mixed-data mechanism** (A6) is supported by an oracle experiment, not by a direct test that the model infers the state.
- **The controlled grid** has no results of record, and whether its no-AoA history gain is also measurement averaging was not tested.
- **Not in this repository:** `Project Report 2/`, `main.tex`, the figure scripts, section status, the exhibits sourced from `FINDINGS.md` and `analysis/regression_vs_classification.md`, and the 2026-10-04 date of the predictions.
