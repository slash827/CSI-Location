# Overleaf edits — separate channel realizations and the shared environment (2026-11-15)

Edits to Alon's Overleaf report, *Channel History for Single-BS 5G Localization* (PDF of
2026-11-07, `Simulation-Nov-2026/Transition_History .pdf`). Page and section numbers refer to
that PDF.

**How to use this file.** Each edit has:

- **Where**: section and page in the PDF.
- **Find**: a phrase to search for in the Overleaf source (Ctrl+F). It is copied from the PDF, so
  line breaks and hyphenation may differ in the source.
- **Replace with** or **Insert**: the LaTeX to paste. Only the content of the grey `latex` boxes
  goes into Overleaf; everything outside the boxes is explanation.

Marks inside the LaTeX:

- `% CHECK:` lines are notes for us and can stay (they are LaTeX comments); delete them once
  checked.
- `\ref{...}` labels are guesses; adjust them to the labels in the Overleaf source.

Numbers come from `docs/results_of_record/device_generalization_2026_11/` (the arms
`macro_mixed`, `macro_mixed_gru`, `shared`, `shared_gru`, and the `*_class_gru_h20` arms for the
two environments).

---

## What changed since the 2026-11-07 PDF, and how strong the evidence is

The report already says that every user in the simulation has its own channel realization
(Section VII-B). The edits below add two things:

1. **The macro cell has the same property.** Its test users are unseen, but their RSS map is also
   separate, so only the angle, which follows the geometry, can carry over between users. The
   current text reads as if the full channel transfers.
2. **A shared-environment check now exists.** Two macro-geometry datasets simulate all users in
   one environment (`run_shared_env_devices.m`). In them, history helps unseen users more,
   single-antenna devices included, and only there do differences between reports help at all.

