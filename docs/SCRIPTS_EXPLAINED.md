# CSI_location Scripts - Complete Guide

## Overview
This folder contains MATLAB scripts for simulating wireless channel propagation using **QuaDRiGa** (Quasi Deterministic Radio Channel Generator) and computing Channel State Information (CSI) and Channel Quality Indicators (CQI) for 5G systems.

## 📚 Documentation Files

- **[SCRIPTS_EXPLAINED.md](SCRIPTS_EXPLAINED.md)** (this file) - Complete explanation of all scripts and how to use them
- **[ML_LOCATION_PREDICTION_GUIDE.md](ML_LOCATION_PREDICTION_GUIDE.md)** - Comprehensive guide for your ML project: data generation, feature engineering, model training, and evaluation
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick reference card for common tasks, troubleshooting, and workflows

---

## Scripts Summary

### 1. **simple_full_csi_matrix.m** - Basic Introduction
**Purpose**: Minimal example showing how to set up QuaDRiGa with 1 BS and 1 static UE.

**What it does**:
- Creates a single base station at origin (0,0,25m height)
- Creates a single static UE at position (50,0,1.5m)
- Uses 3GPP Urban Macro LOS scenario
- Generates channel impulse response (time-domain taps)
- Displays CSI matrix dimensions

**Use this script to**:
- Understand basic QuaDRiGa setup
- Learn the minimal code structure
- See what raw CSI looks like

---

### 2. **csi_matrix_of_one_user.m** - CSI Analysis and Metrics
**Purpose**: Comprehensive single-UE simulation with frequency-domain CSI analysis and quality metrics.

**What it does**:
1. **Channel Generation**: Creates BS-UE link with richer multipath (UE at 200,60,1.5m)
2. **Time-Domain**: Computes channel impulse response (taps and delays)
3. **Frequency-Domain**: Converts taps to CSI across 1024 subcarriers (100 MHz BW)
   - Uses FFT-like transform: `H(f) = Σ h_l * exp(-j*2πf*τ_l)`
4. **Metrics Calculation**: Uses `CSIMetrics` class to compute:
   - RSS (Received Signal Strength) - wideband and per-subcarrier
   - SINR (Signal-to-Interference-plus-Noise Ratio)
   - CQI (Channel Quality Indicator) - 0 to 15 scale
5. **Visualization**: Creates 3 plots:
   - Impulse response (time-domain taps)
   - |H(f)| linear magnitude
   - |H(f)| in dB
6. **Re-plot helpers**: Stores plot functions in workspace for easy redrawing

**Key Concepts**:
- **RMS delay spread**: Measure of channel frequency selectivity
- **Coherence bandwidth**: ~1/(5*delay_spread), frequency range where channel is flat
- **Subcarrier spacing**: 100MHz/1024 ≈ 97.7 kHz

**Use this script to**:
- Analyze frequency-selective fading
- Understand CSI structure
- Learn how to compute wireless metrics
- Get familiar with `CSIMetrics` class

---

### 3. **simulate_ue_movement_v2_tracks.m** - UE Trajectory Simulation
**Purpose**: Simulate a moving UE along a predefined path and track CSI/CQI changes over time.

**What it does**:
1. **Movement Setup**: Creates 60-snapshot trajectory from (50,-30,1.5) to (260,90,1.5)
2. **Time-Consistent Channels**: 
   - **Primary mode**: Uses `qd_track` API for physically realistic channel evolution
   - **Fallback mode**: Regenerates channel at each position (if track API unavailable)
3. **Per-Snapshot Processing**: For each time step:
   - Gets channel taps and delays
   - Converts to frequency-domain CSI (256 subcarriers, 100 MHz)
   - Computes RSS, SINR, CQI using local helper function
4. **Three Visualizations**:
   - **Plot 1**: CQI over time (stairs plot showing quality changes)
   - **Plot 2**: Surface view (BS + colored UE samples by time)
   - **Plot 3**: UE trajectory with direction arrows
5. **Output Table**: Creates `traj_tbl_tracks` with columns: time, x, y, z, RSS_dBm, SINR_dB, CQI

**Key Features**:
- Time-consistent channel modeling (important for realistic simulations)
- Demonstrates how channel quality degrades/improves with movement
- Shows spatial-temporal correlation of wireless channels

**Use this script to**:
- Simulate mobility scenarios
- Analyze how position affects channel quality
- Generate training data for ML models (location prediction)

---

