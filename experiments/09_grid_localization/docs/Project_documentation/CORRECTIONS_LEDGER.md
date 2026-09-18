# Corrections ledger

Claims that were once in this project's documents and have since been **measured and
withdrawn**, with what replaced them and how to avoid reintroducing them.

This file exists because the withdrawn numbers are still sitting in
`results_of_record/` and in older Google Doc snapshots. Every one of them is a
plausible, quotable figure. Without this list, the natural thing for a new session to
do is find `master_benchmark_summary.json`, read `18.518 m` next to `gru_h5`, and
write "the GRU performs best" again.

**Rule of thumb for this project:** a difference below roughly **0.5 m** overall, or
below roughly **5 m** in any single-antenna figure, is not a result. See §5.7 of
`FINAL_REPORT.md` for the measured noise floor.

---

## 1. "The GRU is the best model" — withdrawn

**Was:** GRU best overall at $18.518\,\text{m}$, explained by recurrent gates
extracting motion derivatives that axis-aligned tree splits cannot express.

**Now:** Re-running the scorecard under the current pipeline puts GRU at
$19.355\,\text{m}$, **fifth of six**. The five-seed repeat puts it fourth inside a
six-way statistical tie: the six $h=5$ models span $0.74\,\text{m}$ against a
$1.85\,\text{m}$ marginal seed spread, and every adjacent pair has overlapping 95%
intervals.

**Replacement claim:** no architecture wins. Given history, a convolution, a boosted
tree ensemble and a recurrent network are indistinguishable on this task.

**Source:** `ablations_2026_09/master_benchmark_rerun_summary.json`,
`ablations_2026_09/seed_repeats_all_models_summary.json`.

---

## 2. "Random Forest is the outlier whose single-antenna error is worse than the baseline" — withdrawn

**Was:** RF single-antenna error $38.904\,\text{m}$ exceeds the $h=0$ $k$-NN
baseline's $37.142\,\text{m}$; inferred that axis-aligned splits fragment the temporal
signal.

**Now:** Both were single-seed estimates of the noisiest quantity in the study. Across
five seeds RF is $36.27 \pm 2.35\,\text{m}$ and the baseline is
$46.17 \pm 3.13\,\text{m}$ — **RF leads the baseline by about 10 m** on that cohort.
The re-run confirms it directly: RF's single-antenna error is $33.069\,\text{m}$ at
seed 42, reproduced identically by three independent scripts (B2, B3, B5).

**Replacement claim:** RF is the expensive way to reach the same place —
$2.25$ M tree nodes and $60\times$ XGBoost's inference cost for a statistically
identical MAE.

---

## 3. "Fixed-window estimators turn; tree ensembles do not" — withdrawn

**Was:** the 1D-CNN rises from $19.260\,\text{m}$ at $h=5$ to $20.215\,\text{m}$ at
$h=10$, so convolutions degrade past their optimum while trees plateau.

**Now:** the single-protocol sweep puts the same architecture at $19.268$ and
$19.146\,\text{m}$ — it does not turn. The two runs agree at $h=5$ and differ by
$1.07\,\text{m}$ at $h=10$, about twice the seed-paired CI. Deep-model training is
stochastic and one run at one depth was never enough to establish a turn.

**Replacement claim:** only $k$-NN turns within the swept range, and it is the one
deterministic estimator in the set. Six of seven families are still improving at
$h=10$. The architectural explanation survives only as a hypothesis.

---

## 4. "The LOS/NLOS prediction is confirmed" — withdrawn, and untestable on this data

**Was:** history is worth $+15.98\%$ in LOS against $+4.84\%$ in NLOS, a $3.3\times$
difference confirming that the gain is largest where the distance-ring ambiguity is
worst.

**Now:** Campaign B contains **no LOS**. See `MATLAB_RERUN_RUNBOOK.md` §1 for the full
diagnosis. The four "zones" are geometric regions of a uniformly NLOS map.

**Replacement claim:** the prediction is untested. The measured per-region gains
($+4.38\%$ to $+18.75\%$) are real but isolate a purely *geometric* contribution, with
propagation held constant by accident.

**Do not** reintroduce the supporting argument that "the range confound points the
wrong way because the LOS stratum has shorter mean range." With propagation uniform,
range and geometry were the only things varying, so that argument attributed a
geometric difference to physics that was never simulated.

---

## 5. "$h=5$ is the universal optimum" and "$h=5 \approx 2.5\,\text{s}$" — both withdrawn

**Was:** a sweet spot at $h=5$, glossed as about 2.5 seconds of history.

**Now:** two separate corrections.

* The optimum is $h=10$ or beyond for six of seven families (§5.4).
* The window is **spatial, not temporal** (§5.8). Per-speed-class optimal durations
  span $1.6\,\text{s}$ to $134.7\,\text{s}$, so the optimum is not a fixed time. Since
  every walk step advances exactly one grid cell, $h=5$ is $20\,\text{m}$ of path and
  $h=10$ is $40\,\text{m}$, for every user regardless of speed.

