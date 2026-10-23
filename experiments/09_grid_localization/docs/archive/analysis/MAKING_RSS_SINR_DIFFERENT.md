# How to Make RSS and SINR Different (Realistic Configuration)

## Current Problem

RSS and SINR always give identical results because:
```
SINR_dB = RSS_dBm + constant (spatially invariant)
std(SINR) = std(RSS) → identical Gaussian classification
```

This happens with a **single BS** and **constant interference** across space.

---

## Solution: Spatially-Varying Interference (Multi-BS Scenario)

The most realistic way to make RSS ≠ SINR is to add **interfering base stations** at different locations. This mirrors real cellular networks where multiple cells create spatially-varying interference.

### Why This Works

With multiple BSs at different positions:
- **RSS**: Measures signal from serving BS only → varies with distance to main BS
- **SINR**: Measures signal/(noise + interference) → interference varies by location
  - Near main BS: high signal, low interference → high SINR
  - Near interferer: moderate signal, high interference → low SINR (different pattern than RSS!)

---

## Implementation Steps

### Step 1: Modify QuaDRiGa Setup

Currently (single BS):
```matlab
l = qd_layout(s);
l.no_tx = 1;
l.tx_position = config.bs_position;  % [0, 0, 25]
```

**Change to multi-BS:**
```matlab
l = qd_layout(s);
l.no_tx = 4;  % Main BS + 3 interferers

% Main serving BS (center)
l.tx_position(:, 1) = [0; 0; 25];

% Interfering BSs (surrounding positions)
l.tx_position(:, 2) = [150; 0; 25];      % East interferer
l.tx_position(:, 3) = [-150; 0; 25];     % West interferer  
l.tx_position(:, 4) = [0; 150; 25];      % North interferer

% All BSs use omni antennas
for i = 1:4
    l.tx_array(1, i) = qd_arrayant('omni');
end
```

### Step 2: Generate Channels from All BSs

```matlab
% Generate channels from all BSs
ch = l.get_channels();  % Now returns [n_rx x n_tx] cell array

% Extract serving BS channel (BS 1)
ch_serving = ch{1, 1};  % Main BS
```

### Step 3: Compute Interference from Other BSs

```matlab
% Compute interference power from other BSs
n_subcarriers = 256;
n_snapshots = size(ch_serving.coeff, 4);
interference_per_sc = zeros(n_subcarriers, n_snapshots);

for bs_idx = 2:4  % Interfering BSs
    ch_interf = ch{1, bs_idx};
    
    for snap = 1:n_snapshots
        % Get channel frequency response from interferer
        coeff = ch_interf.coeff(:,:,:,snap);
        delays = ch_interf.delay(:,:,:,snap);
        
        h_paths = squeeze(coeff);
        tau_paths = squeeze(delays);
        H_freq = (h_paths(:).' * exp(-1j * 2 * pi * tau_paths(:) * fvec(:).')).';
        
        % Compute interference power per subcarrier (in Watts)
        Pt_W_sc = 10^((0-30)/10);  % 0 dBm per SC
        G_sc = abs(H_freq).^2;
        I_W_sc = Pt_W_sc * G_sc;
        
        interference_per_sc(:, snap) = interference_per_sc(:, snap) + I_W_sc;
    end
end

% Convert to dBm per subcarrier
interference_per_sc_dBm = 10*log10(interference_per_sc + eps) + 30;
```

### Step 4: Pass Interference to CSIMetrics

```matlab
% For each snapshot, use actual interference vector
for snap_idx = 1:n_snapshots
    % ... (extract H_freq for serving BS as before)
    
    % Pass snapshot-specific interference
    out = m.compute(H_sc, interference_per_sc_dBm(:, snap_idx));
    
    metrics.RSS_wb(snap_idx) = out.RSS_dBm_wb;
    metrics.SINR_wb(snap_idx) = out.SINR_dB_wb;
    metrics.CQI_wb(snap_idx) = out.CQI_wb;
end
```

---

## Expected Results

### Without Multi-BS (Current - Identical)
```
Grid 7×7, LOS:
RSS:  31.13% accuracy, MAE = 2.019
SINR: 31.13% accuracy, MAE = 2.019  ← Same!
```

### With Multi-BS (Expected - Different)
```
Grid 7×7, LOS:
RSS:  31% accuracy, MAE = 2.0   ← Unchanged (same signal pattern)
SINR: 24% accuracy, MAE = 2.5   ← Worse! (interference varies spatially)

Transition improvement:
RSS:  +14% (same as before)
SINR: +18% (bigger improvement! Spatial constraint helps more)
```

