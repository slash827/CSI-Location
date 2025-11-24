# NLOS Implementation for CSI-Based Localization
## Dataset Enhancement with Non-Line-of-Sight Scenarios

**Created:** November 15, 2025  
**Purpose:** Extend exp10 dataset with realistic NLOS conditions  
**Target:** 40,000 total samples with 50% LOS + 50% NLOS diversity  
**Status:** 🚧 Implementation in Progress

---

## 🎯 Motivation

### Why Add NLOS Scenarios?

The current exp10 dataset uses **100% LOS (Line-of-Sight)** scenarios, which is unrealistic for indoor environments:

**Current Limitations:**
- ❌ No wall/obstacle modeling
- ❌ No material penetration effects  
- ❌ Overly optimistic signal propagation
- ❌ Model won't generalize to real buildings

**Real Indoor Environments:**
- ✅ 60-80% of indoor links are NLOS
- ✅ Walls, furniture, people cause obstructions
- ✅ Signal penetration varies by material
- ✅ NLOS adds ~15-25 dB path loss

**Expected Benefits:**
1. **Robustness:** Model handles blocked/obstructed paths
2. **Realism:** Matches real-world deployment scenarios
3. **Generalization:** Better performance in unseen environments
4. **Feature Learning:** Model learns NLOS-specific CSI patterns

---

## 📊 Dataset Design Strategy

### Target Dataset Composition

**Total Samples:** 40,000 (same as exp10)  
**Sample Distribution:**

| Condition | Percentage | Samples | Trajectories | Samples/Traj |
|-----------|------------|---------|--------------|--------------|
| **Pure LOS** | 30% | 12,000 | 150 | 80 |
| **Light NLOS** | 25% | 10,000 | 125 | 80 |
| **Moderate NLOS** | 25% | 10,000 | 125 | 80 |
| **Heavy NLOS** | 20% | 8,000 | 100 | 80 |
| **TOTAL** | 100% | **40,000** | **500** | 80 |

### NLOS Severity Levels

#### 1. Pure LOS (30% - Baseline)
- **Scenario:** `3GPP_38.901_UMa_LOS`
- **Obstruction:** None
- **Path Loss:** ~75 dB at 50m
- **Use Case:** Open corridors, large rooms

#### 2. Light NLOS (25% - Minimal Obstruction)
- **Scenario:** `3GPP_38.901_UMa_NLOS`
- **Obstruction Type:** 
  - Single thin obstacle (drywall, glass partition)
  - Grazing angle obstruction (signal skims obstacle)
- **Additional Path Loss:** +10-15 dB
- **RMS Delay Spread:** 20-40 ns
- **Dominant Tap Power:** 40-60% of total
- **Use Case:** Office cubicles, glass partitions

#### 3. Moderate NLOS (25% - Significant Obstruction)
- **Scenario:** `3GPP_38.901_UMa_NLOS`
- **Obstruction Type:**
  - Multiple thin walls
  - Single thick wall (concrete, brick)
  - Furniture clusters
- **Additional Path Loss:** +15-20 dB
- **RMS Delay Spread:** 40-80 ns
- **Dominant Tap Power:** 20-40% of total
- **Use Case:** Multiple rooms, dense office areas

#### 4. Heavy NLOS (20% - Severe Obstruction)
- **Scenario:** `3GPP_38.901_UMa_NLOS`
- **Obstruction Type:**
  - Multiple thick walls
  - Metal obstacles (elevators, server rooms)
  - Deep indoor (far from BS)
- **Additional Path Loss:** +20-30 dB
- **RMS Delay Spread:** 80-150 ns
- **Dominant Tap Power:** 10-30% of total
- **Use Case:** Deep indoor, basement, heavy construction

---

## 🏗️ Technical Implementation

### QuaDRiGa NLOS Scenarios

QuaDRiGa provides built-in NLOS modeling through 3GPP 38.901 standard:

**Available Scenarios:**
```matlab
LOS:  '3GPP_38.901_UMa_LOS'   % Line of sight
NLOS: '3GPP_38.901_UMa_NLOS'  % Non-line of sight
```

**Key Differences:**
- **LOS:** Strong first tap (direct path), few reflections
- **NLOS:** Power spread across many taps, no dominant direct path
- **NLOS:** Higher RMS delay spread (more multipath)
- **NLOS:** More frequency-selective fading

### Implementation Strategy

#### Option 1: Scenario-Based (RECOMMENDED) ✅
**Approach:** Use QuaDRiGa's built-in LOS/NLOS scenarios  
**Pros:**
- ✅ Based on 3GPP standards (realistic)
- ✅ No manual parameter tuning needed
- ✅ Consistent with academic literature
- ✅ Fast implementation

