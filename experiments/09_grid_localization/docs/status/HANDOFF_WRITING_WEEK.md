# Handoff: writing week on a computer without MATLAB (from 2026-10-25)

Paste the prompt in section 1 into Claude Code on the new computer, from the repository root, on branch `followup-2026-10`.

## 1. Prompt for Claude Code

> You are continuing the CSI-Location project (single-base-station 5G localization; claim: transition history improves localization). This week is for writing the paper; no simulations (MATLAB is not installed here) and no new experiments unless I ask. Read, in this order: `experiments/09_grid_localization/docs/status/HANDOFF_WRITING_WEEK.md` (this file), `docs/README.md` (inside `experiments/09_grid_localization/`), `docs/status/CLAIM_EVIDENCE_MAP.md`, `docs/paper/PAPER_OUTLINE.md`, `docs/status/PLAN_AND_CHECKLIST.md` sections 4.3, 6b. Then tell me in a few lines what state the paper is in and what you propose to do first. Rules: every number you write must come from `docs/results_of_record/` or the tables in `docs/paper/tables/` (check it there, never from memory or from old snapshots); keep chat replies short; write documents in plain, careful English; commit only the files you changed, by explicit path, with the trailer `Co-Authored-By: Claude <noreply@anthropic.com>`; never commit `docs/Personal/` or LaTeX build files.

## 2. State on 2026-10-25

- Branch `followup-2026-10`, everything pushed. `main` is far behind (merge after the paper draft is stable).
- Paper: not started as text on purpose. A 2-page review package for the instructors (`docs/paper/paper_draft/review_v1.tex`) is ready; the author answered its five questions (in `docs/paper/PAPER_OUTLINE.md`, "Author's answers"). Waiting for the instructors on venue and on including the irregular-history result.
- Decisions taken: framing = consistent gain from history (Dudi, 22.10: "paradigm change", not a method or an accuracy); metric = MAE first, MPE (MAE / grid spacing) second, exact-cell accuracy only for the grid; irregular history (claim C8) goes in, marked "pending Dudi's approval"; the paper stays on learned history and reports the HMM tracking filter as a baseline that is stronger than the GRU on the grid, with the reason; LSTM and attention get one sentence each; no runs beyond h = 15.
- Open issue to state as a limitation (and raise with the instructors): in the grid and 25×25 simulations each user has its own environment realization, so their results are within-user (known-map) results; a model trained on four users fails on the fifth (leave-one-user-out test, claim map C5/C6). A shared-environment simulation was tried with a common seed and only partly worked; the proper fix (one layout with all users) was not done.
- Open question for the discussion section: why history helps without an angle on small cells but not at macro range (claim map, C5/C6: hypotheses H1 and H2; the leave-one-user-out result supports H1).

## 3. Where everything is (all under `experiments/09_grid_localization/docs/`)

| What | Where |
|---|---|
| What the paper claims and the evidence for each claim | `status/CLAIM_EVIDENCE_MAP.md` |
| Paper structure, page budget, figures, tables, cuts, decisions | `paper/PAPER_OUTLINE.md` |
| Paper tables (generated, do not edit by hand) | `paper/tables/` — rebuild: `python paper/tables/make_tables.py` |
| Review package for the instructors | `paper/paper_draft/review_v1.tex` |
| The long report (36 pages; the thesis version; source of paragraphs and figures) | `paper/Transition_History/` (`main.tex`; figures in `figures/`, follow-up figures made by `figure_scripts/make_figures_followup.py`) |
| Full technical documentation of every result | `technical/Project_documentation/technical_documentation_revised.md` (section 6 is the results) |
| Every number's source data | `results_of_record/` (small copies of the result files; `results/` itself is not in git) |
| Plan, checklist, meeting decisions | `status/PLAN_AND_CHECKLIST.md` (4.3 to do; 6 and 6b the instructor meetings of 12.10 and 22.10) |
| Which old numbers are superseded and why | `status/OLD_VS_REGENERATED_RUNS.md` |
| Personal material (study guide, meeting transcripts, slides) | `Personal/` — not in git; in the handoff zip |

## 4. What to do this week, in order

1. Start the paper as a new LaTeX project in `paper/paper_draft/` (`main.tex`), following `PAPER_OUTLINE.md`. Generic single-column article class until the venue is known; at most 12 pages.
2. Write sections 4 (setup) and 5 (results) first, from the tables in `paper/tables/` and the figures listed in the outline; add an MPE column to the tables (`make_tables.py`).
3. Then section 6 (discussion; the C5/C6 paragraph needs care, see claim map), then the introduction and abstract, then related work, then limitations and conclusion.
4. Related work and `reference.bib` (does not exist yet): channel charting, single-BS CSI localization accuracy, fingerprinting, sequence models and tracking filters for localization, 3GPP device mix. Do not invent references; mark missing ones `%TODO-CITE`.
5. Small fixes from the 22.10 meeting (plan 4.3): define the propagation settings (RMa LOS, UMi LOS/NLOS, mixed per-cell) where they first appear; antenna footnote (UE profiles 1, 2, 4 omni elements; serving BS a single omni antenna; AoA = simulator angle plus noise); limitation on per-user environments.
6. Mark every paragraph that depends on an instructor decision with `% PENDING:` and the decision.

## 5. Tools needed on this computer

- Python 3.11 with the packages in `experiments/09_grid_localization/requirements.txt` (numpy, pandas, matplotlib are enough for the tables and figure scripts; torch and xgboost only if experiments are rerun, which is not planned).
- A LaTeX distribution (MiKTeX or TeX Live) with `pdflatex`. Build: `pdflatex main.tex` twice in the project folder.
- Not needed: MATLAB, QuaDRiGa, the `results/` folder.

## 6. Numbers to keep at hand (all from the results of record)

- Grid (15×15, mixed, MAE): best without history 4.93 m (corner) / 5.21 m (centre), GRU h = 15 1.42 / 1.24 m; with AoA 1.30 / 0.60 m; constant guess 10.91 m. AoA gain +19.5 pp centre, +1.0 pp corner (XGBoost, h = 3).
- 25×25 (MAE): GRU h = 15 beats the best tree in 6 of 6 settings by 1.3–5.0 m; constant guess 37.3 m.
- Macro: multi-antenna 18.7 → 15.4 m (guess 37.1 m); 15–21 % gain in seven families; single-antenna at the guess level (34.7 m, guess 33.6 m).
- Order: 13–28 % of the GRU gain from h = 0 to 15 is the order; shuffling older reports raises the error 19–48 %.
- Irregular history: GRU keeps 80–90 % of its gain with 30 % missing or uneven gaps; train with the irregularity.
- Tracking filter (RF + HMM, grid corner, no AoA): 0.71 m learned motion, 0.93 m generic 2 m motion, against GRU 1.59 m.
- Leave-one-user-out (grid): about 1 % / 12 m on an unseen user for every model.
