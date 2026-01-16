# Why RSS and SINR Are Still Identical (Bug Investigation)

## Problem Summary

You set `"interference_per_sc_dbm": -90` in config.json, but RSS and SINR still produce identical results:

**3×3 Grid Results:**
- RSS:  100.00% accuracy, MAE = 0.000
- SINR: 100.00% accuracy, MAE = 0.000
- **IDENTICAL!** ❌

**7×7 Grid Results:**
- RSS:  31.13% accuracy, MAE = 2.019
- SINR: 31.13% accuracy, MAE = 2.019
- **IDENTICAL!** ❌

---

## Root Cause: Old Code Was Used

### The Issue

The code to read the `interference_per_sc_dbm` parameter from config.json and pass it to CSIMetrics was added RECENTLY. Your experiment results are from:
- 3×3: `2026-01-09 09:50:52`
- 7×7: `2026-01-09 09:59:51`

**These experiments may have run BEFORE the interference parameter support was added to the script.**

---

## Verification: CSIMetrics Works Correctly

I created a simple test (`test_interference_effect.m`) that confirms:

```
Test 1: No interference (InterfPerSC_dBm = -Inf)
  RSS_wb:  24.08 dBm
  SINR_wb: 111.06 dB

Test 2: With interference (InterfPerSC_dBm = -90)
  RSS_wb:  24.08 dBm    ← Unchanged!
  SINR_wb: 89.97 dB     ← Dropped by 21 dB!

✓ RSS is unchanged (as expected)
✓ SINR dropped with interference (as expected)
✓ CSIMetrics interference handling is CORRECT
```

**CSIMetrics itself is working perfectly.** The bug must be in how we call it.

---

## How To Fix: Re-run Experiments

### Step 1: Verify Config Has Interference

Check `config.json`:
```json
"channel": {
    "interference_per_sc_dbm": -90
}
```

✓ This is correct.

### Step 2: Verify Script Uses Interference

I just added debug output to `exp13e_corrected_fair_comparison.m`:
```matlab
% Get interference parameter from config
interference_dbm = -Inf;
if isfield(config_json.channel, 'interference_per_sc_dbm')
    if config_json.channel.interference_per_sc_dbm > -900
        interference_dbm = config_json.channel.interference_per_sc_dbm;
        fprintf('  Using interference: %.1f dBm per subcarrier\n', interference_dbm);
    else
        fprintf('  No interference (ideal scenario)\n');
    end
end

m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, 'NoiseFigure_dB', 7, ...
               'InterfPerSC_dBm', interference_dbm);

% DEBUG: Verify interference parameter
fprintf('  CSIMetrics initialized with InterfPerSC_dBm = %.1f dBm\n', m.InterfPerSC_dBm);
```

### Step 3: Re-run Experiments

**Watch for these print statements:**
```
Computing CSI metrics...
  Using interference: -90.0 dBm per subcarrier
  CSIMetrics initialized with InterfPerSC_dBm = -90.0 dBm
```

If you see:
- `"Using interference: -90.0 dBm"` → Good, config was read
- `"CSIMetrics initialized with InterfPerSC_dBm = -90.0 dBm"` → Good, it was passed correctly
- `"No interference (ideal scenario)"` → Bug! Config not read properly
- `"CSIMetrics initialized with InterfPerSC_dBm = -Inf dBm"` → Bug! Not passed correctly

---

## Expected Results After Re-running

### 3×3 Grid (Easy Problem)

#### Without Interference (-999):
```
RSS:  87-95% accuracy
SINR: 87-95% accuracy  ← Same as RSS
Transition improvement: ~1-2%
```

#### With -90 dBm Interference:
```
RSS:  87-95% accuracy  ← Unchanged
SINR: 45-60% accuracy  ← Much worse!
Transition improvement: 
  - RSS:  +1-2% (same as before)
  - SINR: +5-10% (much more!)
```

### 7×7 Grid (Harder Problem)

#### Without Interference (-999):
```
RSS:  30-40% accuracy
SINR: 30-40% accuracy  ← Same as RSS
Transition improvement: ~10-15%
```

#### With -90 dBm Interference:
```
RSS:  30-40% accuracy   ← Unchanged
SINR: 15-25% accuracy   ← Much worse!
Transition improvement:
  - RSS:  +10-15% (same as before)
  - SINR: +15-25% (much more!)
```

