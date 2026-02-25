# Voronoi 10×10 Grid with BS Inside Grid

**Created:** February 23, 2026  
**Purpose:** Realistic small-cell scenario with the serving base station positioned **inside** the grid coverage area, using Voronoi-based heterogeneous LOS/NLOS environment.

---

## Overview

This simulation creates a **10×10 grid** (2m spacing, 18m × 18m area) with the serving BS **at the center** of the grid. This represents a realistic **Urban Micro small cell** deployment where UEs move within the cell coverage area directly under/around the BS.

### Key Differences from Previous 10×10 Data

| Parameter | Previous 10×10 | Voronoi 10×10 (This) |
|-----------|----------------|----------------------|
| **BS position** | (44, 26, 25)* or outside grid | **(14, 14, 10) — at grid center** |
| **BS height** | 25m (macro) | **10m (small cell UMi)** |
| **Scenario** | Uniform NLOS or LOS | **Mixed (Voronoi 4-areas)** |
| **Area types** | Single | **shopping_center, residential, office, park** |
| **Interferers** | 4 BSs outside grid | **None** |
| **Grid offset** | [30, 0] or varies | **[5, 5]** |
| **Grid extent** | X: [30, 68], Y: [0, 38] or varies | **X: [5, 23], Y: [5, 23]** |
| **Samples** | 40,001 | **40,001** |
| **Steps/point** | 400 | **400** |

*Based on `data_generation_config.jsonc`

---

## Simulation Parameters

### Grid Configuration

```json
"grid": {
  "size": 10,
  "spacing": 2.0,          // 2m grid spacing
  "ue_height": 1.5,        // UE at 1.5m height
  "grid_offset": [5, 5],   // Grid starts at (5,5)
  "position_jitter": 0.1,  // ±0.1m random offset
  "neighbor_connectivity": 8
}
```

- **Grid points:** 100 (10×10)
- **Grid extent:** X: [5, 23], Y: [5, 23]
- **Grid center:** (14, 14)
- **Area:** 18m × 18m

### Base Station

```json
"base_station": {
  "position": [14, 14, 10],  // At grid center (x,y) + 10m height
  "tx_power_dbm": 30,
  "interferers": {
    "enabled": false         // No interfering BSs
  }
}
```

- **Position:** (14, 14, 10) — **directly at the center** of the grid, 10m above ground
- **Height:** 10m (Urban Micro small cell)
- **Type:** Single serving BS, no interferers

### Voronoi Heterogeneous Environment

```json
"channel": {
  "scenario": "3GPP_38.901_UMi_NLOS",  // Fallback
  "center_frequency": 3e9,             // 3 GHz
  "bandwidth": 1e8,                    // 100 MHz
  "n_subcarriers": 256,
  
  "mixed_scenario": {
    "enabled": true,
    "auto_generate": true,
    
    "area_generator": {
      "num_areas": 4,
      "area_bounds": "auto",           // Calculated from grid
      "transition_width": 3,           // 3m transition zones
      "area_types": [
        "shopping_center",             // UMi_NLOS (indoor/enclosed)
        "residential",                 // 50/50 LOS/NLOS
        "office",                      // UMi_NLOS (buildings)
        "park"                         // UMi_LOS (open spaces)
      ]
    }
  }
}
```

The Voronoi cells are **auto-generated at runtime** by `AreaGenerator.m`:
- 4 random seed points within grid bounds
- Each UE position assigned to nearest Voronoi center
- Scenario determined by area type (see mapping above)
- 3m transition zones between cells

### Movement

```json
"movement": {
  "steps_per_point": 400,  // 400 samples per grid point
  "ue_speed": 1.5,         // 1.5 m/s
  "starting_point": "center"
}
```

- **Total samples:** 40,001 (400 × 100 + 1)
- **Random walk:** 8-connected neighbors (includes diagonals)
- **Duration:** ~7.4 hours at 1.5 m/s (1.33s per 2m step)

### Extracted Metrics

All 10 metrics are extracted:

| Metric | Description |
|--------|-------------|
| `rss_wb` | Wideband RSS (dBm) |
| `sinr_wb` | Wideband SINR (dB) |
| `cqi_wb` | Wideband CQI (0–15) |
| `aoa_azimuth` | Azimuth angle of arrival (degrees) |
| `aoa_elevation` | Elevation angle of arrival (degrees) |
| `timing_advance` | First-arrival delay (μs) |
| `path_loss` | Total path loss (dB) |
| `n_multipath` | Number of significant paths |
| `rms_delay_spread` | RMS delay spread (ns) |
| `k_factor` | Rician K-factor (dB) |

---

## How to Run

### 1. Generate Simulation Data (MATLAB)

```matlab
% In MATLAB command window:
cd experiments/09_grid_localization/src/matlab
run_voronoi_10x10
```

This will:
1. Load `voronoi_10x10_config.jsonc`
2. Generate 4 Voronoi areas with random seeds (seed=42 for reproducibility)
3. Run QuaDRiGa channel simulation (40,001 snapshots)
4. Extract all CSI metrics
5. Save to `results/grid_localization/grid_10x10/sim_data_voronoi_<timestamp>/`

**Expected output directory:**
```
results/grid_localization/grid_10x10/sim_data_voronoi_2026-02-23_XX-XX-XX/
├── simulation_data.mat
└── data_generation_config.jsonc
```

