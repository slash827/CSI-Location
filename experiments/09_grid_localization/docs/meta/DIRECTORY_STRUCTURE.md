# Experiment 09: Grid Localization - Directory Structure

**Last Updated:** January 17, 2026

This document explains the reorganized directory structure for the grid localization experiment.

---

## 📁 Directory Overview

```
experiments/09_grid_localization/
├── src/                          # Active source code
│   ├── matlab/                   # Current MATLAB scripts
│   └── python/                   # Current Python scripts
├── archived/                     # Old/experimental code (not in active use)
│   ├── matlab/                   # Archived MATLAB files
│   └── python/                   # Archived Python files
├── configs/                      # Configuration files
├── docs/                         # Documentation (organized by category)
│   ├── guides/                   # User guides and how-tos
│   ├── analysis/                 # Technical analysis documents
│   └── architecture/             # System architecture docs
├── __pycache__/                  # Python bytecode cache
├── README.md                     # Main project README
├── requirements.txt              # Python dependencies
└── DIRECTORY_STRUCTURE.md        # This file
```

---

## 📂 Detailed Structure

### `src/` - Active Source Code

Contains **currently maintained** and actively used code.

#### `src/matlab/`
| File | Purpose |
|------|---------|
| `generate_simulation_data.m` | Primary MATLAB script for generating QuaDRiGa channel simulations |
| `run_from_config.m` | Helper script to run simulations from config file |

**Usage:**
```matlab
cd src/matlab
run_from_config  % Reads from ../../configs/config.json
```

#### `src/python/`
| File | Purpose |
|------|---------|
| `localization_pipeline.py` | **Main pipeline** - Trains and evaluates localization models (Gaussian, Random Forest) |
| `plot_pipeline_results.py` | Generates visualizations from pipeline results (.npz format) |
| `run_full_pipeline.py` | End-to-end script: MATLAB simulation → Python analysis → Visualization |

**Usage:**
```powershell
# Run main pipeline
python src/python/localization_pipeline.py --data-dir <DATA_DIR> --max-history 3 --metrics RSS,SINR,CQI

# Generate plots
python src/python/plot_pipeline_results.py <RESULTS_DIR>

# Full end-to-end pipeline
python src/python/run_full_pipeline.py --grid-size 10x10 --scenario UMa_NLOS
```

---

### `archived/` - Historical Code

Contains **legacy code** from previous experiments and trial-and-error phases. Kept for reference but not actively maintained.

#### `archived/matlab/`
| File | Status | Purpose (Historical) |
|------|--------|---------------------|
| `exp13e_corrected_fair_comparison.m` | ⚠️ Superseded | Old MATLAB-based localization (before Python migration) |
| `exp13e_corrected_fair_comparison_backup.m` | 📦 Backup | Backup of above |
| `compute_delta_likelihood.m` | 🔬 Experimental | Delta calculation experiments |
| `generate_corrected_report.m` | ⚠️ Old | Generated reports in old format |
| `reorganize_results.m` | 🛠️ Utility | Result reorganization script (one-time use) |
| `test_interference_effect.m` | 🧪 Test | Interference impact testing |

#### `archived/python/`
| File | Status | Purpose (Historical) |
|------|--------|---------------------|
| `plot_results.py` | ⚠️ Superseded | Old plotting script (for .mat files, not .npz) |
| `compare_all_approaches.py` | 🔬 Experimental | Comparison experiments across methods |
| `fusion_experiments.py` | 🧪 Test | Multi-metric fusion experiments |
| `test_rf_fusion.py` | 🧪 Test | Random Forest fusion testing |

**Note:** These files are preserved for:
- Reference during debugging
- Understanding past design decisions
- Comparing old vs new implementations
- Historical record of experiments

---

### `configs/` - Configuration Files

Contains JSON configuration files for simulations and experiments.

| File | Purpose |
|------|---------|
| `config.json` | **Primary config** - Used by `generate_simulation_data.m` and `run_full_pipeline.py` |
| `config_rf_fusion.json` | Random Forest fusion experiments config |

**Config Structure:**
```json
{
  "grid": {
    "size": 10,
    "spacing": 2.0,
    "grid_offset": [0, 0]
  },
  "base_station": {
    "position": [50, 50, 25],
    "interferers": { "enabled": true, ... }
  },
  "channel": {
    "scenario": "3GPP_38.901_UMa_NLOS",
    ...
  },
  "simulation": {
    "n_samples": 40000,
    "velocity": 1.0
  }
}
```

---

### `docs/` - Documentation

All documentation organized by category.

#### `docs/guides/` - User Guides & References

**How-to guides and command references for daily use:**

| File | Purpose |
|------|---------|
| `COMMON_COMMANDS.md` | Quick reference for all pipeline commands |
| `SCALABILITY_AND_OPTIMIZATION_GUIDE.md` | Performance optimization strategies (data leakage, curse of dimensionality, 8-neighbors, etc.) |
| `SCALING_TEST_PLAN.md` | Test plan for scaling to larger grids |

**Read this first if you're:**
- Running experiments
- Need command syntax
- Looking to optimize performance
- Scaling to larger grids

#### `docs/analysis/` - Technical Analysis

**In-depth technical investigations and findings:**

