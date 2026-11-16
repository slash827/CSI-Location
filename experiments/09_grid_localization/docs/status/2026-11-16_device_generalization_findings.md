# Device generalization: findings for Dudi's three questions (2026-11-16)

This note answers the three questions Dudi raised about the single-BS localization work:
(a) whether to use absolute values, differences between reports, or both;
(b) how the models generalize to devices they have not seen;
(c) how performance changes as devices become more heterogeneous.

All numbers are mean position errors in metres on users that were not seen in training. They
come from `docs/results_of_record/device_generalization_2026_11/` (see `MANIFEST.md` there for
the arms and how to reproduce them).

## Setup in brief

- **Data.** A simulated macro cell with one base station and 300 users in four device classes:
  mid-tier phones (4 antenna elements), flagship phones and vehicles (16), and IoT devices (1).
  The classes differ in height, antenna gain, noise figure and speed.
- **Shared environment.** All users see the same large-scale channel maps. The small-scale
  fading is still drawn separately, so the environment is only partly shared. Three such
  environments exist: two with mixed LOS/NLOS regions and one with uniform NLOS.
- **Inputs.** RSS and SINR only; no angle of arrival unless stated. Four representations of the
  last h + 1 reports: a single report (h = 0), the levels as received, the differences between
  consecutive reports, and both together.
- **Models.** A GRU (one layer) and XGBoost. Five splits of the users, 80 % for training.
- **Device offset.** A constant offset in dB, drawn per test device and added to its RSS, with a
  standard deviation from 0 to 20 dB.

## The condition that comes first: a shared environment

Differences between reports only help when users share an environment. In our older data, every
user was simulated as a separate channel realization, and there the differences made the error
worse than a single report (by 2 to 4 m). In the mixed shared environments, with the GRU, they
lower it by 4 to 7 m.
The same holds for history in general under uniform NLOS: no gain with separate realizations,
5 to 10 m for multi-antenna devices in a shared environment. A real deployment is a shared
environment, so the shared results are the relevant ones, but this dependence on the simulation
is itself a finding and is now in the report (Section VII, "A Shared Environment").

## (a) Absolute values, differences, or both?

It depends on whether the devices are known and calibrated.

All device classes in training, h = 5, GRU, first mixed environment:

| Offset std | Single report | Levels | Differences | Both |
|---|---|---|---|---|
| 0 dB | 30.0 | 25.0 | 23.4 | 21.2 |
| 6 dB | 31.7 | 27.7 | 23.4 | 23.6 |
| 10 dB | 33.3 | 29.7 | 23.4 | 24.9 |
| 20 dB | 43.5 | 38.4 | 23.4 | 33.5 |

- With calibrated devices of known classes, both together are best (21.2 m against 30.0 m for a
  single report).
- Differences are unaffected by a constant offset, by construction. Above an offset of about
  6 dB they are the best input.
- Levels alone are never the best choice.

The second mixed environment gives the same picture (0 dB: 30.5, 24.5, 24.2, 21.9 m; 20 dB:
44.8, 41.0, 24.2, 34.6 m).

## (b) Generalization to unseen devices

The GRU was trained on phones only (flagship and mid-tier) and tested on all four classes, so
IoT devices and vehicles are classes it never saw. No offset, first mixed environment:

| History | Class | Single report | Levels | Differences | Both |
|---|---|---|---|---|---|
| h = 5 | IoT (unseen) | 37.5 | 35.7 | 27.0 | 32.4 |
| h = 5 | Vehicle (unseen) | 34.0 | 31.2 | 24.6 | 27.7 |
| h = 20 | IoT (unseen) | 37.5 | 33.4 | 20.2 | 30.5 |
| h = 20 | Vehicle (unseen) | 34.0 | 28.4 | 18.4 | 24.2 |
| h = 20 | Flagship (trained) | 28.2 | 22.5 | 21.5 | 20.6 |
| h = 20 | Mid-tier (trained) | 28.7 | 20.5 | 19.3 | 19.0 |

- Differences transfer to unseen device classes; levels do not. At h = 20, an unseen IoT device
  is located as well with differences (20.2 m) as a phone the model was trained on (19 to 22 m).
- Longer history helps the differences most: for IoT, 27.0 m at h = 5, 22.7 m at h = 10 and
  20.2 m at h = 20.
- On the trained classes, the three representations are within about 3 m of each other.
- The second mixed environment agrees (h = 20, IoT: 21.1 m with differences against 28.7 m with
  levels; vehicle: 20.3 m against 30.1 m).

## (c) Growing heterogeneity

The table in (a) is the answer for known classes: levels and both degrade steadily as the
offset grows, while differences stay flat. For unseen classes the effect is stronger. With the
GRU trained on phones only, h = 20, and a 20 dB offset, IoT devices are at 44.2 m with levels,
39.6 m with both and 20.2 m with differences.

Variety in training also matters. With the training set held at 55 users and device classes
added one at a time, levels and both improve once the test class is among the training classes,
while differences stay about the same throughout. Differences need more training data than
levels: at 55 training users they are worse than levels on the trained classes.

## Limits of these results

- **Simulation only, partly shared environment.** The small-scale fading is not shared between
  users. A fully shared environment has not been tested.
- **A sequence model is needed.** With XGBoost, differences are about as good as a single
  report (30 to 32 m); the gains above are for the GRU.
- **Smaller advantage under uniform NLOS at zero offset.** There, at h = 20, unseen IoT devices
  are at 23.8 m with differences, 26.1 m with levels and 22.5 m with both. The robustness to
  offsets is unchanged (levels rise to 35.2 m at 20 dB, differences stay at 23.8 m).
- **Offsets are constant per device.** A slowly drifting offset (0.1 dB per report) and 2 dB
  quantization were also tested and do not change the picture; fast-varying gain was not tested.
- **With an angle of arrival.** A model trained only on multi-antenna devices fails on
  single-antenna devices, whose angle is missing (51 to 69 m). Removing the angle for 30 % of
  the training users fixes this (30 to 38 m) at a cost of about 1.5 m for multi-antenna users.

## Recommendation

Give the model both levels and differences, use a sequence model with a history of 10 to 20
reports, and train on as many device classes as possible. When the device population is unknown
or poorly calibrated (offsets above about 6 dB, or classes absent from training), rely on the
differences alone.
