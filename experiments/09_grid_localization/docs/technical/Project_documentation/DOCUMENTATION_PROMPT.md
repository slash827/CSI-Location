# Claude Code Prompt — Research Documentation

## Your Goal

Write a comprehensive research documentation file that tells the story of this
localization project from beginning to end — what was tried, why, what worked,
what didn't, and how the research evolved. This document will serve as the
foundation for a future academic paper.

The output is a single Markdown file: `docs/research_documentation.md`
If this file already exists, read it first and improve/extend it rather than
starting from scratch.

---

## Step 1: Project Survey (do this before writing anything)

### 1a — Read all summary and results documents

Search the project for Markdown files whose names contain any of these words:
`summary`, `results`, `analysis`, `experiment`, `session`, `progress`, `findings`

Read every file you find. These are the primary source of truth about what
happened in the project and in what order.

Also read:
- `TASKS.md` — current task list and experiment naming convention
- `README.md` (root and any subdirectories)
- Any file named `CHANGELOG` or `NOTES`

### 1b — Read the experiment naming convention

The current experiment naming convention is:

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

Legend: H = history absolute stacking h=3, A = AoA with noise model
(4° Gaussian + 5° quantization), dp = device params, uid = user_id oracle.

Use these names consistently throughout the document. If older documents use
the old names (E1–E7 in the original scheme), translate them using this mapping:

| Old | New |
|-----|-----|
| E1 (old) | BASE |
| E2 (old) | BASE_H |
| E3 (old) | BASE_H_dp |
| E4 (old) | BASE_H_uid |
| E5 (old) | BASE_A |
| E6 (old) | BASE_A_H |
| E7 (old) | BASE_A_H_dp |

### 1c — Read the results data

Read the following files if they exist:
- `results/multi_user_voronoi_15x15/results_summary.csv`
- `results/multi_user_voronoi_15x15/per_user_breakdown.csv`
- `results/multi_user_voronoi_15x15/per_cell_breakdown.csv`
- Any other CSV files under `results/`

### 1d — Inventory the plots

List all PNG files under `results/`. You will reference the most important ones
in the document.

### 1e — Skim the source code (optional, for methodology details)

If any methodology detail is unclear from the documents and CSVs, skim:
- `src/python/multi_user_pipeline.py` — experiment definitions and feature builders
- `src/python/localization_pipeline.py` — single-user pipeline
- `src/matlab/AreaGenerator.m` — Voronoi environment generation

Do not spend time on implementation details — only read enough to clarify
methodology questions.

---

## Step 2: Write the Documentation

Write `docs/research_documentation.md` following this structure.
The document should read as a **research narrative**, not a bullet-point list.
Use prose paragraphs for explanations, tables only for results.

---

### Document Structure

#### Title and Header
- Title, student name, advisors, institution, industry partners, date

#### Abstract (half page)
One paragraph summarizing: the problem, the central hypothesis, the approach,
and the key findings. Written as if for a paper abstract.

#### 1. Problem Statement
- Why indoor localization is hard
- Why RSS alone is insufficient (distance ring ambiguity)
- The central hypothesis: transition history improves localization
- Formal definition of the input/output (feature window, classification vs regression)
- Scope: single serving BS, no triangulation

#### 2. Simulation Environment
- QuaDRiGa setup: frequency **3.5 GHz**, bandwidth, subcarriers, BS antenna
- UE walk model: random walk, 8-connectivity, steps per point
- The two environments: uniform NLOS (scalability) and Voronoi heterogeneous (main)
- Voronoi cell design rationale: why 4 maximally distinct scenarios
- BS placement inside grid: why this enables 360° AoA coverage
- Train/test split: why chronological, why not random

#### 3. Feature Metrics
- Table of all available metrics with realism assessment
- AoA noise model: the two-stage impairment (4°+5°) and its justification
- Key insight: RSS ≈ SINR without interference, and why
- Feature importance finding: the dramatic AoA effect (+55pp)
- CQI saturation at close range

#### 4. Research Progression

This is the most important section. Tell the story chronologically:

**4.1 Starting point — single user, uniform environment**
- First experiments: can history help at all?
- Algorithm comparison (Gaussian, RF, XGBoost, MLP) — all improve with history
- Scalability: does it hold from 3×3 to 20×20?
- Performance optimization: the speedups that made large-scale experiments feasible

**4.2 Adding realism — Voronoi heterogeneous environment**
- Why uniform NLOS is insufficient
- Design of the 4-cell Voronoi environment
- Feature selection experiments: RSS → RSS+SINR → +AoA azimuth → +AoA elevation
- Per-cell analysis: why small cells confuse the model, why highway benefits most from AoA

**4.3 Adding interference — multi-BS experiment**
- Motivation: can SINR be made spatially informative?
- The v1 bug (SINR 30 dB too negative) and how it was found and fixed
- v2 realistic setup: interferers outside the grid, orthogonal directions
- Result: interference SINR helps (+33pp over RSS) but AoA dominates

**4.4 Multi-user heterogeneous devices**
- Motivation: real networks have heterogeneous hardware
- The 5 device profiles and the U1/U4 control pair
- Experiment design: BASE → BASE_H → BASE_H_dp and the AoA variants
- Key findings: transitions help, device params help more, AoA is device-independent
- Cross-user generalization: why AoA drops only 7pp vs 4pp from a much lower base
- Per-user and per-cell breakdown

#### 5. Key Findings
Numbered list of the main empirical findings, each with a one-sentence
explanation of why it matters. Cover:
- Transition history is universal (all algorithms, all scales)
- AoA dominance and device independence
- RSS ≈ SINR without interference
- Classification vs regression trade-off and crossover estimate
- Device heterogeneity and how to handle it
- Cell size as the dominant factor in per-cell accuracy
- The feature hierarchy: AoA ≫ interference SINR > RSS

#### 6. Methodology Notes
Short section on decisions that affected validity:
- Why temporal split (not random)
- AoA oracle vs noise model — what was fixed and when
- The AreaGenerator bug and its effect on results
- Memory management for Gaussian model

#### 7. Open Questions
Brief section on what remains to be tested:
- Absolute values vs. deltas across data volumes and environments
- Environmental variability (same user, different days)
- Generalization to real hardware

---

## Writing Guidelines

**Tone:** Academic but readable. Assume the reader is a senior engineer or
researcher in wireless communications, not necessarily familiar with ML.

**On negative results:** Include them. The SINR bug, the oracle AoA issue,
the AreaGenerator fix — these show scientific rigor and are expected in a paper.

**On numbers:** Every claim must be backed by a specific number from the results.
Do not write "accuracy improved significantly" — write "accuracy improved from
43.5% to 52.5% (+9pp)".

**On experiment names:** Always use the new naming convention (BASE, BASE_H,
BASE_A, etc.) with the index in parentheses (e.g., "BASE_H (E4)") on first
mention in each section.

**Length:** Aim for 2,500–4,000 words. This is a working document for advisor
review, not a final paper — completeness is more important than brevity.

---

## Output

Save the completed document to `docs/research_documentation.md`.

Print a short summary of what you found during the survey (Step 1) before
writing — list the summary files you read, the experiments you found evidence
of, and any gaps or inconsistencies you noticed.