| File | Topic |
|------|-------|
| `BUG_INVESTIGATION_RSS_SINR_IDENTICAL.md` | Why RSS and SINR produced identical results |
| `DATA_LEAKAGE_ANALYSIS.md` | Data leakage in train/test splits |
| `INTERFERENCE_IMPACT_EXPLAINED.md` | How interfering base stations affect metrics |
| `MAKING_RSS_SINR_DIFFERENT.md` | Techniques to differentiate RSS and SINR |
| `RSS_vs_SINR_INSIGHTS.md` | Comparative analysis of RSS vs SINR |
| `WHY_RSS_SINR_IDENTICAL_EXPLAINED.md` | Root cause analysis of metric similarity |

**Read this if you're:**
- Debugging unexpected behavior
- Understanding why metrics behave certain ways
- Investigating performance issues
- Writing thesis analysis sections

#### `docs/architecture/` - System Architecture

**High-level design and system structure:**

| File | Purpose |
|------|---------|
| `PIPELINE_ARCHITECTURE.md` | Overall pipeline design and data flow |
| `IMPLEMENTATION_SUMMARY.md` | Implementation details and design decisions |
| `New_experiment_13e.md` | Experiment 13e design and methodology |
| `RESULTS_REORGANIZATION.md` | Results directory structure explanation |

**Read this if you're:**
- Understanding the overall system design
- Planning new features
- Reviewing architecture decisions
- Onboarding new team members

---

## 🚀 Quick Start Guide

### For New Users:

1. **Read documentation:**
   ```
   README.md                           # Start here
   docs/guides/COMMON_COMMANDS.md      # Command reference
   docs/architecture/PIPELINE_ARCHITECTURE.md  # System overview
   ```

2. **Set up environment:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run a simple test:**
   ```powershell
   # 3x3 grid for quick testing
   python src/python/run_full_pipeline.py --grid-size 3x3 --n-samples 5000
   ```

### For Daily Usage:

1. **Configure experiment:**
   - Edit `configs/config.json`

2. **Generate data (MATLAB):**
   ```matlab
   cd src/matlab
   run_from_config
   ```

3. **Run pipeline (Python):**
   ```powershell
   python src/python/localization_pipeline.py --data-dir <DATA_DIR> --max-history 3
   ```

4. **Generate plots:**
   ```powershell
   python src/python/plot_pipeline_results.py <RESULTS_DIR>
   ```

### For Performance Optimization:

See: `docs/guides/SCALABILITY_AND_OPTIMIZATION_GUIDE.md`

---

## 📝 File Naming Conventions

- **Active scripts:** Descriptive names (e.g., `localization_pipeline.py`)
- **Configs:** `config_<purpose>.json`
- **Docs:** `UPPERCASE_WITH_UNDERSCORES.md`
- **Archived files:** Keep original names with location indicating status

---

## 🔄 Migration Notes

**What changed (Jan 17, 2026):**

1. ✅ Split source code by language (`src/matlab/`, `src/python/`)
2. ✅ Moved experimental/old code to `archived/`
3. ✅ Centralized configs in `configs/`
4. ✅ Organized docs by category (`guides/`, `analysis/`, `architecture/`)

**Impact on existing scripts:**

- **MATLAB scripts:** Update paths in scripts to reference `../../configs/config.json`
- **Python imports:** Update import paths if needed:
  ```python
  # Old:
  from localization_pipeline import Pipeline
  
  # New:
  from src.python.localization_pipeline import Pipeline
  ```

- **Command-line usage:** Adjust paths:
  ```powershell
  # Old:
  python localization_pipeline.py --data-dir ...
  
  # New:
  python src/python/localization_pipeline.py --data-dir ...
  ```

---

## 🛠️ Maintenance

### When to Archive a File:

✓ File is superseded by a new implementation  
✓ File was used for one-time experiments  
✓ File is a backup or old version  
✓ File is no longer referenced in active workflows

### When to Keep a File Active:

✓ File is used in current experiments  
✓ File is imported by other active code  
✓ File is referenced in documentation  
✓ File provides core functionality

### Regular Maintenance:

- Review `archived/` quarterly, delete truly obsolete files
- Update `COMMON_COMMANDS.md` when adding new features
- Keep `DIRECTORY_STRUCTURE.md` (this file) up to date

---

## 📊 Results Directory Structure

Results are stored separately in `results/grid_localization/`:

```
results/grid_localization/
├── grid_3x3/
│   ├── sim_data_LOS_YYYY-MM-DD_HH-MM-SS/     # MATLAB simulation output
│   └── exp13e_LOS_YYYY-MM-DD_HH-MM-SS/       # Python pipeline results
├── grid_5x5/
├── grid_10x10/
└── grid_NxN/
```

See `docs/architecture/RESULTS_REORGANIZATION.md` for details.

---

## 🤝 Contributing

When adding new files:

1. Place in appropriate `src/` subdirectory
2. Update this document
3. Update `COMMON_COMMANDS.md` if adding user-facing features
4. Add entry to `README.md` if it's a major component

---

## 📞 Contact

For questions about this directory structure, see:
- Main README: `README.md`
- Architecture: `docs/architecture/PIPELINE_ARCHITECTURE.md`
- Commands: `docs/guides/COMMON_COMMANDS.md`

---

*This structure was reorganized on January 17, 2026 to improve maintainability and clarity.*
