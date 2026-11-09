# Simulation-Nov-2026

Material received from Alon on 2026-11-07.

| Path | What it is |
| :--- | :--- |
| `Transition_History .pdf` | Alon's Overleaf report as downloaded on 2026-11-07. The Overleaf project is now the master copy of the report; `docs/paper/Transition_History/` in this repository is out of date. |
| `omri_simulator_not_for_claims/` | Output, configuration and report of Omri's QuaDRiGa simulator (Alon's branch `heterogeneous-ue-device-classes`, local clone `C:\Git\temporary_omri_simulator`). |

## Do not use `omri_simulator_not_for_claims/` for any claim

Kept for provenance and for comparison only. No number in the report or in
`docs/results_of_record/` comes from it. The simulator has two flaws that each, on their own,
decide the questions this project asks:

1. **A new environment for every user.** Each user gets their own channel realization, so there
   is no common map that a model could learn from other users. Any test on unseen users or
   unseen devices then fails because of the simulation, not because of the method. Alon found
   this in November 2026.
2. **A new layout for every report.** The simulator builds a new `qd_layout` for every 0.5 s
   report, so consecutive reports are independent draws. With the distance trend removed, the
   lag-1 autocorrelation of RSRP in the three sample logs is 0.03 (IoT device moving 5 cm per
   report), 0.03 and 0.11, and the spread of the report-to-report difference (5.8–6.7 dB) is
   larger than the spread of the level itself (4.4–4.8 dB). History and differences can then
   carry only noise. Check it with:

   ```bash
   .venv/Scripts/python experiments/09_grid_localization/src/python/utils/alon_csv_loader.py \
       --csv-dir experiments/09_grid_localization/Simulation-Nov-2026/omri_simulator_not_for_claims
   ```

Other properties to keep in mind when reading its output: no AoA output; RSRP is the transmit
power plus the mean path gain, so the antenna count of a device does not change it; the noise
figure enters only the SINR, as a constant offset; RSRP is clipped to [−120, −40] dBm and SINR
to [−5, 30] dB.

The older 100-UE logs in `../Alon_scripts/UE Log CSVs/` have the same format without the
`device_class` column. They appear to come from an earlier version of the same simulator. Their
lag-1 autocorrelation is higher (median 0.48, range −0.08 to 0.81, steps of 0.4–1.0 m), but the
report-to-report difference is still about as large as the level (median std 5.9 dB against
6.2 dB), so the same caution applies.

## What the device experiments use instead

`src/matlab/runners/run_shared_env_devices.m` generates a shared environment: every walk is one
continuous track (temporal consistency inside a walk), and the random generator is reset before
each segment so that all users see the same large-scale map. Small-scale fading is still drawn
per segment, so the environment is only partly shared: at the same grid point, the median
difference in received power between users is 5.1 dB, against 6.7 dB in the older per-user
data. Two such environments (shared seeds 20261107 and 20261108) back the results in
`docs/results_of_record/device_generalization_2026_11/`.

Our own older 300-user macro data (`sim_data_300users_mixed_*`) also has one environment per
user (flaw 1, not flaw 2). Results on it with the temporal split (the same users in training and
test) stand but are optimistic, since the model can learn each user's own map; results on
unseen users are not valid evidence about the method (see the leave-one-user-out test).