### 4. **CSIMetrics.m** - Metrics Computation Class
**Purpose**: Reusable class for converting frequency-domain CSI to practical wireless metrics.

**Input**: 
- CSI matrix `H` with shape `[Nrx, Ntx, Nsc]` or `[Nrx, Ntx, Nsc, Ns]`
  - Nrx: number of receive antennas
  - Ntx: number of transmit antennas
  - Nsc: number of subcarriers
  - Ns: number of snapshots (optional)

**Configurable Parameters**:
- `SubcarrierSpacing`: Hz (default 30 kHz for 5G NR)
- `TxPowerPerSC_dBm`: Transmit power per subcarrier (default 0 dBm = 1 mW)
- `NoiseFigure_dB`: UE noise figure (default 7 dB)
- `InterfPerSC_dBm`: Interference level (default -Inf = no interference)
- `MIMOCombine`: How to reduce MIMO matrix to scalar ('sumPow', 'svd', 'maxEig')
- `RBSizeSC`: Subcarriers per Resource Block (default 12 for NR)
- `CQIThresholds_dB`: SINR thresholds for CQI values 0-15

**Output Structure**:
```matlab
out.RSS_dBm_sc    % Per-subcarrier RSS [Nsc x Ns]
out.RSS_dBm_wb    % Wideband RSS [1 x Ns]
out.SINR_dB_sc    % Per-subcarrier SINR [Nsc x Ns]
out.SINR_dB_wb    % Wideband SINR (averaged) [1 x Ns]
out.CQI_sc        % Per-subcarrier CQI (0-15) [Nsc x Ns]
out.CQI_RB        % Per-RB CQI (median) [NRB x Ns]
out.CQI_wb        % Wideband CQI [1 x Ns]
out.meta          % Copy of configuration
```

**How it works**:
1. **Gain Calculation**: Reduces MIMO H matrix to scalar gain per subcarrier
2. **RSS**: `RSS = TxPower * Gain` (in Watts, then converted to dBm)
3. **Noise**: `N = k*T*BW*NF` (thermal noise + noise figure)
4. **SINR**: `SINR = Signal / (Noise + Interference)`
5. **CQI Mapping**: Maps SINR to CQI 0-15 using threshold table

**Use this class when**:
- You have frequency-domain CSI and need metrics
- You want standardized, reusable metric computation
- You need both per-subcarrier and wideband values

---

## How Scripts Are Connected

```
simple_full_csi_matrix.m (Beginner)
         ↓
         └─→ Learn QuaDRiGa basics
         
csi_matrix_of_one_user.m (Intermediate)
         ↓
         ├─→ Frequency-domain CSI conversion
         ├─→ Uses CSIMetrics class
         └─→ Advanced visualization
         
simulate_ue_movement_v2_tracks.m (Advanced)
         ↓
         ├─→ Time-varying channels
         ├─→ Uses CSIMetrics principles (local function)
         └─→ ML-ready output table

CSIMetrics.m (Utility Class)
         ↑
         └─→ Used by csi_matrix_of_one_user.m
         └─→ Can be used by any script needing metrics
```

---

## How to Create Your Own Simulation

### Goal: Single UE moving in a simple environment, observe CSI and CQI

Based on your requirements, I recommend **modifying `simulate_ue_movement_v2_tracks.m`**. Here's your step-by-step guide:

### Step 1: Define Your Environment
```matlab
%% Parameters
fc = 3.5e9;        % 3.5 GHz (or use 2.4e9, 28e9, etc.)
BW = 100e6;        % 100 MHz bandwidth
Nsc = 256;         % Number of subcarriers
T = 50;            % Number of time snapshots

%% Base Station Position
bs_x = 0;          % meters
bs_y = 0;
bs_z = 25;         % 25m height (typical macro cell)

%% Define UE Movement (straight line example)
% Start position
start_pos = [20; 10; 1.5];  % x, y, z in meters

% End position
end_pos = [80; 50; 1.5];

% Create linear trajectory
X = linspace(start_pos(1), end_pos(1), T);
Y = linspace(start_pos(2), end_pos(2), T);
Z = linspace(start_pos(3), end_pos(3), T);
P = [X; Y; Z];  % 3 x T matrix
```

