# Utility Functions

This folder contains reusable utility classes and functions for QuaDRiGa experiments.

## Files

### `ExperimentUtils.m`
**Purpose:** Common operations for all experiments - follows DRY principle

**Key Methods:**

1. **`generateChannel(params)`** - One-line channel generation with robust delay handling
   ```matlab
   params = struct('center_frequency', 3.5e9, 'rx_position', [50;0;1.5]);
   [H_taps, delays_ns, c, l] = ExperimentUtils.generateChannel(params);
   ```

2. **`convertToFrequency(h_t, tau, fvec)`** - Time to frequency domain conversion
   ```matlab
   H_freq = ExperimentUtils.convertToFrequency(h_t, tau, fvec);
   ```

3. **`calculateChannelStats(H_taps, delays_ns)`** - Automatic statistics calculation
   ```matlab
   stats = ExperimentUtils.calculateChannelStats(H_taps, delays_ns);
   % Returns: path_loss_dB, rms_delay_spread_ns, dominant_tap_ratio, etc.
   ```

4. **`createFigure(title, layout)`** - Standard figure sizing
   ```matlab
   fig = ExperimentUtils.createFigure('My Experiment', 'square');
   % Layouts: 'square' (0.8x0.8), 'wide' (0.8x0.4), 'tall' (0.5x0.8)
   ```

5. **`saveFigures(fig_handles, filenames, results_dir)`** - Save PNG + FIG
   ```matlab
   ExperimentUtils.saveFigures({fig1, fig2}, {'plot1', 'plot2'}, results_dir);
   ```

6. **`createResultsDir(experiment_name)`** - Timestamped results folder
   ```matlab
   results_dir = ExperimentUtils.createResultsDir('exp01');
   % Creates: results/exp01_2025-11-03_14-30-45/
   ```

7. **Report Writing Functions:**
   ```matlab
   fid = ExperimentUtils.createReportHeader(results_dir, 'My Experiment');
   ExperimentUtils.writeSimParams(fid, params);
   % ... write custom sections ...
   ExperimentUtils.closeReport(fid, {'file1.png', 'file2.fig'});
   ```

### `CSIMetrics.m`
**Purpose:** Calculate wireless metrics (RSS, SINR, CQI) from CSI

**Usage:**
```matlab
m = CSIMetrics('SubcarrierSpacing', 390.625e3, 'TxPowerPerSC_dBm', 0);
out = m.compute(H_freq);  % Returns RSS_dBm, SINR_dB, CQI
```

### `example_usage.m`
**Purpose:** Demonstrates how to use ExperimentUtils

Run this to see the utilities in action and compare code length!

## Benefits of Using Utils

### Before (Original Code):
```matlab
% 30+ lines for channel generation
s = qd_simulation_parameters;
s.center_frequency = 3.5e9;
s.sample_density = 2;
s.use_absolute_delays = 1;
l = qd_layout(s);
l.tx_position = [0; 0; 25];
l.tx_array = qd_arrayant('omni');
l.rx_position = [75; 0; 1.5];
l.rx_array = qd_arrayant('omni');
l.set_scenario('3GPP_38.901_UMa_LOS');
c = l.get_channels;
H_taps = squeeze(c.coeff(1,1,:,1));
taus = c.delay;
% ... 15 more lines for robust delay extraction ...
```

### After (With Utils):
```matlab
% 2 lines for channel generation!
params = struct('rx_position', [75;0;1.5], 'scenario', '3GPP_38.901_UMa_LOS');
[H_taps, delays_ns] = ExperimentUtils.generateChannel(params);
```

**Code Reduction: ~47%** 🎉

## Design Principles

1. **DRY (Don't Repeat Yourself):** Common operations extracted to utilities
2. **Robust Error Handling:** Automatic handling of QuaDRiGa dimension variations
3. **Consistent Interface:** All experiments use same patterns
4. **Easy Maintenance:** Fix bugs in one place, benefits all experiments
5. **Better Readability:** Experiments focus on logic, not boilerplate

## Migration Guide

To refactor existing experiments:

1. Replace channel generation with `ExperimentUtils.generateChannel()`
2. Replace frequency conversion with `ExperimentUtils.convertToFrequency()`
3. Replace figure creation with `ExperimentUtils.createFigure()`
4. Replace saving logic with `ExperimentUtils.saveFigures()`
5. Use report helper functions for consistent formatting

See `example_usage.m` for a complete refactored experiment!

## Next Steps

You can refactor existing experiments (exp01-exp05) to use these utilities, or:
- Keep existing experiments as-is (they work fine)
- Use utilities for all NEW experiments going forward
- Gradually refactor old experiments as you revisit them

The choice is yours! The utilities are ready to use. 🚀
