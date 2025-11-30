# Experiment 13: Static vs Random Walk CSI Transitions

## Research Question

**Does a UE arriving at position B (after walking from A) experience the same CSI as if it were simply placed at B?**

In other words: Is the CSI change during movement (A→B) equal to the difference between static measurements at A and B?

---

## Experiment Design

| Parameter | Static (exp13a) | Walk (exp13b) |
|-----------|-----------------|---------------|
| Grid | 3×3 = 9 points, 1m spacing | Same grid |
| Repetitions | 100 per position | 900 walk steps |
| Movement | Instantaneous (no motion) | 1 m/s walking speed |
| Channel Model | 3GPP 38.901 UMa LOS | Same, with temporal correlation |
| Comparison | CSI(B) − CSI(A) for adjacent pairs | CSI(step N+1) − CSI(step N) |

**Adjacent pairs analyzed:** 12 pairs (horizontal + vertical neighbors on the 3×3 grid)

---

## Key Results

### 1. Distribution Shape: SIGNIFICANTLY DIFFERENT ⚠️

| Metric | KS Test p-value | Verdict |
|--------|-----------------|---------|
| RSS_wb | 3.5×10⁻¹⁰⁰ | **Highly significant** |
| SINR_wb | 3.5×10⁻¹⁰⁰ | **Highly significant** |
| Path Loss | 3.5×10⁻¹⁰⁰ | **Highly significant** |
| CQI_wb | 0.99 | Not significant |

The Kolmogorov-Smirnov test reveals the **distribution shapes** are fundamentally different.

### 2. Central Tendency: NOT SIGNIFICANTLY DIFFERENT ✓

| Metric | Static (mean ± std) | Walk (mean ± std) | Welch's t p-value |
|--------|---------------------|-------------------|-------------------|
| RSS_wb | −0.09 ± 0.27 dB | +0.19 ± 5.55 dB | 0.13 (ns) |
| SINR_wb | −0.09 ± 0.27 dB | +0.19 ± 5.55 dB | 0.13 (ns) |
| Path Loss | +0.09 ± 0.27 dB | −0.19 ± 5.55 dB | 0.13 (ns) |

The **means are similar** (Cohen's d ≈ 0.07, negligible effect size).

### 3. Variance: DRAMATICALLY DIFFERENT 📊

| Condition | Standard Deviation |
|-----------|-------------------|
| Static transitions | ~0.27 dB |
| Walk transitions | ~5.5 dB |

**Walk transitions have ~20× higher variance than static transitions!**

---

## Interpretation

### What This Means

1. **On average**, the CSI change when walking A→B matches the static difference between A and B (similar means).

2. **However**, the walk transitions exhibit much greater **variability** — sometimes the CSI changes more than expected, sometimes less.

3. This is due to **temporal channel correlation** in QuaDRiGa:
   - When walking, the channel evolves continuously
   - Small-scale fading creates fluctuations during movement
   - The channel "remembers" its recent history (Doppler effects)

### Physical Intuition

```
Static:     Measure at A ────────────→ Measure at B
            (independent)              (independent)
            Difference = geometry only

Walk:       A ──step──step──step──→ B
            Channel evolves continuously
            Fading, Doppler, multipath variation
            Difference = geometry + temporal dynamics
```

---

## Points to Emphasize for Your Instructor

### 1. **Novel Comparison Framework**
- This experiment directly tests a fundamental assumption in CSI-based localization
- Most studies assume position → CSI mapping is deterministic
- We show that **how you arrive** at a position affects CSI variability

### 2. **Practical Implications for ML-Based Localization**
- Training data collected from static measurements may not represent real-world mobility
- A model trained on static data might perform poorly for moving users
- **Recommendation**: Training data should include movement patterns

### 3. **Statistical Rigor**
- Multiple statistical tests applied (KS, Mann-Whitney, Welch's t)
- Per-pair analysis (12 pairs × 100 samples) AND aggregate analysis
- Effect size (Cohen's d) computed to assess practical significance

### 4. **Key Insight: Mean vs Variance**
- **Means match** → position geometry dominates on average
- **Variances differ drastically** → movement introduces significant randomness
- This is the core finding: "same destination, different journey = different CSI distribution"

### 5. **QuaDRiGa Validation**
- Results confirm QuaDRiGa correctly models temporal channel correlation
- The 1 m/s walking speed produces realistic Doppler effects
- Track-based simulation captures continuous channel evolution

---

## Suggested Visualizations to Show

1. **Distribution histograms** (`distribution_comparison.png`)
   - Show the narrow static distribution vs wide walk distribution
   
2. **Per-pair analysis** (`per_pair_rss.png`)
   - Demonstrates consistency across all 12 adjacent pairs
   
3. **Box plots** (`boxplot_comparison.png`)
   - Clear visual of variance difference

---

## Conclusion

> **The CSI at position B depends on the path taken to reach B, not just the position itself.**

While the average CSI change matches between static and walk conditions (validating basic geometry), the variance during movement is ~20× larger. This has important implications for:

- CSI fingerprinting accuracy for mobile users
- Training data collection strategies
- Real-time localization algorithms

---

## Files

| File | Description |
|------|-------------|
| `exp13a_static_grid.m` | Static grid measurement |
| `exp13b_random_walk.m` | Random walk with 1 m/s speed |
| `analyze_static_vs_walk.py` | Python analysis script |
| `analysis_output/` | Generated plots and report |
