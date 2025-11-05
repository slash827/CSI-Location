# Experiment Level 1: Basics

## 🎯 Learning Goals
- Understand QuaDRiGa workflow
- Learn CSI matrix structure
- Observe how distance affects signal
- Compare LOS vs NLOS scenarios

## 📝 Experiments

### exp01_minimal_setup.m
**Time**: 5 minutes  
**Learn**: Basic QuaDRiGa structure

**What happens**:
- Creates 1 BS and 1 UE (50m apart)
- Generates channel with ~5 multipath taps
- Plots impulse response

**Key output**: CSI matrix [1 × 1 × 5 × 1]

---

### exp02_distance_comparison.m
**Time**: 10 minutes  
**Learn**: Distance vs path loss relationship

**What happens**:
- Tests 3 distances: 25m, 50m, 100m
- Shows path loss increases with distance
- Doubling distance → ~6 dB increase

**Key insight**: CSI magnitude decreases exponentially with distance

---

### exp03_los_vs_nlos.m
**Time**: 10 minutes  
**Learn**: Impact of obstacles (Line-of-Sight vs blocked)

**What happens**:
- Compares LOS vs NLOS at same distance
- LOS: Strong first tap (70-90% of power)
- NLOS: Power spread across many taps

**Key insight**: NLOS → rich scattering → frequency-selective fading

---

## 🚀 Quick Start

```matlab
% Add utils to path (do once)
addpath('../utils');

% Run experiments in order
exp01_minimal_setup
exp02_distance_comparison
exp03_los_vs_nlos
```

## ✅ Before Moving On

Make sure you understand:
- [ ] CSI matrix dimensions: [Rx × Tx × Taps × Snapshots]
- [ ] Complex numbers: magnitude (strength) + phase (delay)
- [ ] Path loss increases with distance
- [ ] LOS vs NLOS characteristics
- [ ] Multipath = multiple signal paths

## ➡️ Next Level

Once comfortable with basics, move to:
**experiments/02_single_ue_analysis/**