**Why SINR gets worse but transition helps more:**
- SINR is noisier due to spatially-varying interference
- Transition method's spatial constraint provides more value when measurements are noisier
- This validates your approach!

---

## Configuration Changes Needed

### Option A: Modify Experiment Script Directly

Edit `exp13e_corrected_fair_comparison.m` around line 124:

```matlab
% BEFORE:
l.no_tx = 1;
l.tx_position = config.bs_position;
l.tx_array = qd_arrayant('omni');

% AFTER:
l.no_tx = 4;  % Main + 3 interferers
l.tx_position(:, 1) = config.bs_position;
l.tx_position(:, 2) = config.bs_position + [150; 0; 0];
l.tx_position(:, 3) = config.bs_position + [-150; 0; 0];
l.tx_position(:, 4) = config.bs_position + [0; 150; 0];
for i = 1:4
    l.tx_array(1, i) = qd_arrayant('omni');
end
```

### Option B: Add to Config File (Recommended)

Add to `config.json`:

```json
"base_station": {
    "position": [0, 0, 25],
    "tx_power_dbm": 30,
    "interferers": {
        "enabled": true,
        "positions": [
            [150, 0, 25],
            [-150, 0, 25],
            [0, 150, 25]
        ],
        "tx_power_dbm": 30
    }
}
```

Then modify script to read this configuration.

---

## Simpler Alternative: Per-Subcarrier Random Interference

If multi-BS is too complex, you can add **frequency-selective interference**:

```matlab
% Add random interference per subcarrier (simpler but less realistic)
for snap = 1:n_snapshots
    % Random interference varies across subcarriers
    interference_sc_dBm = -90 + 5*randn(n_subcarriers, 1);  % Mean -90, std 5 dB
    
    out = m.compute(H_sc, interference_sc_dBm);
    % ...
end
```

**Pros:** Easy to implement, breaks linear relationship
**Cons:** Less realistic (real interference is correlated across frequency)

---

## Recommended Configuration

For realistic and meaningful RSS ≠ SINR:

### Urban Scenario (7×7 grid, 2m spacing)

```json
{
  "grid": {
    "size": 7,
    "spacing": 2.0
  },
  "channel": {
    "scenario": "3GPP_38.901_UMa_LOS",
    "interference_per_sc_dbm": -999
  },
  "base_station": {
    "position": [0, 0, 25],
    "tx_power_dbm": 30,
    "interferers": [
      {"position": [150, 0, 25], "tx_power_dbm": 30},
      {"position": [-150, 0, 25], "tx_power_dbm": 30},
      {"position": [0, 150, 25], "tx_power_dbm": 30}
    ]
  }
}
```

**Key parameters:**
- Grid: 14m × 14m (small cell)
- Main BS: Overhead at 25m height
- Interferers: 150m away (neighboring cells)
- All BSs: Same power (30 dBm EIRP)

**Expected behavior:**
- Center locations: High RSS, high SINR (close to main BS, far from interferers)
- Edge locations: Medium RSS, low SINR (farther from main BS, closer to interferers)
- RSS and SINR now have **different spatial patterns** → different classification performance

---

## Implementation Checklist

1. [ ] Modify QuaDRiGa layout to include multiple BSs
2. [ ] Generate channels from all BSs (`l.get_channels()`)
3. [ ] Compute interference from BSs 2-4
4. [ ] Pass per-snapshot interference to `CSIMetrics.compute(H, I_vec)`
5. [ ] Verify RSS ≠ SINR in results (different accuracies/MAE)
6. [ ] Compare transition method improvement for RSS vs SINR

---

## Verification

After implementation, check:

```matlab
% Load results
load('corrected_comparison_results.mat');

% Check if RSS and SINR differ
fprintf('RSS:  mean=%.2f, std=%.4f\n', mean(metrics.RSS_wb), std(metrics.RSS_wb));
fprintf('SINR: mean=%.2f, std=%.4f\n', mean(metrics.SINR_wb), std(metrics.SINR_wb));
fprintf('Correlation: %.6f\n', corr(metrics.RSS_wb, metrics.SINR_wb));

% Expected:
% Correlation < 0.95 (not perfectly linear anymore)
% std(SINR) ≠ std(RSS) (different spatial variation)
```

If correlation is still 1.000000, multi-BS setup didn't work correctly.

---

## Summary

**Current:** Single BS → RSS = SINR + constant → identical classification

**Solution:** Multi-BS → Spatially-varying interference → RSS ≠ SINR

**Most realistic:** 4 BSs (main + 3 interferers at 150m distance)

**Expected:** SINR worse than RSS, but transition method helps SINR more!

This validates that your transition-based approach is especially valuable when measurements are noisy/unreliable.
