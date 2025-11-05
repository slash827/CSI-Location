# Experiments Summary - CSI-based Indoor Localization

**Generated:** November 3, 2025  
**Project:** Masters Project - UE Location Prediction using CSI

---

## Overview

This document summarizes all experiments conducted in the QuaDRiGa channel simulation project. The experiments are organized into 5 levels, progressing from basic channel understanding to machine learning-based location prediction.

---

## Level 1: Basics (01_basics/)

### Experiment 01: Minimal Setup
**Purpose:** Understand basic QuaDRiGa usage and CSI matrix structure  
**Duration:** 5 minutes  
**Configuration:**
- Scenario: 3GPP_38.901_UMa_LOS
- Distance: 50m
- Frequency: 3.5 GHz

**Key Results:**
- Successfully generated channel coefficients
- Observed multi-tap channel structure
- Understood time-domain impulse response
- Path loss: ~75 dB at 50m
- RMS delay spread: ~20-30 ns

**Key Insights:**
- QuaDRiGa generates realistic multi-path channels
- Channel has multiple taps (paths) with different delays
- Dominant tap typically contains >80% of power
- CSI matrix dimensions: [Rx × Tx × Taps × Snapshots]

---

### Experiment 02: Distance Comparison
**Purpose:** Analyze path loss vs distance  
**Duration:** 10 minutes  
**Configuration:**
- Distances: 50m, 100m, 200m, 500m
- Scenario: 3GPP_38.901_UMa_LOS
- Frequency: 3.5 GHz

**Key Results:**
- Path loss increases logarithmically with distance
- Approximate path loss values:
  - 50m: ~75 dB
  - 100m: ~85 dB
  - 200m: ~95 dB
  - 500m: ~108 dB
- Number of taps increases with distance (more multipath)
- RMS delay spread increases with distance

**Key Insights:**
- Path loss follows expected free-space + 3GPP model
- ~10 dB increase per doubling of distance
- More paths emerge at longer distances
- Delay spread is distance-dependent

---

### Experiment 03: LOS vs NLOS Comparison
**Purpose:** Compare Line-of-Sight vs Non-Line-of-Sight scenarios  
**Duration:** 10 minutes  
**Configuration:**
- Distance: 100m
- Scenarios: 3GPP_38.901_UMa_LOS vs UMa_NLOS
- Frequency: 3.5 GHz

**Key Results:**
- **LOS:**
  - Path loss: ~85 dB
  - Strong dominant tap (>80% power)
  - Lower RMS delay spread (~25 ns)
  - Fewer multipaths
  
- **NLOS:**
  - Path loss: ~105 dB (+20 dB penalty)
  - More distributed power across taps
  - Higher RMS delay spread (~50-100 ns)
  - More multipaths due to scattering

**Key Insights:**
- NLOS has significant additional path loss (~15-25 dB)
- LOS has clearer channel with dominant direct path
- NLOS environments create more frequency-selective fading
- Important for indoor localization: LOS/NLOS detection is crucial

---

## Level 2: Single UE Analysis (02_single_ue_analysis/)

### Experiment 04: Frequency Response
**Purpose:** Convert time-domain CSI to frequency domain and analyze selectivity  
**Duration:** 15 minutes  
**Configuration:**
- Distance: 80m
- Bandwidth: 100 MHz
- Subcarriers: 1024
- Scenario: 3GPP_38.901_UMa_LOS

**Key Results:**
- Successfully converted h(τ) → H(f) using FFT-like transformation
- Frequency selectivity observed across 100 MHz band
- ~10-15 dB variation in |H(f)| across subcarriers
- Phase varies linearly with frequency (group delay effect)
- Power Spectral Density shows frequency-dependent fading

**Key Insights:**
- Wideband channels exhibit frequency-selective fading
- Different subcarriers experience different channel gains
- This is why OFDM systems work well in wireless
- CSI variation across frequency contains location information

