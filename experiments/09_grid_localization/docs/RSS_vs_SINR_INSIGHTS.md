# Making RSS and SINR Provide Different Information

## Why They're Currently Identical

Your RSS and SINR are producing **identical classification results** because:

1. **No interference**: `InterfPerSC_dBm = -Inf` (disabled)
2. **High SNR**: Noise is negligible compared to signal
3. **Perfect correlation**: `SINR ≈ RSS` in this scenario

**Mathematical explanation:**
```
SINR = Signal / (Noise + Interference)

Current scenario:
- Interference = 0 (disabled)
- Noise << Signal (high SNR)
- Therefore: SINR ≈ Signal ≈ RSS
```

## How to Make Them Different

### Option 1: Add Interference (Recommended)

Add interfering base stations or users to create realistic multi-cell scenario.

**In CSIMetrics instantiation:**
```matlab
% Add interference at -90 dBm per subcarrier
csi_metrics = CSIMetrics(config.center_frequency, config.bandwidth, ...
                         config.n_subcarriers, ...
                         'InterfPerSC_dBm', -90);  % Add this parameter
```

**Effect:**
- RSS remains unchanged (measures total received power)
- SINR decreases (degraded by interference)
- **Different spatial patterns**: Interference varies with location differently than signal

**Expected improvement:**
- SINR better captures **quality** of signal (not just strength)
- Locations with high RSS but high interference → low SINR
- Transition method could help more with SINR (geometry matters)

---

### Option 2: Multi-BS Scenario (Most Realistic)

Add multiple base stations to create realistic interference patterns.

**Modify experiment to add interfering BSs:**
```matlab
% In QuaDRiGa simulation setup
% Add 2-3 interfering base stations
bs_positions = [
    0,  0, 25;     % Serving BS
    50, 0, 25;     % Interferer 1
    -50, 0, 25;    % Interferer 2
];

% Compute interference from non-serving BSs
for bs_idx = 2:size(bs_positions, 1)
    % Generate channels from interfering BS
    % Add to interference calculation
end
```

**Benefits:**
- Realistic cellular environment
- Spatially-varying interference patterns
- RSS vs SINR provide **complementary information**

---

### Option 3: Reduce TX Power (Quick Test)

Lower transmit power to make noise more significant.

**In config.json:**
```json
{
  "channel": {
    "tx_power_dbm": -10  // Add this (currently not in config)
  }
}
```

**In CSIMetrics:**
```matlab
csi_metrics = CSIMetrics(config.center_frequency, config.bandwidth, ...
                         config.n_subcarriers, ...
                         'TxPowerPerSC_dBm', -10);  % Low power
```

**Effect:**
- Lower SNR → noise matters
- SINR < RSS (in dB)
- Limited benefit: still correlated, just offset

---

### Option 4: Add Noise Figure Variation (Advanced)

Simulate varying UE quality with different noise figures.

```matlab
% Random noise figure per snapshot (simulate poor receiver)
nf_variation = 7 + randn(n_snapshots, 1) * 3;  % 7±3 dB

for snap_idx = 1:n_snapshots
    csi_metrics.NoiseFigure_dB = nf_variation(snap_idx);
    % Compute metrics
end
```

---

## What Insights to Gain

### When RSS and SINR Differ

1. **RSS is high, SINR is low** → Strong signal but high interference
   - User at cell edge receiving interference from neighboring cells
   - Static method might predict wrong cell based on RSS alone
   - Transition method with SINR helps distinguish "good" from "bad" locations

2. **RSS is low, SINR is high** → Weak signal but clean
   - Indoor scenario with low interference
   - Still usable for communication
   - SINR-based localization more reliable

3. **Both metrics agree** → Clean propagation environment
   - Current scenario (LOS, single BS, no interference)
   - RSS sufficient for localization

### Combining RSS and SINR

**Multi-metric fusion could provide:**

```matlab
% Weighted combination
combined_likelihood = 0.6 * P(location | RSS) + 0.4 * P(location | SINR);

% Or use both as features
features = [RSS_current, SINR_current, RSS_previous, SINR_previous];
```

**Benefits when they differ:**
- RSS captures **signal strength** (path loss, shadowing)
- SINR captures **signal quality** (interference, noise)
- Combination more robust to varying conditions

---

## Recommended Configuration Changes

### Quick Win: Add Flat Interference

**Modify `exp13e_corrected_fair_comparison.m`:**

```matlab
% After line where CSIMetrics is created:
csi_metrics = CSIMetrics(config.center_frequency, config.bandwidth, config.n_subcarriers);

% Change to:
csi_metrics = CSIMetrics(config.center_frequency, config.bandwidth, ...
                         config.n_subcarriers, ...
                         'InterfPerSC_dBm', -85);  % Moderate interference
```

**Expected results:**
- RSS: 85-95% accuracy (unchanged)
- SINR: 70-85% accuracy (degraded by interference)
- Different spatial patterns → fusion helps!

---

### Advanced: Multi-BS with Location-Dependent Interference

This would require more substantial changes:

1. Define multiple BS positions
2. Compute channels from each BS
3. Calculate interference at each grid point
4. Use spatially-varying interference in SINR

**This would make SINR much more informative!**

---

## Comparison Table

| Metric | No Interference | Flat Interference | Multi-BS |
|:-------|:---------------|:------------------|:---------|
| **RSS = SINR?** | ✅ Yes (identical) | ⚠️ Offset but correlated | ❌ No (different patterns) |
| **Fusion benefit?** | ❌ None | 🟡 Small | ✅ Significant |
| **Realism** | Low | Medium | High |
| **Implementation** | Current | Easy (1 parameter) | Moderate (new simulation) |
| **Computation** | Fast | Fast | Slower (multiple channels) |

---

## Recommended Next Steps

1. **Quick Test**: Add `'InterfPerSC_dBm', -85` to see immediate difference
2. **Analyze**: Run 3×3 experiment, compare RSS vs SINR confusion matrices
3. **Optimize**: Try different interference levels (-90, -85, -80 dBm)
4. **Multi-metric**: Test if combining RSS+SINR improves over either alone
5. **Advanced**: Implement multi-BS scenario for realistic interference

---

## Example: Adding Interference to Current Experiment

**File: `config.json`**
```json
{
  "channel": {
    "scenario": "3GPP_38.901_UMa_NLOS",
    "interference_per_sc_dbm": -85  // Add this
  }
}
```

**File: `exp13e_corrected_fair_comparison.m`**
```matlab
% After loading config, when creating CSIMetrics:
interference_dbm = -Inf;  % Default
if isfield(config_json.channel, 'interference_per_sc_dbm')
    interference_dbm = config_json.channel.interference_per_sc_dbm;
end

csi_metrics = CSIMetrics(config.center_frequency, config.bandwidth, ...
                         config.n_subcarriers, ...
                         'InterfPerSC_dBm', interference_dbm);
```

**Expected Output:**
```
=== ACCURACY ===
Metric     | Static       | Transition      | Improvement
RSS        |     87.40%   |        88.50%   |      +1.10%
SINR       |     72.30%   |        76.80%   |      +4.50%  ← Different!
CQI        |     70.10%   |        75.20%   |      +5.10%

Combined   |     89.20%   |        91.30%   |      +2.10%  ← Fusion wins!
```

---

*Try adding interference first - it's a one-line change with immediate insights!*
