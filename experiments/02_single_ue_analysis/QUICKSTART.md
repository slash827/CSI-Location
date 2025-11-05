# 🚀 Quick Start Guide - Level 2

## What You'll Learn (50 minutes total)

By completing these 3 experiments, you'll understand:
- ✅ How CSI varies across frequencies
- ✅ How to calculate RSS, SINR, and CQI
- ✅ How system parameters affect performance
- ✅ Which metrics to use for ML features

---

## Run the Experiments

### In MATLAB:

```matlab
% Make sure you're in the right folder
cd experiments/02_single_ue_analysis

% Experiment 4: Frequency Response (15 min)
exp04_frequency_response

% Experiment 5: CSI Metrics (15 min)
exp05_csi_metrics

% Experiment 6: Parameter Effects (20 min)
exp06_parameter_effects
```

---

## What to Look For

### Experiment 4 - Frequency Response
**Expected**: 9 plots showing:
- Time-domain taps (5-10 taps typical)
- Frequency-domain CSI (256 subcarriers)
- Peaks and nulls in frequency response
- ~20-40 dB dynamic range

**Console output**: Coherence bandwidth, delay spread

**Key observation**: CSI magnitude varies wildly across frequencies!

---

### Experiment 5 - CSI Metrics
**Expected**: 2 figures with multiple plots showing:
- RSS: Around -30 to -50 dBm (depends on distance)
- SINR: 10-30 dB typical for LOS
- CQI: 8-15 for good channels

**Console output**: Metrics table, distance comparison

**Key observation**: Metrics degrade with distance (for ML!)

---

### Experiment 6 - Parameter Effects
**Expected**: 4 figures showing:
- Wider BW → More frequency selectivity
- Higher Tx power → Better SINR/CQI
- Higher NF → Worse SINR/CQI

**Console output**: Comparison tables for all scenarios

**Key observation**: Parameters affect metrics significantly!

---

## Common Issues

### "Cannot find CSIMetrics"
**Solution**:
```matlab
addpath('../../utils');
```

### Script runs but no plots
**Solution**: Plots might be hidden behind MATLAB window - check taskbar

### Very low CQI (0-3)
**Solution**: This is normal if UE is far away or NLOS - try exp05 which has closer UE

---

## After Completing Level 2

You should be able to answer:

1. **What is frequency-selective fading?**
   → Different frequencies experience different channel gains

2. **What's the difference between RSS and SINR?**
   → RSS = received power, SINR = signal-to-noise ratio

3. **Why does CQI range from 0-15?**
   → Quantized quality metric for selecting modulation/coding

4. **How does distance affect metrics?**
   → RSS, SINR, and CQI all decrease with distance

5. **Which parameters matter for ML?**
   → Use consistent BW, Tx power, NF across all training data

---

## ✓ Completion Checklist

- [ ] Ran exp04_frequency_response successfully
- [ ] Saw frequency-selective fading pattern
- [ ] Ran exp05_csi_metrics successfully  
- [ ] Understood RSS, SINR, CQI values
- [ ] Ran exp06_parameter_effects successfully
- [ ] Compared different scenarios
- [ ] Understood parameter tradeoffs

---

## Next Steps

**Ready for Level 3?**

```matlab
cd ../03_ue_movement
```

You'll learn to simulate moving UE and see how CSI changes with position - this is crucial for your ML project!

---

*Need help? Check `README.md` in this folder or `../../docs/QUICK_REFERENCE.md`*