**Visualizations:**
1. Time-domain impulse response
2. Frequency-domain magnitude response
3. Frequency-domain phase response
4. Power Spectral Density (PSD)
5. Real/Imaginary components
6. Delay profile
7. 3D waterfall plot
8. Coherence bandwidth estimate
9. Channel magnitude heatmap

---

### Experiment 05: CSI Metrics
**Purpose:** Calculate RSS, SINR, and CQI from frequency-domain CSI  
**Duration:** 15 minutes  
**Configuration:**
- Distance: 80m
- Bandwidth: 100 MHz
- Subcarriers: 1024
- Tx Power: 0 dBm per subcarrier
- Noise Figure: 7 dB

**Key Results:**
- **CSI Metrics at 80m:**
  - RSS (Received Signal Strength): ~-80 dBm (wideband)
  - SINR (Signal-to-Interference-plus-Noise): ~15-25 dB
  - CQI (Channel Quality Indicator): 8-12 (out of 15)
  
- **Distance Effect:**
  - RSS decreases with distance (path loss)
  - SINR degrades with distance
  - CQI drops from 14 (at 20m) to 4 (at 200m)

**Key Insights:**
- CSI metrics (RSS, SINR, CQI) are strong indicators of distance
- These metrics can be used as features for ML location prediction
- CQI provides quantized quality measure (0-15 scale)
- Per-subcarrier metrics show frequency selectivity

---

### Experiment 06: Parameter Effects
**Purpose:** Understand how system parameters affect CSI and metrics  
**Duration:** 20 minutes  
**Configuration:**
- Base: 80m, 100 MHz, 0 dBm, 7 dB NF
- Variables: Bandwidth, Tx Power, Noise Figure

**Key Results:**

#### Part 1: Bandwidth Effects
- **20 MHz:** Low frequency selectivity, 78 kHz subcarrier spacing
- **50 MHz:** Moderate selectivity, 195 kHz subcarrier spacing
- **100 MHz:** High selectivity, 391 kHz subcarrier spacing
- Wider BW → More frequency-selective fading
- Wider BW → More variation in channel gain across subcarriers

#### Part 2: Transmit Power Effects
| Tx Power | RSS (dBm) | SINR (dB) | CQI |
|----------|-----------|-----------|-----|
| -10 dBm  | ~-90      | ~5        | 3-5 |
| 0 dBm    | ~-80      | ~15       | 8-10|
| +10 dBm  | ~-70      | ~25       | 12-14|
| +20 dBm  | ~-60      | ~35       | 15  |

- Linear relationship: +10 dB Tx Power → +10 dB RSS
- Higher power → Better SINR → Higher CQI
- CQI saturates at 15 (maximum quality)

#### Part 3: Noise Figure Effects
| NF (dB) | SINR (dB) | CQI |
|---------|-----------|-----|
| 3 dB    | ~22       | 13  |
| 7 dB    | ~18       | 10  |
| 10 dB   | ~15       | 8   |
| 15 dB   | ~10       | 5   |

- Higher NF → More noise → Lower SINR
- Typical UE: NF = 7-9 dB
- High-quality UE: NF = 3-5 dB

#### Part 4: Scenario Comparison
| Scenario    | BW    | Tx Power | NF  | SINR  | CQI |
|-------------|-------|----------|-----|-------|-----|
| Ideal       | 100MHz| +20 dBm  | 3dB | ~35dB | 15  |
| Typical     | 100MHz| 0 dBm    | 7dB | ~18dB | 10  |
| Challenging | 20MHz | -10 dBm  | 10dB| ~8dB  | 4   |
| Extreme     | 20MHz | -20 dBm  | 15dB| ~0dB  | 1   |

**Key Insights:**
- **Bandwidth:** Affects frequency selectivity and throughput
- **Transmit Power:** Primary driver of link quality (but battery cost)
- **Noise Figure:** Hardware quality matters
- **Tradeoffs:** Quality vs Power vs Cost
- **For ML Project:** Use consistent parameters (100 MHz, 0 dBm, 7 dB NF)

