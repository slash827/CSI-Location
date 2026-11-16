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
`macro_mixed*`, `macro_uniform*`, `shared`, `shared_gru`, `seed2_shared*`, `shared_uniform*`, and
the `*_class_gru_h20` arms). The full table with the reproduction notes is in
`docs/results_of_record/MANIFEST.md`, section `device_generalization_2026_11`.

*Updated 2026-11-16* with the uniform-NLOS shared environment and the second mixed shared
environment. Edits 1, 2, 6, 7 and 8 changed; Edits 3, 4 and 5 did not.

---

## What changed since the 2026-11-07 PDF, and how strong the evidence is

The report already says that every user in the simulation has its own channel realization
(Section VII-B). The edits below add two things:

1. **The macro cell has the same property.** Its test users are unseen, but their RSS map is also
   separate, so only the angle, which follows the geometry, can carry over between users. The
   current text reads as if the full channel transfers.
2. **A shared-environment check now exists.** Three macro-geometry datasets simulate all users
   in one environment (`run_shared_env_devices.m`): two with mixed LOS/NLOS propagation and one
   with uniform NLOS. In them, history helps unseen users more, and only there do differences
   between reports help at all.

**How strong the evidence is for the uniform-NLOS claim of Section VII** ("history adds nothing
for single-antenna devices"):

- With separate realizations and uniform NLOS, our script reproduces the null result: without an
  angle, history gains nothing for either device group (−0.2 to 0.4 m).
- In the uniform-NLOS shared environment, history lowers the error of multi-antenna devices by
  5–10 m (no angle used).
- For single-antenna devices, the gain is 2.5 ± 2.0 m (XGBoost, both) and 5.9 ± 3.2 m (GRU,
  both). Only the GRU interval is clear of zero. IoT devices are 15 % of users, so the intervals
  are wide.

So the null result is largely a consequence of simulating every user as a separate channel
realization, and the edits now say so. The single-antenna part rests on one model and one
environment, and the edits say that too.

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
environment shared by all users, history lowers the error of unseen users, under uniform NLOS as
well.
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
depends largely on the simulation: when all users share one simulated environment, history
lowers the error of unseen users, also under uniform NLOS, and differences between consecutive
reports become informative.
```

---

## Edit 3 — Channel simulation, Section III-A (p. 8)

**Find:** `This work extends a time-aware multi-user massive multiple`

**Insert after** the sentence that ends `...that is described in Section III-D.`:

*Origin, checked 2026-11-16:* the channel generation (`core/generate_simulation_data.m`) is
ours; its history goes back to the repository's first commit (2025-11-02), before any of Omri's
code arrived. The Voronoi area, geometry and traffic helpers (`lib/AreaGenerator.m`,
`GeometryUtils.m`, `TrafficUtils.m`) were added on 2026-02-21. Their names and header text
match Omri's files, which carry his copyright, and about four fifths of the lines of
`AreaGenerator.m` are identical. So "extends [16]" is accurate for the area model, not for how the channel is drawn.
Optionally, make the existing sentence precise by replacing `This work extends a time-aware
multi-user ... simulator developed within the same research group [16], [17], to which we added`
with `This work adapts the area model of a time-aware multi-user ... simulator developed within
the same research group [16], [17], and adds`.

```latex
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
realization, we generated three further macro-cell datasets in which all users share one
environment: two with the mixed LOS/NLOS regions of the macro cell, drawn from different seeds,
and one in which every region is NLOS. Each has 300~users in four device classes: mid-tier
phones with four antenna elements, flagship phones and vehicles with sixteen, and single-antenna
IoT devices, which differ in carrying height, antenna gain, noise figure and speed. The random
generator of the channel simulation is reset to a common seed before every segment of every
walk, so that all users see the same large-scale parameter maps; the small-scale fading is still
drawn per segment, so the environment is only partly shared. At the same grid point, the median
difference in received power between two users is \SI{5.1}{dB}, against \SI{6.7}{dB} with
separate realizations. No angle is used in this comparison, and no static device attributes are
given to the models.

Table~\ref{tab:shared-env} compares the history gain on unseen users (five user splits, 80/20)
with separate realizations and in the shared environments, for XGBoost and a gated recurrent
unit~(GRU) given the last $h=5$ reports. With separate realizations, history lowers the error
by about \SI{2}{} to \SI{3}{m} under mixed propagation, the gain of Section~VII-C, and not at all
under uniform NLOS; in both cases the differences between consecutive reports make the error
worse than a single report. In the shared environments, the gain grows for both models and both
propagation settings. It is largest for the GRU given levels and differences together, which
lowers the error of multi-antenna devices by \SI{9}{} to \SI{10}{m}, and the differences between
reports now lower the error as well. Under uniform NLOS, where history gains nothing with
separate realizations, the shared environment gives single-antenna devices a gain of
\SI{5.9 \pm 3.2}{m} with the GRU; the gain of XGBoost, \SI{2.5 \pm 2.0}{m}, is not clearly
different from zero. With $h=20$ and the GRU trained on phones only, the differences alone bring
single-antenna IoT devices, a class not seen in training, from 37.5 and \SI{35.1}{m} to 20.2 and
\SI{21.1}{m} in the two mixed environments, and from 32.9 to \SI{23.8}{m} under uniform NLOS.

A shared map therefore lets history, and above all the change between reports, carry over to
new users. The uniform-NLOS result of Section~VII, where history adds nothing for single-antenna
devices, is thus largely a consequence of the separate realizations, although the single-antenna
evidence rests on one model and one environment.

\begin{table}[h]
  \centering
  \caption{History gain on unseen users with separate channel realizations and in a shared
  environment (macro-cell geometry, no angle). Error of a single report ($h=0$) and its
  reduction by a window of $h=5$ reports, in metres; seed-paired means over five user splits
  with 95\,\% Student-t intervals. Levels: the reports as received; differences: the change
  between consecutive reports; both: the two together. Mixed: LOS/NLOS regions; shared~1 and~2
  are two environments drawn from different seeds.}
  \label{tab:shared-env}
  \begin{tabular}{@{}llllrrrr@{}}
    \toprule
    Propagation & Environment & Model & Devices & $h=0$ & Levels & Differences & Both \
    \midrule
    Mixed & Separate & XGBoost & Multi  & 29.4 & $2.3 \pm 0.6$ & $-3.3 \pm 0.4$ & $2.4 \pm 0.6$ \
          &          &         & Single & 28.7 & $2.6 \pm 0.5$ & $-2.9 \pm 1.3$ & $2.9 \pm 0.6$ \
          &          & GRU     & Multi  & 28.3 & $1.8 \pm 0.3$ & $-3.6 \pm 0.6$ & $2.1 \pm 0.8$ \
          &          &         & Single & 27.8 & $2.3 \pm 0.7$ & $-2.7 \pm 1.3$ & $2.9 \pm 0.6$ \
    \cmidrule{2-8}
          & Shared 1 & XGBoost & Multi  & 30.6 & $3.9 \pm 0.4$ & $-0.3 \pm 0.5$ & $4.6 \pm 0.4$ \
          &          &         & Single & 32.1 & $2.8 \pm 1.1$ & $-0.2 \pm 1.4$ & $3.5 \pm 0.8$ \
          &          & GRU     & Multi  & 29.8 & $5.2 \pm 0.7$ & $6.8 \pm 1.9$  & $9.0 \pm 1.3$ \
          &          &         & Single & 32.1 & $3.6 \pm 1.1$ & $5.4 \pm 3.7$  & $7.2 \pm 2.0$ \
    \cmidrule{2-8}
          & Shared 2 & XGBoost & Multi  & 31.4 & $4.1 \pm 0.5$ & $0.3 \pm 0.6$  & $5.8 \pm 0.6$ \
          &          &         & Single & 31.0 & $3.2 \pm 1.0$ & $-0.6 \pm 2.0$ & $4.1 \pm 1.3$ \
          &          & GRU     & Multi  & 30.4 & $6.2 \pm 1.1$ & $6.5 \pm 2.5$  & $8.9 \pm 1.8$ \
          &          &         & Single & 30.7 & $3.9 \pm 3.9$ & $4.1 \pm 4.9$  & $5.7 \pm 4.3$ \
    \midrule
    NLOS  & Separate & XGBoost & Multi  & 33.7 & $0.2 \pm 0.3$  & $-2.0 \pm 0.4$ & $0.4 \pm 0.3$ \
          &          &         & Single & 33.4 & $-0.2 \pm 0.6$ & $-2.3 \pm 1.2$ & $-0.2 \pm 0.7$ \
          &          & GRU     & Multi  & 33.6 & $0.3 \pm 0.3$  & $-2.1 \pm 0.4$ & $0.2 \pm 0.4$ \
          &          &         & Single & 33.5 & $-0.2 \pm 0.7$ & $-1.9 \pm 1.3$ & $0.0 \pm 0.5$ \
    \cmidrule{2-8}
          & Shared   & XGBoost & Multi  & 34.2 & $5.1 \pm 0.5$ & $1.1 \pm 0.6$  & $5.8 \pm 0.5$ \
          &          &         & Single & 32.8 & $2.0 \pm 2.0$ & $-0.7 \pm 2.6$ & $2.5 \pm 2.0$ \
          &          & GRU     & Multi  & 32.6 & $7.4 \pm 1.2$ & $5.1 \pm 2.0$  & $10.1 \pm 2.2$ \
          &          &         & Single & 33.1 & $3.8 \pm 3.1$ & $1.8 \pm 4.3$  & $5.9 \pm 3.2$ \
    \bottomrule
  \end{tabular}
\end{table}
```

*Notes for us:*

- **Datasets differ in more than the shared map.** The device models differ: the old data
  has antenna counts of 1, 2 and 4 with a gain drawn from −4 to +2 dB; the new data has the four
  classes above.
  Single-antenna devices are 15 % of users in both. Say so if a reviewer asks; the table caption
  does not claim the device sets are equal. The uniform-NLOS shared environment uses the same
  seed, users and devices as shared environment 1; only the propagation differs.
- **Separate uniform NLOS** is the old campaign B data (`sim_data_300users_2026-07-25_11-46-11`),
  run through the same script. Its multi-antenna gain is zero here because no angle is used; the
  report's multi-antenna gain in Section VII comes from the angle.
- **`\SI{5.9 \pm 3.2}{m}`** needs siunitx with `separate-uncertainty`; if it does not compile,
  write `$5.9 \pm 3.2$\,m`.
- **The table is long (20 rows).** If it is too long, drop the Shared 2 rows and say in the text
  that a second mixed environment gives the same picture.
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
on unseen users under mixed and uniform-NLOS propagation (Section~\ref{sec:shared-env}); a fully
shared environment, and the same test on the controlled grid, remain to be done.
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
by all users, history lowers the error of unseen single-antenna devices by about \SI{6}{} to
\SI{7}{m} with a recurrent model, under uniform NLOS as well.
```

### 8b. Last follow-up of the second paragraph

**Find:** `Finally, a controlled grid simulated as one environment shared by all users would test`

The current sentence:

> Finally, a controlled grid simulated as one environment shared by all users would test whether
> the within-user gain carries over to new users.

**Replace with:**

```latex
Finally, a fully shared environment, including the small-scale fading, and the same test on the
controlled grid would show whether the within-user gain carries over to new users there as it
does, in part, in the partly shared macro-cell environments.
```

---

## Not changed

- **Section VII-C** (single-antenna devices under mixed propagation) stays. The gain there
  follows the propagation state of the region, which is geometric and therefore shared between
  users even with separate realizations.
- **Controlled grid and 25 × 25 results** stay. Section VII-B already labels them within-user.
- **Abstract:** the PDF of 2026-11-07 has none. If the Overleaf source has one, apply Edit 1 to
  it too.
