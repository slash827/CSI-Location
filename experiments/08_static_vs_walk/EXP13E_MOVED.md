# ⚠️ Experiment 13e Has Moved

**Experiment 13e (Grid Localization)** has been moved to its own directory:

## New Location
📁 **`experiments/09_grid_localization/`**

This directory now contains:
- `exp13e_corrected_fair_comparison.m` - Main experiment script
- `generate_corrected_report.m` - Report generator
- `reorganize_results.m` - Results migration tool
- `run_from_config.m` - Experiment reproduction tool
- `SCALING_TEST_PLAN.md` - Scaling guide (3×3 to 20×20)
- `RESULTS_REORGANIZATION.md` - Results structure docs
- `README.md` - Complete documentation

## Why the Move?

Experiment 13e evolved into a comprehensive grid localization study comparing:
- Static classification (RSS_current only)
- Transition-based classification (RSS_current + RSS_previous)

It deserved its own dedicated directory with proper organization for:
- Multiple grid sizes (3×3, 5×5, 10×10, 20×20)
- Reproducible experiments (JSON configs)
- Organized results (grid_localization/grid_NxN/)

## What Remains Here?

This directory (`08_static_vs_walk/`) now focuses on the original hypothesis:
- **exp13a**: Static grid CSI measurements
- **exp13b**: Random walk CSI measurements  
- **exp13c**: Temporal stability analysis
- **exp13d**: Delta (Δ) characteristics analysis
- Python analysis tools

These experiments test whether CSI depends on movement history in QuaDRiGa.

## Updated Index

See `experiments/EXPERIMENT_INDEX.md` for the updated structure:
- **Level 8**: Static vs Walk CSI Comparison (exp13a-13d)
- **Level 9**: Grid Localization (exp13e) ← **Moved here**

---

*Last Updated: January 8, 2026*