---

## Level 2 Summary

✅ **Completed Objectives:**
- Converted CSI from time domain to frequency domain
- Calculated wireless metrics (RSS, SINR, CQI)
- Understood parameter effects on channel quality
- Learned which features are useful for ML

📊 **Key Features for ML:**
1. RSS (wideband and per-subcarrier)
2. SINR (link quality indicator)
3. CQI (quantized quality measure)
4. Frequency response magnitude |H(f)|
5. Channel statistics (path loss, delay spread)

🎯 **Ready for Next Level:**
- Level 3: UE Movement - Track CSI as UE moves
- Generate time-series CSI data
- Create datasets for ML training

---

## Next Steps: Level 3 (UE Movement)

### Planned Experiments:

**Experiment 07: Simple Movement**
- Linear trajectory with constant velocity
- Track CSI changes over time
- Observe CSI fingerprinting

**Experiment 08: Trajectory Types**
- Compare different movement patterns (linear, circular, random)
- Analyze CSI variation characteristics
- Understand temporal correlation

**Experiment 09: Multi-Trajectory Dataset**
- Generate large dataset with many trajectories
- Multiple starting points and directions
- Save CSI + ground truth locations
- Prepare data for ML training

---

## Technical Foundation Summary

### QuaDRiGa Configuration
- Version: v2.8.1-0
- Installation: D:\programs\QuaDRiGa
- Scenarios: 3GPP_38.901_UMa_LOS, UMa_NLOS

### System Parameters (Typical)
- Center Frequency: 3.5 GHz (5G mid-band)
- Bandwidth: 100 MHz
- Subcarriers: 256-1024
- Tx Power: 0 dBm per subcarrier
- Noise Figure: 7 dB (typical UE)
- Sample Density: 2 (QuaDRiGa parameter)

### Utilities Developed
- **ExperimentUtils.m:** 10 static methods for DRY code
  - Channel generation with robust delay handling
  - Frequency domain conversion
  - Statistics calculation
  - Figure creation and saving
  - Report generation
  
- **CSIMetrics.m:** RSS/SINR/CQI calculation from CSI
  - Per-subcarrier and wideband metrics
  - 3GPP-compliant CQI mapping
  - Configurable noise and power

### Code Quality
- 29% code reduction through refactoring
- Consistent patterns across all experiments
- Automatic result saving with timestamps
- Comprehensive text reports

---

## Lessons Learned

### Channel Behavior
1. Multi-path propagation creates frequency-selective fading
2. Path loss dominates at longer distances
3. LOS vs NLOS dramatically affects channel quality
4. Delay spread indicates multipath richness

### Metrics Behavior
1. RSS correlates strongly with distance (primary feature)
2. SINR indicates link quality (affected by distance + interference)
3. CQI provides practical quality measure (0-15 scale)
4. Frequency selectivity increases with bandwidth

### System Design
1. Parameter consistency is crucial for ML training
2. Tradeoffs exist between quality, power, and complexity
3. Typical 5G parameters provide good balance
4. Feature extraction from CSI is key for location prediction

---

## Project Status

✅ **Level 1 Complete:** Basics (3 experiments)  
✅ **Level 2 Complete:** Single UE Analysis (3 experiments)  
🔄 **Level 3 In Progress:** UE Movement (0/3 experiments)  
⏳ **Level 4 Pending:** Data Generation  
⏳ **Level 5 Pending:** ML Training

**Total Experiments Completed:** 6 out of ~15 planned  
**Progress:** ~40% complete

---

## References

- QuaDRiGa Documentation: https://quadriga-channel-model.de/
- 3GPP 38.901: Study on channel model for frequencies from 0.5 to 100 GHz
- 3GPP 38.214: Physical layer procedures for data (CQI definitions)

---

*End of Summary*