**Cons:**
- ❌ Less control over obstruction details
- ❌ Cannot specify exact wall positions

**Implementation:**
```matlab
% Generate channel with NLOS scenario
l = qd_layout;
l.set_scenario('3GPP_38.901_UMa_NLOS');  % Switch to NLOS
c = l.get_channels();
```

#### Option 2: Explicit Obstacle Modeling
**Approach:** Add walls/obstacles to QuaDRiGa layout  
**Pros:**
- ✅ Full control over obstacle positions
- ✅ Can model specific building layouts
- ✅ Realistic geometry

**Cons:**
- ❌ Complex implementation
- ❌ Slow simulation (ray tracing)
- ❌ Requires building floor plans

**Decision:** Use **Option 1** (scenario-based) for speed and standardization.

---

## 🔧 NLOS Configuration Parameters

### Modified config_nlos_dataset.m

**New Parameters:**
```matlab
% NLOS Distribution
config.nlos_distribution = struct(...
    'pure_los', 0.30, ...       % 30% pure LOS
    'light_nlos', 0.25, ...     % 25% light NLOS
    'moderate_nlos', 0.25, ...  % 25% moderate NLOS
    'heavy_nlos', 0.20 ...      % 20% heavy NLOS
);

% NLOS Scenario Mapping
config.nlos_scenarios = struct(...
    'pure_los', '3GPP_38.901_UMa_LOS', ...
    'light_nlos', '3GPP_38.901_UMa_NLOS', ...
    'moderate_nlos', '3GPP_38.901_UMa_NLOS', ...
    'heavy_nlos', '3GPP_38.901_UMa_NLOS' ...
);
```

**Trajectory Distribution (same as exp10):**
```matlab
config.trajectory_distribution = struct(...
    'linear', 0.20, ...        % 20% straight lines
    'circular', 0.15, ...      % 15% circles
    'zigzag', 0.15, ...        % 15% zigzag
    'random_walk', 0.20, ...   % 20% random walk
    'grid', 0.10, ...          % 10% grid pattern
    'spiral', 0.10, ...        % 10% spiral
    'figure8', 0.10 ...        % 10% figure-8
);
```

---

## 📈 Expected Dataset Characteristics

### Feature Statistics (Predicted)

| Feature | LOS Range | NLOS Range | Change |
|---------|-----------|------------|--------|
| **RSS (dB)** | -80 to -46 | -110 to -60 | -30 to -14 dB lower |
| **SINR (dB)** | 15-25 | 5-15 | 10 dB worse |
| **CQI** | 8-12 | 4-10 | Lower quality |
| **RMS Delay Spread** | 10-30 ns | 20-150 ns | 2-5× higher |
| **Dominant Tap Power** | 60-90% | 10-60% | More spread |

### Spatial Coverage

**Target:** 91.7% coverage of 80m × 80m area (same as exp10)

**Expected Coverage by NLOS Type:**
- Pure LOS: 95%+ (unobstructed access)
- Light NLOS: 90-95% (minimal impact)
- Moderate NLOS: 85-90% (some dead zones)
- Heavy NLOS: 75-85% (more dead zones)

### Feature Distribution Changes

**Expected Impact on ML Features:**

1. **Wideband Features (RSS, SINR, CQI):**
   - ✅ Larger dynamic range (better discrimination)
   - ✅ NLOS adds distinct low-power regime
   - ⚠️ More noise at low SNR

2. **Per-Subcarrier Features:**
   - ✅ More frequency-selective fading patterns
   - ✅ NLOS creates unique "fingerprints"
   - ✅ Rich multipath → richer CSI structure

3. **Channel Magnitude:**
   - ✅ NLOS: More variation across subcarriers
   - ✅ LOS: Flatter frequency response
   - ✅ Enables LOS/NLOS classification

---

## 🤖 Expected ML Model Impact

### Predicted Performance Changes

**Baseline (LOS-only, current):**
- ResNet: MAE = 13.5m, R² = 0.80

**With NLOS (predicted):**

| Scenario | Expected MAE | Expected R² | Notes |
|----------|--------------|-------------|-------|
| **Initial Training** | 16-18m | 0.70-0.75 | Harder problem |
| **After Optimization** | 12-15m | 0.78-0.83 | Better generalization |
| **Best Case** | 10-13m | 0.82-0.87 | NLOS-robust model |

**Reasoning:**
- 📉 Initial drop: NLOS adds complexity and noise
- 📈 Recovery: Model learns NLOS-specific patterns
- 🎯 End result: More robust model, possibly better accuracy

### Training Strategy Recommendations