### Step 2: QuaDRiGa Setup
```matlab
%% QuaDRiGa initialization
s = qd_simulation_parameters;
s.center_frequency = fc;
s.sample_density = 2;
s.use_absolute_delays = 1;

%% Layout
l = qd_layout(s);
l.tx_position = [bs_x; bs_y; bs_z];
l.tx_array = qd_arrayant('omni');
l.rx_array = qd_arrayant('omni');

%% Choose scenario
% Options: '3GPP_38.901_UMa_LOS'     - Urban Macro, Line of Sight
%          '3GPP_38.901_UMa_NLOS'    - Urban Macro, Non-LOS (more multipath)
%          '3GPP_38.901_UMi_LOS'     - Urban Micro, LOS
%          '3GPP_38.901_InH_LOS'     - Indoor Hotspot, LOS
l.set_scenario('3GPP_38.901_UMa_LOS');
```

### Step 3: Create Track and Generate Channels
```matlab
%% Create track
trk = qd_track;
trk.name = 'MyUE';
trk.initial_position = P(:,1);
trk.positions = P;  % Set entire trajectory
l.rx_track = {trk};

%% Generate time-consistent channels
c = l.get_channels;
Htaps = c.coeff;   % [Nrx x Ntx x Ntaps x T]
taus = c.delay;    % [1 x Ntaps x T]
```

### Step 4: Compute CSI and Metrics
```matlab
%% Storage
CQI_wb = zeros(T, 1);
SINR_wb = zeros(T, 1);
RSS_wb = zeros(T, 1);
CSI_complex = cell(T, 1);  % Store full CSI for each snapshot

%% Frequency axis
fvec = linspace(-BW/2, BW/2, Nsc);

%% Process each snapshot
for t = 1:T
    % Get taps and delays at time t
    h = squeeze(Htaps(1,1,:,t));
    tau = squeeze(taus(1,:,t));
    
    % Convert to frequency-domain CSI
    Hsc = zeros(1, 1, Nsc);
    for k = 1:Nsc
        Hsc(1,1,k) = sum(h .* exp(-1j*2*pi*fvec(k).*tau));
    end
    
    % Store CSI
    CSI_complex{t} = squeeze(Hsc);  % [Nsc x 1] complex values
    
    % Compute metrics using CSIMetrics class
    m = CSIMetrics('SubcarrierSpacing', BW/Nsc, ...
                   'TxPowerPerSC_dBm', 0, ...
                   'NoiseFigure_dB', 7);
    out = m.compute(Hsc);
    
    RSS_wb(t) = out.RSS_dBm_wb;
    SINR_wb(t) = out.SINR_dB_wb;
    CQI_wb(t) = out.CQI_wb;
end
```

### Step 5: Visualize Results
```matlab
%% Plot 1: CQI over time
figure('Name', 'CQI Evolution');
stairs(1:T, CQI_wb, 'LineWidth', 2);
xlabel('Time Step'); ylabel('CQI (0-15)');
title('Channel Quality Indicator Over Time');
grid on;

%% Plot 2: Top-down view with trajectory
figure('Name', 'UE Movement');
plot(X, Y, 'b-', 'LineWidth', 2); hold on;
plot(X(1), Y(1), 'go', 'MarkerSize', 10, 'MarkerFaceColor', 'g'); % Start
plot(X(end), Y(end), 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r'); % End
plot(bs_x, bs_y, '^', 'MarkerSize', 15, 'MarkerFaceColor', 'r'); % BS
quiver(X(1:end-1), Y(1:end-1), diff(X), diff(Y), 0, 'k');
xlabel('X [m]'); ylabel('Y [m]');
legend('Path', 'Start', 'End', 'BS', 'Direction');
title('UE Trajectory');
grid on; axis equal;

%% Plot 3: CSI magnitude heatmap
CSI_mag = zeros(Nsc, T);
for t = 1:T
    CSI_mag(:, t) = abs(CSI_complex{t});
end
figure('Name', 'CSI Magnitude');
imagesc(1:T, 1:Nsc, CSI_mag);
xlabel('Time Step'); ylabel('Subcarrier Index');
title('CSI Magnitude Over Time and Frequency');
colorbar; colormap('jet');

%% Plot 4: SINR and RSS
figure('Name', 'RSS and SINR');
subplot(2,1,1);
plot(1:T, RSS_wb, 'LineWidth', 2);
xlabel('Time Step'); ylabel('RSS [dBm]');
title('Received Signal Strength');
grid on;

subplot(2,1,2);
plot(1:T, SINR_wb, 'LineWidth', 2);
xlabel('Time Step'); ylabel('SINR [dB]');
title('Signal-to-Noise Ratio');
grid on;
```

