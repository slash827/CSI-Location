# Experiment Level 2: Single UE Analysis

## 🎯 Learning Goals
- Convert CSI to frequency domain
- Calculate wireless metrics (RSS, SINR, CQI)
- Understand frequency-selective fading
- Use CSIMetrics class
- Understand parameter effects

## 📝 Experiments

### exp04_frequency_response.m
**Time**: 15 minutes  
**Learn**: Time to frequency domain conversion

**What happens**:
- Converts channel taps to frequency-domain CSI
- Shows frequency-selective fading (peaks and nulls)
- Estimates coherence bandwidth
- 9 comprehensive plots

**Key insight**: Different frequencies experience different fading → ML can use this pattern!

---

### exp05_csi_metrics.m
**Time**: 15 minutes  
**Learn**: Calculate practical wireless metrics

**What happens**:
- RSS (Received Signal Strength) in dBm
- SINR (Signal-to-Interference-plus-Noise Ratio) in dB
- CQI (Channel Quality Indicator) 0-15
- Uses CSIMetrics class
- Shows per-subcarrier and wideband values
- Tests distance effects

**Key insight**: These metrics are what you'll use as ML features!

---

### exp06_parameter_effects.m
**Time**: 20 minutes  
**Learn**: How system parameters affect quality

**What happens**:
- Tests 3 bandwidths (20, 50, 100 MHz)
- Tests 4 transmit powers (-10 to 20 dBm)
- Tests 4 noise figures (3 to 15 dB)
- Compares 4 scenarios (Ideal, Typical, Challenging, Extreme)

**Key insight**: Understand tradeoffs and choose consistent parameters for ML training

---

## 🚀 Quick Start

```matlab
% Navigate to this folder
cd experiments/02_single_ue_analysis

% Run experiments in order
exp04_frequency_response
exp05_csi_metrics
exp06_parameter_effects
```

## ✅ Before Moving On

Make sure you understand:
- [ ] Time → Frequency domain conversion
- [ ] RSS, SINR, CQI meanings and ranges
- [ ] Frequency-selective fading
- [ ] How to use CSIMetrics class
- [ ] Parameter effects on metrics
- [ ] Per-subcarrier vs wideband metrics

## 📚 Key Concepts

- **Frequency domain**: H(f) = Σ h_l * exp(-j2πfτ_l)
- **RSS**: Total received power (dBm)
- **SINR**: Signal / (Noise + Interference) ratio (dB)
- **CQI**: Quality metric (0-15) for scheduling decisions
- **Subcarrier**: Individual frequency component in OFDM
- **Wideband**: Averaged across all subcarriers

## 💡 Key Takeaways for ML

1. **Features to extract**:
   - RSS mean, std, min, max
   - SINR mean, std, range
   - CQI mean, mode, distribution
   - CSI magnitude statistics
   - Frequency selectivity metrics

2. **Why these matter**:
   - Different locations → Different CSI patterns
   - Multipath changes with position
   - ML learns location → CSI mapping

3. **Consistent parameters**:
   - Use same BW, Tx power, NF for all training
   - Typical: 100 MHz, 0 dBm, 7 dB NF

## ➡️ Next Level

Ready for movement? Go to:
**experiments/03_ue_movement/**

Learn how CSI changes as UE moves!