**1. Data Augmentation Approach:**
```python
# Train on full mixed dataset (LOS + NLOS)
# Model learns to handle both conditions
dataset = load_nlos_dataset()  # 30% LOS + 70% NLOS
model = ResNet()
train(model, dataset, epochs=100)
```

**2. Curriculum Learning Approach:**
```python
# Phase 1: Train on LOS only (easier)
model = ResNet()
train(model, los_data, epochs=50)

# Phase 2: Fine-tune on mixed data (harder)
fine_tune(model, mixed_data, epochs=50)
```

**3. Conditional Training Approach:**
```python
# Add NLOS indicator as input feature
features = [RSS, SINR, H_mag, nlos_indicator]
model = CondResNet()  # Model learns to condition on NLOS
train(model, dataset, epochs=100)
```

**Recommendation:** Start with **Approach 1** (full mixed dataset)

---

## 📁 File Structure

### New Files Created

```
experiments/04_data_generation/
├── exp11_nlos_dataset.m              # Main script (NEW)
├── config_nlos_dataset.m             # NLOS configuration (NEW)
├── NLOS_IMPLEMENTATION.md            # This document (NEW)
├── NLOS_RESULTS_ANALYSIS.md          # Results summary (AFTER GENERATION)
│
└── [existing files]
    ├── exp10_large_dataset.m
    ├── config_large_dataset.m
    └── trajectory_generators.m
```

### Generated Dataset

```
results/exp11_<timestamp>/
├── dataset/
│   ├── train_data.mat                # 32,000 samples
│   ├── val_data.mat                  # 8,000 samples
│   └── nlos_metadata.mat             # NLOS condition per sample (NEW)
│
├── trajectories/
│   └── trajectory_*.png              # Visual verification
│
├── analysis/
│   ├── nlos_distribution.png         # NLOS type histogram
│   ├── feature_comparison_los_nlos.png
│   └── spatial_coverage_by_nlos.png
│
└── experiment_report.txt
```

---

## 🔬 NLOS Metadata

### Additional Data Tracking

For each sample, store:
```matlab
nlos_metadata = struct();
nlos_metadata.condition = [...];      % 1=LOS, 2=Light, 3=Mod, 4=Heavy
nlos_metadata.scenario = {...};       % Scenario name per sample
nlos_metadata.trajectory_type = {...}; % linear/circular/etc.
nlos_metadata.path_loss_excess = [...]; % Extra dB vs LOS
```

**Use Cases:**
- Analyze model performance by NLOS type
- LOS/NLOS classification task
- Conditional training (feed NLOS indicator to model)
- Error analysis (where does model fail?)

---

## 📊 Validation Checks

### Pre-Generation Validation

**1. Configuration Verification:**
```matlab
✓ NLOS distribution sums to 1.0
✓ Trajectory distribution sums to 1.0
✓ Total samples = 500 traj × 80 samples = 40,000
✓ Train/val split = 32,000 / 8,000
```

**2. Scenario Testing:**
```matlab
✓ Test each NLOS scenario generates valid channels
✓ Verify path loss ranges match expectations
✓ Check RMS delay spread values
```

### Post-Generation Validation

**1. Sample Count:**
```matlab
✓ Total samples = 40,000
✓ Pure LOS ≈ 12,000 (30%)
✓ Light NLOS ≈ 10,000 (25%)
✓ Moderate NLOS ≈ 10,000 (25%)
✓ Heavy NLOS ≈ 8,000 (20%)
```

**2. Feature Quality:**
```matlab
✓ RSS dynamic range > 30 dB
✓ No NaN/Inf values
✓ Realistic SINR values (not negative at dB scale)
✓ CQI in valid range [0, 15]
```

**3. Spatial Coverage:**
```matlab
✓ Coverage > 85% of 80×80m area
✓ No large gaps (>10m) in coverage
✓ Reasonable position distribution
```

**4. NLOS Distribution:**
```matlab
✓ Compare actual vs target distribution
✓ Verify NLOS types properly labeled
✓ Check path loss differences match theory
```

---

## ⏱️ Generation Timeline

### Estimated Runtime

**Based on exp10 performance:**
- exp10: 500 traj × 80 samples = 40,000 samples in ~11 minutes
- exp11 (NLOS): Similar complexity, expect **10-15 minutes**

**Breakdown:**
- Trajectory generation: ~2 minutes
- CSI simulation: ~8-10 minutes (same as exp10)
- Data saving: ~1-2 minutes
- Plotting/analysis: ~2 minutes

**Total: 13-17 minutes**

---

## 🎯 Success Criteria

### Dataset Quality Metrics

**1. Sample Distribution:**
- ✅ 40,000 total samples (32K train + 8K val)
- ✅ NLOS distribution matches target (±2%)
- ✅ All trajectory types represented