### Step 6: Export Data for Analysis
```matlab
%% Create table for ML/analysis
results_table = table((1:T)', X', Y', Z', RSS_wb, SINR_wb, CQI_wb, ...
    'VariableNames', {'TimeStep', 'X_m', 'Y_m', 'Z_m', 'RSS_dBm', 'SINR_dB', 'CQI'});

% Save to CSV
writetable(results_table, 'ue_movement_results.csv');

% Save CSI to MAT file
save('ue_movement_csi.mat', 'CSI_complex', 'P', 'results_table', 'Nsc', 'BW', 'fc');

disp('Results saved!');
disp(results_table(1:10, :));  % Show first 10 rows
```

---

## Different Movement Patterns

### Circular Path
```matlab
T = 100;
radius = 50;
theta = linspace(0, 2*pi, T);
X = radius * cos(theta);
Y = radius * sin(theta);
Z = 1.5 * ones(1, T);
P = [X; Y; Z];
```

### Random Walk
```matlab
T = 50;
step_size = 5;
X = cumsum([20, randn(1, T-1) * step_size]);
Y = cumsum([10, randn(1, T-1) * step_size]);
Z = 1.5 * ones(1, T);
P = [X; Y; Z];
```

### Approaching BS
```matlab
T = 60;
start_distance = 100;
end_distance = 10;
distances = linspace(start_distance, end_distance, T);
X = distances;
Y = zeros(1, T);
Z = 1.5 * ones(1, T);
P = [X; Y; Z];
```

---

## Key Concepts for Your Experiment

### CSI (Channel State Information)
- **Complex-valued**: Each subcarrier has magnitude and phase
- **Magnitude**: `|H(f)|` shows attenuation at each frequency
- **Phase**: `∠H(f)` shows phase shift
- **Frequency-selective**: Different subcarriers experience different fading

### CQI (Channel Quality Indicator)
- **Range**: 0 to 15 (integer)
- **0**: Very poor channel (SINR < -6.7 dB)
- **15**: Excellent channel (SINR ≥ 22.7 dB)
- **Purpose**: Used by scheduler to select Modulation and Coding Scheme (MCS)

### Observations to Expect
1. **Distance effect**: CQI decreases as UE moves away from BS
2. **Multipath fading**: CSI shows frequency-selective nulls/peaks
3. **Small-scale fading**: Quick variations due to multipath interference
4. **Large-scale fading**: Slow variations due to distance and shadowing

---

## Troubleshooting

### "Undefined function 'qd_track'"
- Your QuaDRiGa version might not support track API
- Use the fallback loop method (regenerate channel each step)

### Very flat CSI (no frequency selectivity)
- Use NLOS scenario instead of LOS: `'3GPP_38.901_UMa_NLOS'`
- Increase BW or move UE further from BS

### All CQI values are 15 or 0
- Adjust `TxPowerPerSC_dBm` parameter
- Check `NoiseFigure_dB` (default 7 dB)
- Verify scenario is appropriate for your setup

---

## Next Steps

1. **Start with**: `simple_full_csi_matrix.m` to verify QuaDRiGa works
2. **Then run**: `csi_matrix_of_one_user.m` to understand CSI structure
3. **Finally modify**: `simulate_ue_movement_v2_tracks.m` for your experiment
4. **Use**: `CSIMetrics.m` whenever you need standardized metrics

Good luck with your simulation! 🎯

---

## Moving Forward: Machine Learning Project

Once you've generated simulation data and understand CSI/CQI behavior, you can move to the next phase: **predicting UE location from CSI/CQI measurements using machine learning**.

📚 **See the complete guide**: [`ML_LOCATION_PREDICTION_GUIDE.md`](ML_LOCATION_PREDICTION_GUIDE.md)

This comprehensive guide covers:
- **Data generation strategy** for training ML models
- **Feature engineering** from CSI/CQI measurements
- **ML pipeline** (from data prep to model training)
- **Evaluation metrics** and performance analysis
- **Advanced techniques** (LSTM, multi-BS, real-time tracking)
- **Step-by-step roadmap** for your master's project

The guide provides complete code examples for:
- Generating diverse training trajectories
- Extracting 25+ features from wireless measurements
- Training Random Forest, Neural Networks, and LSTMs
- Evaluating localization accuracy
- Analyzing feature importance

**Your Project Goal**: Train a model that can predict UE position (x, y coordinates) from observed CSI and CQI values over time, achieving < 10 meter mean localization error.
