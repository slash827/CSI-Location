# Quick Reference Card - CSI Location Project

## 🚀 Quick Start Commands

### First Time Setup
```matlab
% Verify QuaDRiGa is installed
which qd_layout
% Should return path to QuaDRiGa installation

% Run simple test
simple_full_csi_matrix
```

### Generate Your First Dataset
```matlab
% Edit my_ue_movement_experiment.m to set your parameters, then:
my_ue_movement_experiment

% Output files:
% - my_experiment_results.csv (table with metrics)
% - my_experiment_data.mat (full CSI data)
```

---

## 📊 Common Tasks

### View CSI Values
```matlab
% After running simulation with variable H_sc:
abs(squeeze(H_sc))           % Magnitude
angle(squeeze(H_sc))         % Phase (radians)
20*log10(abs(squeeze(H_sc))) % Magnitude in dB
```

### Change Scenario
```matlab
% In your script, replace l.set_scenario() line:
l.set_scenario('3GPP_38.901_UMa_LOS');    % Urban Macro, Line of Sight
l.set_scenario('3GPP_38.901_UMa_NLOS');   % Urban Macro, Non-LOS (more multipath)
l.set_scenario('3GPP_38.901_UMi_LOS');    % Urban Micro
l.set_scenario('3GPP_38.901_InH_LOS');    % Indoor Hotspot
```

### Change Movement Pattern
```matlab
% Linear (current default)
X = linspace(start_x, end_x, T);
Y = linspace(start_y, end_y, T);

% Circular
theta = linspace(0, 2*pi, T);
radius = 50;
X = center_x + radius * cos(theta);
Y = center_y + radius * sin(theta);

% Random walk
X = cumsum([start_x, randn(1, T-1)*step_size]);
Y = cumsum([start_y, randn(1, T-1)*step_size]);

% Then: P = [X; Y; 1.5*ones(1,T)];
```

### Adjust Radio Parameters
```matlab
% Frequency
fc = 2.4e9;   % 2.4 GHz (WiFi)
fc = 3.5e9;   % 3.5 GHz (5G mid-band)
fc = 28e9;    % 28 GHz (5G mmWave)

% Bandwidth
BW = 20e6;    % 20 MHz (LTE)
BW = 100e6;   % 100 MHz (5G)

% Subcarriers
Nsc = 256;    % Fewer subcarriers
Nsc = 1024;   % More subcarriers (finer frequency resolution)

% Transmit power
TxPowerPerSC_dBm = 10;   % Higher power (10 dBm)
TxPowerPerSC_dBm = -10;  % Lower power (-10 dBm)
```

### Multiple Base Stations
```matlab
% After l = qd_layout(s);
l.no_tx = 3;  % 3 base stations
l.tx_position = [[0;0;25], [100;50;25], [-50;80;25]];

% Then generate channels for each link separately:
for bs_idx = 1:3
    % ... process each BS-UE link
end
```

---

## 🔧 Troubleshooting

### "Undefined function 'qd_layout'"
**Solution**: QuaDRiGa not in MATLAB path
```matlab
addpath(genpath('C:\path\to\quadriga'));  % Adjust path
```

### CSI is all the same / no fading
**Solution**: Need richer multipath environment
```matlab
% Change to NLOS scenario
l.set_scenario('3GPP_38.901_UMa_NLOS');

% Or move UE further from BS
l.rx_position = [500; 300; 1.5];  % Further away
```

### CQI always 0 or always 15
**Solution**: Adjust power levels
```matlab
% If CQI = 0 (too low signal):
TxPowerPerSC_dBm = 10;   % Increase power

% If CQI = 15 (too high signal):
TxPowerPerSC_dBm = -10;  % Decrease power
% Or increase noise:
NoiseFigure_dB = 15;     % Higher noise
```

### "Track API failed"
**Solution**: Your QuaDRiGa version doesn't support tracks
```matlab
% The script automatically falls back to regenerating channels
% This is slower but works on all versions
% No action needed - just note slower execution
```

### Script runs very slowly
**Solution**: Reduce complexity
```matlab
T = 30;       % Fewer snapshots (was 50-60)
Nsc = 128;    % Fewer subcarriers (was 256-1024)
% Or wait - it's doing heavy computation :)
```

---

## 📈 Data Analysis Tips

### Load and Explore Saved Data
```matlab
% Load your results
load('my_experiment_data.mat');

% View table
disp(results_table);

% Plot specific metrics
figure; plot(results_table.CQI);
figure; plot(results_table.SINR_dB);
figure; plot(results_table.RSS_dBm);

% Access CSI
first_snapshot_csi = CSI_complex{1};  % Cell array
csi_magnitude_all = CSI_magnitude;    % Matrix [Nsc x T]
```

### Export for Python/ML
```matlab
% Convert to CSV
writetable(results_table, 'data_for_python.csv');

% Or use scipy.io in Python:
% from scipy.io import loadmat
% data = loadmat('my_experiment_data.mat')
```

### Quick Statistics
```matlab
% From results_table:
fprintf('CQI range: %d to %d\n', min(results_table.CQI), max(results_table.CQI));
fprintf('Mean SINR: %.2f dB\n', mean(results_table.SINR_dB));
fprintf('Distance traveled: %.2f m\n', ...
    sum(sqrt(diff(results_table.X_m).^2 + diff(results_table.Y_m).^2)));
```

---

## 🎯 Typical Workflow

### For Single Experiment:
1. Edit `my_ue_movement_experiment.m` parameters (lines 10-20)
2. Run: `my_ue_movement_experiment`
3. Examine plots (5 figures created)
4. Check CSV file for numerical results
5. Adjust parameters and repeat