**Expected runtime:** ~10–20 minutes (depending on machine)

### 2. Run ML Pipeline (Python)

```bash
cd experiments/09_grid_localization/src/python
python localization_pipeline.py --data-dir "../../../../results/grid_localization/grid_10x10/sim_data_voronoi_<timestamp>"
```

Or replace `<timestamp>` with the actual directory name.

### 3. Run Full Experiment Matrix (Python)

```bash
cd experiments/09_grid_localization/src/python
python run_experiment_matrix.py --data-dirs voronoi10=../../../../results/grid_localization/grid_10x10/sim_data_voronoi_<timestamp> --algorithms xgboost random_forest --metrics RSS+SINR --history 0 1 2 3 --feature-modes raw
```

This will run the full matrix on the Voronoi 10×10 data and compare with:
- Algorithms: XGBoost, Random Forest
- Metrics: RSS+SINR
- History lengths: h=0, 1, 2, 3
- Feature mode: raw

### 4. Compare with Previous 10×10 Results

To compare the Voronoi-based small-cell scenario with the previous uniform NLOS 10×10:

```bash
python run_experiment_matrix.py --data-dirs \
    voronoi10=../../../../results/grid_localization/grid_10x10/sim_data_voronoi_<timestamp> \
    nlos10=../../../../results/grid_localization/grid_10x10/sim_data_NLOS_<previous_timestamp> \
    --algorithms xgboost random_forest mlp \
    --metrics RSS+SINR rss sinr \
    --history 0 1 2 3 \
    --feature-modes raw smart
```

---

## Expected Results

### Hypothesis

The **BS-inside-grid** scenario should produce **significantly different** localization performance compared to the BS-outside-grid scenarios:

1. **More discriminative AOA patterns:** Since the BS is at the grid center, AOA varies dramatically across the grid (UEs surround the BS in all directions)

2. **Better distance discrimination:** UEs have a wide range of distances from the BS (0–12.7m radial), unlike scenarios where the BS is far outside

3. **Lower absolute RSS values:** The BS is closer (max distance ~12.7m vs 30–50m in previous setups), so RSS range is compressed

4. **Mixed LOS/NLOS effects:** Voronoi cells create spatially structured LOS/NLOS patterns, which may help or hurt localization depending on the model's ability to learn these patterns

5. **K-factor variability:** LOS (park) vs NLOS (shopping_center, office) cells will have very different K-factors, providing additional discriminative information

### Performance Predictions

| Metric | Previous 10×10 | Voronoi 10×10 (Predicted) |
|--------|----------------|---------------------------|
| **Best accuracy (h=3)** | 62.8% | **55–70%** (could go either way) |
| **Best MAE (h=3)** | 2.04m | **1.5–2.5m** |
| **Transition impact** | +29.4 pp | **+20–30 pp** (similar or slightly less) |
| **AOA usefulness** | Low (BS far away) | **High (BS at center)** |

The Voronoi scenario introduces **new challenges** (mixed LOS/NLOS) but also **new opportunities** (AOA, distance discrimination).

---

## Validation

Run the validation script to verify config geometry:

```bash
cd experiments/09_grid_localization/src/python
python validate_voronoi_10x10.py
```

Expected output:
```
============================================================
Voronoi 10x10 Config Validation
============================================================
Grid: 10x10, spacing=2.0m
Grid extent: X=[5, 23.0], Y=[5, 23.0]
Grid center: (14.0, 14.0)
Grid area: 18.0m x 18.0m

BS position: (14, 14, 10)
BS inside grid: True ✓
BS height: 10m (UMi small cell)

Steps per point: 400
Total samples: 40001

Voronoi enabled: True
Auto-generate: True
Num areas: 4
Area types: shopping_center, residential, office, park
Transition width: 3m

Interferers enabled: False

Config is VALID ✓
============================================================
```

---

## Files Created

| File | Purpose |
|------|---------|
| `voronoi_10x10_config.jsonc` | Configuration file |
| `run_voronoi_10x10.m` | MATLAB run script |
| `validate_voronoi_10x10.py` | Config validation script |
| `VORONOI_10X10_README.md` | This documentation |

---

## Next Steps

After running and analyzing the Voronoi 10×10 results:

1. **Compare with uniform scenario:** How much does heterogeneous LOS/NLOS affect accuracy?

2. **Use additional metrics:** The 10×10 data includes AOA and timing_advance. Try experiments with:
   ```bash
   --metrics RSS+SINR+aoa_azimuth+aoa_elevation+timing_advance
   ```

3. **Extend to other grid sizes:** Create `voronoi_15x15_config.jsonc`, `voronoi_7x7_config.jsonc` for cross-size comparison

4. **Analyze Voronoi cell confusion:** Are grid points in the same Voronoi cell more likely to be confused?

5. **Tune Voronoi parameters:** Try `num_areas=6`, `transition_width=5`, different area_types

6. **Multi-BS scenario:** Add 2–3 BSs at different grid positions (not just center)

---

## References

- Config: [voronoi_10x10_config.jsonc](../../configs/voronoi_10x10_config.jsonc)
- Run script: [run_voronoi_10x10.m](run_voronoi_10x10.m)
- Main simulation: [generate_simulation_data.m](generate_simulation_data.m)
- Area generator: [AreaGenerator.m](AreaGenerator.m)
- Findings document: [FINDINGS.md](../../../../FINDINGS.md)