The evidence does **not** show that the uniform-NLOS result of Section VII ("history adds
nothing for single-antenna devices") is only an artifact. The shared environment uses mixed
LOS/NLOS propagation, the setting where the report already finds a single-antenna gain
(Section VII-C). The same script on the old per-user mixed data already gives single-antenna
devices a gain of about 3 m. So the edits soften that claim and state the open question; they do
not reverse it. A shared environment with uniform NLOS would settle it.

---

## Edit 1 — Introduction, end of the paragraph after Section I-A (p. 4)

**Find:** `where one report carries nothing that transfers to new users`

The current sentence:

> The gain depends on the position information a single report carries: where one report carries
> nothing that transfers to new users, as for single-antenna devices in the macro cell, history
> adds nothing.

**Replace with:**

```latex
The gain depends on the position information a single report carries and on whether that
information is shared between users: where one report carries nothing that transfers to new
users, as for single-antenna devices in the uniform-NLOS macro cell, whose users are each
simulated as a separate channel realization, history adds nothing, whereas in a simulated
environment shared by all users, history lowers the error of unseen users of both device groups.
```

---

## Edit 2 — Contribution (iv), Section I-B (p. 4)

**Find:** `(iv) a delimitation of where history adds nothing`

The current text:

> (iv) a delimitation of where history adds nothing, namely where a single report carries no
> position information that transfers between users.

**Replace with:**

```latex
(iv) a delimitation of where history adds nothing, namely where a single report carries no
position information that transfers between users, together with a test showing that this
depends on the simulation: when all users share one simulated environment, history lowers the
error of unseen users, and differences between consecutive reports become informative.
```

---

## Edit 3 — Channel simulation, Section III-A (p. 8)

**Find:** `This work extends a time-aware multi-user massive multiple`

**Insert after** the sentence that ends `...that is described in Section III-D.`:

```latex
% CHECK: confirm that our generator descends from [16]; if it does not, change "extends" above.
Unlike~[16], which draws a new channel layout for every report, each user's walk is simulated
here as one continuous QuaDRiGa track, so that consecutive reports of a user are spatially
consistent samples of the same channel. Each user, or each segment of a user's walk, is
nevertheless simulated as a separate channel realization unless stated otherwise; the
consequences of this choice are examined in Sections~\ref{sec:unseen-users}
and~\ref{sec:shared-env}.
```

*Note for us:* the first sentence matters because the sample logs of the Omri simulator show
almost no correlation between consecutive reports (lag-1 correlation 0.03–0.11). If Alon prefers
not to criticize [16] in the report, keep only the second and third sentences.

---

## Edit 4 — Evaluation protocol, Section III-G (p. 10)

**Find:** `the 47 test users of each split are never seen during training`

**Insert after** the sentence that ends `...for multi-antenna and single-antenna devices.`:

```latex
Because each macro-cell user is also simulated as a separate channel realization, an unseen
user's RSS map is not one the model could have learned from other users; what transfers between
users is the geometry, chiefly the angle of arrival, and the propagation state of the region the
user is in.
```

---

## Edit 5 — Unseen Users, Section VII-B (p. 21), last sentence

**Find:** `make this contrast sharper than it would be in practice`

The current sentence:

> In a real deployment, co-located users share the large-scale shadowing, so the separate channel
> realizations of the simulation make this contrast sharper than it would be in practice.

**Replace with:**

```latex
In a real deployment, co-located users share the large-scale shadowing, so the separate channel
realizations of the simulation make this contrast sharper than it would be in practice;
Section~\ref{sec:shared-env} tests this with an environment shared by all users.
```

---

## Edit 6 — New subsection at the end of Section VII (after VII-C, before Section VIII)

**Insert** (new subsection with one table):

```latex
\subsection{A Shared Environment}
\label{sec:shared-env}

To test how much of the macro-cell result is due to simulating every user as a separate channel
realization, we generated two further macro-cell datasets in which all users share one
environment. They use the geometry and the mixed LOS/NLOS regions of the macro cell, with
300~users each in four device classes: mid-tier phones with four antenna elements, flagship
phones and vehicles with sixteen, and single-antenna IoT devices, which differ in carrying
height, antenna gain, noise figure and speed. The random generator of the channel simulation is
reset to a common seed before every segment of every walk, so that all users see the same
large-scale parameter maps; the small-scale fading is still drawn per segment, so the
environment is only partly shared. At the same grid point, the median difference in received
power between two users is \SI{5.1}{dB}, against \SI{6.7}{dB} with separate realizations. No
angle is used in this comparison, and no static device attributes are given to the models.

Table~\ref{tab:shared-env} compares the history gain on unseen users (five user splits, 80/20)
with separate realizations and in the shared environment, for XGBoost and a gated recurrent
unit~(GRU) given the last $h=5$ reports. With separate realizations, history lowers the error of
both device groups by about \SI{2}{} to \SI{3}{m}, the single-antenna gain under mixed propagation
of Section~VII-C, and the differences between consecutive reports make the error worse than a
single report. In the shared environment, the gain of XGBoost grows by 0.6 to \SI{2.2}{m}, while that of the
GRU grows to \SI{7.2}{m} for single-antenna devices and \SI{9.0}{m} for multi-antenna devices,
and the differences between reports now lower the error as well. With $h=20$ and the GRU trained
on phones only, the differences alone bring single-antenna IoT devices, a class not seen in
training, from 37.5 and \SI{35.1}{m} to 20.2 and \SI{21.1}{m} in the two environments.

A shared map therefore lets history, and above all the change between reports, carry over to
new users. Because both shared datasets use mixed propagation, this does not establish whether
the uniform-NLOS result of Section~VII, where history adds nothing for single-antenna devices,
would also change in a shared environment.

\begin{table}[h]
  \centering
  \caption{History gain on unseen users with separate channel realizations and in a shared
  environment (macro-cell geometry, mixed LOS/NLOS, no angle). Error of a single report ($h=0$)
  and its reduction by a window of $h=5$ reports, in metres; seed-paired means over five user
  splits with 95\,\% Student-t intervals. Levels: the reports as received; differences: the
  change between consecutive reports; both: the two together.}
  \label{tab:shared-env}
  \begin{tabular}{@{}lllrrrr@{}}
    \toprule
    Environment & Model & Devices & $h=0$ & Levels & Differences & Both \\
    \midrule
    Separate & XGBoost & Multi-antenna  & 29.4 & $2.3 \pm 0.6$ & $-3.3 \pm 0.4$ & $2.4 \pm 0.6$ \\
             &         & Single-antenna & 28.7 & $2.6 \pm 0.5$ & $-2.9 \pm 1.3$ & $2.9 \pm 0.6$ \\
             & GRU     & Multi-antenna  & 28.3 & $1.8 \pm 0.3$ & $-3.6 \pm 0.6$ & $2.1 \pm 0.8$ \\
             &         & Single-antenna & 27.8 & $2.3 \pm 0.7$ & $-2.7 \pm 1.3$ & $2.9 \pm 0.6$ \\
    \midrule
    Shared   & XGBoost & Multi-antenna  & 30.6 & $3.9 \pm 0.4$ & $-0.3 \pm 0.5$ & $4.6 \pm 0.4$ \\
             &         & Single-antenna & 32.1 & $2.8 \pm 1.1$ & $-0.2 \pm 1.4$ & $3.5 \pm 0.8$ \\
             & GRU     & Multi-antenna  & 29.8 & $5.2 \pm 0.7$ & $6.8 \pm 1.9$  & $9.0 \pm 1.3$ \\
             &         & Single-antenna & 32.1 & $3.6 \pm 1.1$ & $5.4 \pm 3.7$  & $7.2 \pm 2.0$ \\
    \bottomrule
  \end{tabular}
\end{table}
```

*Notes for us:*

- **Two datasets differ in more than the shared map.** The device models differ: the old data
  has antenna counts of 1, 2 and 4 with a gain drawn from −4 to +2 dB; the new data has the four
  classes above.
  Single-antenna devices are 15 % of users in both. Say so if a reviewer asks; the table caption
  does not claim the device sets are equal.
- **Seed 1 only.** The table uses the first shared environment only, because the arms with all
  classes in training were not repeated on the second. The $h=20$ sentence uses both. A repeat
  on seed 2 takes about 15 minutes, if we want both in the table.
- **Device generalization.** The results on unseen device classes and device offsets (Dudi's
  questions) are not in this subsection; they belong in the section we add for them.

---

## Edit 7 — Limitations, "Known maps" paragraph, Section VIII (p. 22)

**Find:** `Transfer to new users is tested in the macro cell, and a grid simulated`

The current sentence:

> Transfer to new users is tested in the macro cell, and a grid simulated as one environment
> shared by all users would extend that test to the controlled setting.

**Replace with:**

```latex
Transfer to new users is tested in the macro cell, where it rests on the geometry, chiefly the
angle, since each user's RSS map is simulated separately. A partly shared environment, in which
all users share the large-scale maps but not the small-scale fading, enlarges the history gain
on unseen users (Section~\ref{sec:shared-env}); a fully shared environment, and the same test on
the controlled grid and under uniform NLOS, remain to be done.
```

---

## Edit 8 — Conclusion, Section IX (p. 22–23)

### 8a. Last sentence of the first paragraph

**Find:** `whose reports carry nothing that transfers to new users, gain no more than about`

The current sentence:

> Finally, the gain depends on the position information a single report carries: single-antenna
> devices in the macro cell, whose reports carry nothing that transfers to new users, gain no
> more than about 1 %, while the grid's gain without an angle rests on a channel map learned for
> each user.

**Replace with:**

```latex
Finally, the gain depends on the position information a single report carries and on whether
it is shared between users: single-antenna devices in the uniform-NLOS macro cell, whose reports
carry nothing that transfers to new users, gain no more than about 1\,\%, and the grid's gain
without an angle rests on a channel map learned for each user, whereas in an environment shared
by all users, history lowers the error of unseen single-antenna devices by about \SI{7}{m}.
```

### 8b. Last follow-up of the second paragraph

**Find:** `Finally, a controlled grid simulated as one environment shared by all users would test`

The current sentence:

> Finally, a controlled grid simulated as one environment shared by all users would test whether
> the within-user gain carries over to new users.

**Replace with:**

```latex
Finally, a fully shared environment, on the controlled grid and under uniform NLOS, would test
whether the within-user gain carries over to new users there as it does, in part, in the
partly shared macro-cell environment.
```

---

## Not changed

- **Section VII-C** (single-antenna devices under mixed propagation) stays. The gain there
  follows the propagation state of the region, which is geometric and therefore shared between
  users even with separate realizations.
- **Controlled grid and 25 × 25 results** stay. Section VII-B already labels them within-user.
- **Abstract:** the PDF of 2026-11-07 has none. If the Overleaf source has one, apply Edit 1 to
  it too.