**2. Feature Quality:**
- ✅ RSS dynamic range ≥ 30 dB
- ✅ SINR range: 5-25 dB (reasonable)
- ✅ No data corruption (NaN/Inf)

**3. Spatial Coverage:**
- ✅ Coverage ≥ 85% of 80×80m area
- ✅ Diverse positions across all quadrants

**4. NLOS Characteristics:**
- ✅ NLOS path loss: +10-30 dB vs LOS
- ✅ NLOS delay spread: 2-5× higher than LOS
- ✅ NLOS dominant tap: <60% vs LOS >60%

### ML Model Success Criteria

**Phase 1: Initial Training (Expected)**
- 🎯 MAE ≤ 18m (acceptable given added complexity)
- 🎯 R² ≥ 0.70 (good starting point)

**Phase 2: Optimized Training (Target)**
- 🎯 MAE ≤ 15m (match current LOS-only performance)
- 🎯 R² ≥ 0.78 (close to current 0.80)

**Phase 3: Advanced Optimization (Stretch Goal)**
- 🎯 MAE ≤ 12m (exceed current performance!)
- 🎯 R² ≥ 0.82 (new state-of-the-art)

---

## 📝 Implementation Checklist

### Step 1: Configuration ✅ (DONE)
- [x] Create `config_nlos_dataset.m`
- [x] Define NLOS distribution
- [x] Set scenario mappings
- [x] Configure metadata tracking

### Step 2: Script Development 🚧 (IN PROGRESS)
- [ ] Create `exp11_nlos_dataset.m`
- [ ] Add NLOS scenario assignment logic
- [ ] Implement metadata tracking
- [ ] Add NLOS-specific validation

### Step 3: Dataset Generation ⏳ (PENDING)
- [ ] Run `exp11_nlos_dataset.m`
- [ ] Validate sample counts
- [ ] Check NLOS distribution
- [ ] Verify feature quality

### Step 4: Analysis & Visualization ⏳ (PENDING)
- [ ] Generate NLOS distribution plots
- [ ] Compare LOS vs NLOS features
- [ ] Analyze spatial coverage
- [ ] Create summary report

### Step 5: ML Pipeline Update ⏳ (PENDING)
- [ ] Update `data_loader.py` for NLOS metadata
- [ ] Add NLOS visualization to EDA
- [ ] Test with existing models
- [ ] Document results

### Step 6: Model Training ⏳ (PENDING)
- [ ] Train baseline models on NLOS dataset
- [ ] Compare with LOS-only results
- [ ] Optimize hyperparameters
- [ ] Document performance changes

---

## 🚀 Next Steps

### Immediate (Today)
1. ✅ Create this documentation
2. 🚧 Create `config_nlos_dataset.m`
3. 🚧 Create `exp11_nlos_dataset.m`
4. ⏳ Test with small dataset (50 traj)

### Short-term (This Week)
1. ⏳ Generate full NLOS dataset (500 traj)
2. ⏳ Validate dataset quality
3. ⏳ Update ML pipeline for NLOS
4. ⏳ Train baseline models

### Medium-term (Next Week)
1. ⏳ Compare LOS-only vs NLOS-enhanced results
2. ⏳ Optimize models for NLOS
3. ⏳ Analyze performance by NLOS type
4. ⏳ Document findings in `NLOS_RESULTS_ANALYSIS.md`

---

## 📚 References

### QuaDRiGa Documentation
- 3GPP 38.901 scenarios: UMa (Urban Macro) LOS/NLOS
- Channel generation: `l.get_channels()`
- Scenario setting: `l.set_scenario()`

### 3GPP Standards
- **3GPP 38.901:** Study on channel model for frequencies from 0.5 to 100 GHz
- **UMa (Urban Macro):** Macro cell deployment in urban areas
- **LOS/NLOS:** Standardized path loss and delay spread models

### Academic Literature
- CSI fingerprinting for indoor localization
- NLOS mitigation techniques
- Deep learning for NLOS-robust positioning

---

## 📧 Contact & Questions

**Project:** CSI-Location  
**Experiment:** exp11 - NLOS Dataset Generation  
**Document:** NLOS_IMPLEMENTATION.md  

**Questions? Issues?**
- Check existing exp03 (LOS vs NLOS comparison)
- Review QuaDRiGa documentation
- Refer to `utils/ExperimentUtils.m` for helper functions

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-15 | Initial document created |
| 1.1 | TBD | After dataset generation - add results |
| 1.2 | TBD | After ML training - add performance analysis |

---

**Status:** 📝 Documentation complete, ready for implementation  
**Next:** Create configuration and generation scripts  
**Expected Completion:** Dataset ready for ML training within 1 day

---

*End of NLOS Implementation Document*