**Replacement gloss:** convert depth to *distance*, never to time.

---

## 6. "Smoothing degrades every model by 28–48%" — withdrawn, it was a bug

**Was:** RTS smoothing hurts every model badly, recorded in the master benchmark.

**Now:** `DerivedCSI1DDataset` standardises `SIGNAL_COLS` in place and `delta_t` is
one of them, so the smoother received z-scores rather than seconds — 85.8% of values
were negative and clamped to $0.01\,\text{s}$ by `max(0.01, dt)`, destroying the state
transition. Fixed in commit `dee50dd`.

**Replacement claim:** properly configured, smoothing is worth $+2.5\%$ to $+4.7\%$.
**But the gain is entirely non-causal** — it comes from the RTS backward pass. The
forward Kalman filter alone, at the same tuned $Q,R$, *degrades* the 1D-CNN by
$3.4\%$. Smoothing is available to latency-tolerant applications only; transition
history is fully causal.

**Still invalid and must not be cited:** every `rts_*` field in
`campaign_b/master_benchmark_summary.json`, and the `rts_retune` block in
`ablations_2026_09/knn_sweep_rts_retune_summary.json`.

---

## 7. "Boundary crossings cost +1.45 m" — withdrawn (inverted sign)

**Was:** crossing a Voronoi boundary carries a $+1.45\,\text{m}$ penalty.

**Now:** within-cell $19.34\,\text{m}$ vs crossing $18.33\,\text{m}$ — crossings are
marginally *easier*, by $1.00\,\text{m}$. QuaDRiGa's spatial consistency prevents
transient discontinuities.

---

## 8. "Random walk at 1.5 m/s" — withdrawn (wrong mobility description)

**Was:** Campaign B users follow a random walk at $1.5\,\text{m/s}$.

**Now:** four heading-persistent patterns (billiards, momentum walk, waypoint tour,
straight transit) with speeds spanning $0.12$ to $14.89\,\text{m/s}$. This matters
because a true random walk would be *adversarial* to history, so the old description
undersold the result and misdescribed the data.

---

## 9. Figure 2 mixed three experiments — fixed

**Was:** `universal_delta_mae_history_curves.png` plotted four hardcoded curves. Only
the 1D-CNN curve was Campaign B; XGBoost and Random Forest came from the July
200-user sweeps; and the GRU curve came from a **single-user** exploration with a
*chronological* split, 3D MAE and raw AoA angles. A chronological split within one
walk interleaves test samples between training samples, which is why that curve read
$8.5\,\text{m}$ and a $-50\%$ gain where the disjoint-user protocol gives
$18.5\,\text{m}$.

**Now:** the figure is generated from
`ablations_2026_09/history_sweep_all_models_summary.json` — all seven families, one
protocol. `plotting/plot_unified_delta_mae.py` reads that JSON, so the hardcoded
curves cannot return.

---

## 10. `master_benchmark_summary.json` has drifted generally

Beyond the specific rows above: five of seven models reproduce within $0.6\,\text{m}$,
but Random Forest is $1.47\,\text{m}$ off overall and $5.84\,\text{m}$ off on
single-antenna, and the $k$-NN baseline's single-antenna figure is $5.07\,\text{m}$
off. The file predates several pipeline changes and there was no script in the repo
that regenerated it — it came from a notebook, which is why it drifted.

**Cite `ablations_2026_09/master_benchmark_rerun_summary.json` for §6 instead.**
`master_benchmark_rerun.py` now exists so this cannot recur silently.

---

## Recurring process failures worth knowing about

These cost real time on the old machine.

* **Non-raw Python strings containing `\text`** — `\t` becomes a tab, the assertion
  fires, and because the exception precedes the file write, **every earlier edit in
  the same script is silently discarded**. This bit more than once, and twice the
  loss went unnoticed for hours. Use the `Edit` tool, or raw strings, and always
  assert before writing.
* **PowerShell here-strings (`@'...'@`) in the Bash tool** — produced a commit whose
  subject was literally `@`. Use heredocs with quoted delimiters.
* **`s.replace()` without asserting the pattern matched** — silently no-ops. One
  suptitle edit was lost this way and only caught by looking at the rendered figure.
* **Windows `MAX_PATH`** — `Compress-Archive` fails on long scratchpad paths. Build
  archives somewhere short.
* **Git over an intercepting TLS proxy** — `unable to get local issuer certificate`
  while `curl` returns 200. Fix with
  `git config --local http.sslBackend schannel`. Do **not** disable verification.
* **Deep-model per-user MAE is not stable across runs** — the same configuration gave
  user 119 raw MAE of 9.97, 12.08 and 10.29 m on three runs. Population MAE is stable
  to about $0.2\,\text{m}$. Quote population figures; treat per-user numbers as
  illustrative.