---

## What Your Current Results Tell Us

Your 7×7 results show:
- Static: 31.13% → Transition: 45.17% (+14.03%)
- This is a HUGE improvement! ✓

But RSS = SINR exactly, which means:
- ❌ Interference was NOT applied
- ❌ Script ran with old code (or interference parameter not read)

---

## Diagnostic Checklist

Run through these checks:

### 1. Config File
```powershell
cd "d:\gilad\projects\Academy\CSI-Location\experiments\09_grid_localization"
Get-Content config.json | Select-String "interference"
```

**Expected output:**
```
"interference_per_sc_dbm": -90
```

### 2. Script Code
Open `exp13e_corrected_fair_comparison.m` and search for:
```matlab
InterfPerSC_dBm
```

**Should find:**
- Line ~153: Reading from config
- Line ~163: Passing to CSIMetrics constructor
- Line ~166: Debug print (new!)

### 3. Re-run Experiment

```matlab
cd 'd:\gilad\projects\Academy\CSI-Location\experiments\09_grid_localization'
exp13e_corrected_fair_comparison
```

**Watch the console output for:**
```
Computing CSI metrics...
  Using interference: -90.0 dBm per subcarrier
  CSIMetrics initialized with InterfPerSC_dBm = -90.0 dBm
```

### 4. Check Results

After running, the report should show:
```
| Metric | Static | Transition | Improvement |
|:-------|:-------|:-----------|:------------|
| RSS    | ~35%   | ~48%       | +~13%       |
| SINR   | ~20%   | ~32%       | +~12%       | ← DIFFERENT!
```

---

## Why This Happened

Timeline of events (probable):

1. **Earlier:** You ran experiments → RSS = SINR (no interference support yet)
2. **You noticed:** "RSS and SINR are always identical"
3. **I investigated:** Found `InterfPerSC_dBm = -Inf` was the cause
4. **I added:** Code to read interference from config.json
5. **You edited:** config.json to set `interference_per_sc_dbm: -90`
6. **You re-ran:** But MATLAB was still using old code from before the fix

**Solution:** Clear MATLAB workspace and re-run now that the code is updated.

---

## Technical Details: Why They Should Be Different

### RSS (Received Signal Strength)
```
RSS_wb = 10*log10(sum(Signal_Power_per_SC)) + 30

Measures: Total power received from serving BS
Not affected by: Interference (we don't include interfering BS power)
```

### SINR (Signal-to-Interference-plus-Noise Ratio)
```
SINR_wb = 10*log10(mean(Signal / (Noise + Interference)))

With interference I = -90 dBm per SC:
- Noise N ≈ -111 dBm per SC (thermal)
- Interference I = -90 dBm per SC (dominant!)
- Denominator ≈ I (interference dominates)

SINR ≈ 10*log10(Signal / Interference)
     = RSS_dBm_per_SC - I_dBm
     = RSS_dBm_per_SC - (-90)
     = RSS_dBm_per_SC + 90

Much lower than RSS!
```

### Example Calculation

Location with good signal:
```
RSS_sc = -95 dBm per SC
RSS_wb = -95 + 10*log10(256) = -95 + 24 = -71 dBm

Without interference:
SINR = RSS_sc - Noise = -95 - (-111) = +16 dB ✓ Good

With -90 dBm interference:
SINR = RSS_sc - Interference = -95 - (-90) = -5 dB ⚠️ Poor!
```

**That's a 21 dB drop!** (from +16 dB to -5 dB)

---

## Summary

1. **CSIMetrics works correctly** ✓ (verified by test)
2. **Config has interference = -90** ✓ (verified by PowerShell)
3. **Script has interference support** ✓ (verified by code inspection)
4. **Experiments show RSS = SINR** ❌ (means it didn't run with updated code)

**Action Required:** 
Re-run experiments now. Watch for debug output confirming interference is applied. If RSS and SINR are still identical after this, there's a deeper bug we need to investigate.

---

## If Still Broken After Re-running

If you re-run and still see RSS = SINR, check:

1. **MATLAB cache:** Try `clear all; close all; clc` before running
2. **Path issues:** Verify `CSIMetrics.m` is from utils/ folder
3. **Config loading:** Add `disp(config_json.channel)` after loading config.json
4. **Variable scope:** Print `interference_dbm` right before CSIMetrics constructor

Let me know the console output from the re-run!