### For ML Dataset Generation:
1. Create script based on "Data Generation Strategy" in ML guide
2. Loop through multiple trajectories/scenarios
3. Save each trajectory separately
4. Combine into single dataset
5. Extract features
6. Train model

### For Analysis:
1. Generate data (simulations)
2. Visualize (plots, heatmaps)
3. Extract features (CSI statistics, temporal features)
4. Train ML model
5. Evaluate (error metrics, CDF plots)
6. Iterate (improve features, model, data)

---

## 📝 File Organization Recommendation

```
CSI_location/
├── my_ue_movement_experiment.m          ← Your main experiment script
├── generate_training_data.m             ← Batch data generation
├── extract_features.m                   ← Feature engineering
├── data/
│   ├── raw/                             ← Raw simulation outputs
│   │   ├── trajectory_0001.mat
│   │   ├── trajectory_0002.mat
│   │   └── ...
│   ├── processed/
│   │   ├── ml_dataset.mat               ← Ready for ML
│   │   └── features_labels.csv
│   └── results/
│       ├── model_predictions.csv
│       └── evaluation_plots.png
├── models/
│   ├── random_forest_model.mat
│   └── neural_network_model.mat
└── docs/
    ├── SCRIPTS_EXPLAINED.md              ← Overview of all scripts
    ├── ML_LOCATION_PREDICTION_GUIDE.md   ← ML project guide
    └── QUICK_REFERENCE.md                ← This file
```

---

## 🔍 Key Variables Reference

### QuaDRiGa Objects
- `s` = qd_simulation_parameters (global settings)
- `l` = qd_layout (BS/UE positions, antennas)
- `c` = qd_channel (channel realization)
- `trk` = qd_track (UE trajectory)

### Channel Data
- `H_taps` or `Htaps` = [Nrx × Ntx × Ntaps × Nsnapshots] - Time-domain taps
- `taus` or `tau` = [1 × Ntaps × Nsnapshots] - Delays in seconds
- `H_sc` or `Hsc` = [Nrx × Ntx × Nsc × Nsnapshots] - Frequency-domain CSI

### Metrics
- `RSS_wb` = Received Signal Strength (wideband), in dBm
- `SINR_wb` = Signal-to-Interference-plus-Noise Ratio (wideband), in dB
- `CQI_wb` = Channel Quality Indicator (wideband), 0-15 integer

### Dimensions
- `Nrx` = Number of receive antennas (typically 1 for SISO)
- `Ntx` = Number of transmit antennas (typically 1 for SISO)
- `Ntaps` = Number of multipath components (varies, ~5-20)
- `Nsc` = Number of subcarriers (your choice, 128-1024 typical)
- `T` or `Ns` = Number of time snapshots (your choice, 30-100 typical)

---

## 🎓 Learning Path

**Complete Beginner** → Run these in order:
1. `simple_full_csi_matrix.m` - Understand basics
2. `csi_matrix_of_one_user.m` - Learn CSI structure
3. `my_ue_movement_experiment.m` - Your first moving UE
4. Modify trajectory in `my_ue_movement_experiment.m`
5. Try different scenarios (LOS/NLOS)

**Ready for ML** → Next steps:
1. Generate 10 diverse trajectories
2. Manually inspect the patterns (plot CSI vs position)
3. Extract basic features (CQI mean, SINR mean, RSS mean)
4. Train simple Random Forest on 10 trajectories
5. Evaluate - what's your error?
6. Expand to 50+ trajectories
7. Add more features
8. Try Neural Network
9. Read ML_LOCATION_PREDICTION_GUIDE.md for advanced techniques

**Advanced** → Research directions:
1. Multi-BS triangulation
2. LSTM for temporal modeling
3. Real-time tracking (Kalman filter + ML)
4. Validate on real data (indoor_location dataset)
5. Novel contributions (see ML guide)

---

## 📞 Getting Help

**Error in QuaDRiGa**: Check QuaDRiGa documentation
```matlab
doc qd_layout
doc qd_channel
```

**MATLAB errors**: Use debugger
```matlab
dbstop if error  % Auto-break on error
dbclear all      % Clear breakpoints
```

**Conceptual questions**: Re-read SCRIPTS_EXPLAINED.md sections

**ML questions**: See ML_LOCATION_PREDICTION_GUIDE.md

**Feature ideas**: Look at existing ML papers on CSI-based localization

---

## ✅ Checklist for First Successful Run

- [ ] QuaDRiGa installed and in MATLAB path
- [ ] Can run `simple_full_csi_matrix.m` without errors
- [ ] Can run `my_ue_movement_experiment.m` without errors
- [ ] See 5 plots appear
- [ ] CSV file created with results
- [ ] MAT file created with CSI data
- [ ] Can load and view the data
- [ ] Understand what CQI, SINR, RSS mean
- [ ] Can modify trajectory and see different results

**If all checked → You're ready to generate training data!** 🎉

---

## 💡 Pro Tips

1. **Save everything**: You'll want to compare experiments later
2. **Use descriptive filenames**: `trajectory_LOS_linear_50steps_001.mat`
3. **Comment your code**: Future-you will be grateful
4. **Version control**: Use Git from the start
5. **Validate physics**: Does RSS decrease with distance? Good!
6. **Visualize often**: Plots reveal bugs and insights
7. **Start simple**: Single trajectory → Multiple → ML pipeline
8. **Compare baselines**: Random guess? Distance-only? Beat those first!

---

**Happy simulating! 📡🚀**
