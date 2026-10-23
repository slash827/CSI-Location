# docs/ — what is where

| Folder | Contents | Start with |
|---|---|---|
| `status/` | Where the project stands: plan and checklist, claim–evidence map for the paper, old against regenerated runs, results directory map | `status/PLAN_AND_CHECKLIST.md`, `status/CLAIM_EVIDENCE_MAP.md` |
| `paper/` | The report / paper draft (`Transition_History/`, LaTeX, `main.tex`; figures in `Transition_History/figures/`, made by `Transition_History/figure_scripts/`) and its skeleton and guidelines | `paper/Transition_History/main.tex` |
| `technical/` | Technical documentation (`Project_documentation/`, with the revised edition `technical_documentation_revised.md`), architecture notes, how-to guides | `technical/Project_documentation/technical_documentation_revised.md` |
| `results_of_record/` | Small copies of the results every number in the paper and the documentation is taken from (`results/` itself is gitignored). Kept at this level because scripts point to it | `results_of_record/MANIFEST.md` |
| `archive/` | Earlier analyses, plans, session summaries, enhancement notes, old figures; kept for history, not maintained | — |
| `Personal/` | Meeting transcripts and notes, study guide, slides; not tracked (listed in `.git/info/exclude`) | — |

Build the report: `pdflatex main.tex` (twice) inside `paper/Transition_History/`. Regenerate its follow-up figures: `python paper/Transition_History/figure_scripts/make_figures_followup.py`.
