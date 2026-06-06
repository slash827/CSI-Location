# Machine Learning-Based UE Location Prediction Project Guide

## Project Overview

**Goal**: Predict User Equipment (UE) location based on observed CSI (Channel State Information) and CQI (Channel Quality Indicator) values over time using machine learning models.

**Approach**: 
1. Generate synthetic training data using QuaDRiGa simulations
2. Extract meaningful features from CSI/CQI measurements
3. Train ML models to learn the relationship between wireless metrics and location
4. Evaluate and optimize the model performance

---

## Phase 1: Data Generation Strategy

### 1.1 Create Diverse Training Scenarios

You need to generate data that covers various realistic situations:

#### Scenario Types to Simulate:

**A. Grid-Based Coverage**
```matlab
% Create a grid of positions to cover your area of interest
x_range = -100:10:100;  % 21 points
y_range = -100:10:100;  % 21 points
z = 1.5;  % Fixed height

positions = [];
for x = x_range
    for y = y_range
        positions = [positions, [x; y; z]];
    end
end
% Total: 21 × 21 = 441 positions
```

**B. Random Trajectories**
```matlab
% Generate N random walks
N_trajectories = 50;
T_steps = 60;  % Steps per trajectory

for traj_id = 1:N_trajectories
    % Random start position
    start = [rand()*200-100; rand()*200-100; 1.5];
    
    % Random walk with momentum
    positions = zeros(3, T_steps);
    positions(:,1) = start;
    velocity = randn(2,1) * 5;  % Initial velocity
    
    for t = 2:T_steps
        velocity = 0.8*velocity + 0.2*randn(2,1)*5;  % Smooth walk
        positions(1:2, t) = positions(1:2, t-1) + velocity;
        positions(3, t) = 1.5;
    end
    
    % Run simulation for this trajectory
    % ... (use your experiment script)
end
```

**C. Realistic Movement Patterns**
```matlab
% Straight line movements (pedestrian)
% Circular paths (vehicle around roundabout)
% Stop-and-go patterns (urban pedestrian)
% Fast linear (highway vehicle)
```

### 1.2 Vary Environmental Conditions

**Scenarios to Include**:
- **LOS**: `'3GPP_38.901_UMa_LOS'` - Clear line of sight
- **NLOS**: `'3GPP_38.901_UMa_NLOS'` - Obstructed, rich multipath
- **Indoor**: `'3GPP_38.901_InH_LOS'` - Indoor hotspot
- **Urban Micro**: `'3GPP_38.901_UMi_LOS'` - Street level

**Multiple Base Stations**:
```matlab
% Add 3-4 BS to improve triangulation
l.tx_position = [[0;0;25], [100;50;25], [-50;80;25]];  % 3 BS
% Simulate CSI from each BS-UE link separately
```

### 1.3 Data Collection Script Template

```matlab
%% DATA GENERATION FOR ML - COMPREHENSIVE DATASET
clear; clc;

% Configuration
output_dir = 'training_data';
if ~exist(output_dir, 'dir'), mkdir(output_dir); end

scenarios = {'3GPP_38.901_UMa_LOS', '3GPP_38.901_UMa_NLOS'};
N_trajectories_per_scenario = 25;
T_steps = 50;

all_data = [];

for s_idx = 1:length(scenarios)
    scenario = scenarios{s_idx};
    fprintf('\n=== Scenario: %s ===\n', scenario);
    
    for traj = 1:N_trajectories_per_scenario
        fprintf('  Trajectory %d/%d\n', traj, N_trajectories_per_scenario);
        
        % Generate random trajectory
        [P, trajectory_type] = generate_random_trajectory(T_steps);
        
        % Run QuaDRiGa simulation
        [CSI_data, metrics] = run_quadriga_simulation(P, scenario);
        
        % Store with metadata
        traj_data = struct();
        traj_data.scenario = scenario;
        traj_data.trajectory_id = traj;
        traj_data.trajectory_type = trajectory_type;
        traj_data.positions = P;
        traj_data.CSI_magnitude = CSI_data.magnitude;
        traj_data.CSI_phase = CSI_data.phase;
        traj_data.RSS = metrics.RSS_wb;
        traj_data.SINR = metrics.SINR_wb;
        traj_data.CQI = metrics.CQI_wb;
        traj_data.timestamp = 1:T_steps;
        
        all_data = [all_data; traj_data];
    end
end

% Save complete dataset
save(fullfile(output_dir, 'complete_training_data.mat'), 'all_data');
fprintf('\n✓ Dataset saved: %d trajectories\n', length(all_data));
```

---

## Phase 2: Feature Engineering

### 2.1 Raw Features from CSI/CQI

**Temporal Features** (capture dynamics):
```matlab
% For each time window (e.g., 5 consecutive snapshots)

% CQI statistics
CQI_mean = mean(CQI_window);
CQI_std = std(CQI_window);
CQI_trend = polyfit(1:length(CQI_window), CQI_window, 1);  % Linear trend

% SINR statistics  
SINR_mean = mean(SINR_window);
SINR_std = std(SINR_window);
SINR_min = min(SINR_window);
SINR_max = max(SINR_window);

% RSS statistics
RSS_mean = mean(RSS_window);
RSS_std = std(RSS_window);
RSS_rate_of_change = diff(RSS_window);  % Velocity indicator
```

**Frequency-Domain Features** (from CSI magnitude):
```matlab
% Per snapshot CSI magnitude: [Nsc x 1]

% Spectral statistics
CSI_mean_mag = mean(CSI_magnitude);
CSI_std_mag = std(CSI_magnitude);
CSI_max_mag = max(CSI_magnitude);
CSI_min_mag = min(CSI_magnitude);

% Frequency selectivity (how "wavy" is the CSI)
CSI_variance = var(CSI_magnitude);
CSI_dynamic_range = max(CSI_magnitude) - min(CSI_magnitude);

% Number of fades (deep nulls)
threshold = 0.3 * max(CSI_magnitude);
num_fades = sum(CSI_magnitude < threshold);

% Coherence bandwidth estimate
autocorr = xcorr(CSI_magnitude, 'normalized');
coherence_bw_estimate = find(autocorr(Nsc:end) < 0.5, 1) * SCS_Hz;

% Spectral centroid
freq_axis = 1:Nsc;
spectral_centroid = sum(freq_axis .* CSI_magnitude') / sum(CSI_magnitude);

% Spectral spread
spectral_spread = sqrt(sum((freq_axis - spectral_centroid).^2 .* CSI_magnitude') / sum(CSI_magnitude));
```

**Multi-BS Features** (if using multiple base stations):
```matlab
% RSS difference between BS pairs (triangulation-like)
RSS_diff_BS1_BS2 = RSS_BS1 - RSS_BS2;
RSS_diff_BS1_BS3 = RSS_BS1 - RSS_BS3;
RSS_diff_BS2_BS3 = RSS_BS2 - RSS_BS3;

% Dominant BS (which BS has strongest signal)
dominant_BS_id = argmax([RSS_BS1, RSS_BS2, RSS_BS3]);
```

### 2.2 Derived Physical Features

**Path Loss Model Features**:
```matlab
% Estimate distance from RSS using Friis equation
% RSS = TxPower - PathLoss
% PathLoss ≈ 20*log10(d) + 20*log10(f) + ... (simplified)

fc_GHz = fc / 1e9;
estimated_distance = 10^((TxPower_dBm - RSS_dBm - 20*log10(fc_GHz) - 32.45) / 20);
```

**Doppler/Velocity Indicators**:
```matlab
% Rate of change in RSS (related to velocity)
RSS_velocity = diff(RSS_window) / dt;  % dBm/second

% Rate of change in CQI
CQI_velocity = diff(CQI_window) / dt;
```

### 2.3 Feature Engineering Script

```matlab
%% FEATURE EXTRACTION FOR ML

function features = extract_features(CSI_magnitude, RSS_wb, SINR_wb, CQI_wb, window_size)
    % Extract features from a time window of measurements
    % Inputs:
    %   CSI_magnitude: [Nsc x T] matrix
    %   RSS_wb, SINR_wb, CQI_wb: [T x 1] vectors
    %   window_size: number of snapshots to include
    
    T = length(RSS_wb);
    n_windows = T - window_size + 1;
    n_features = 25;  % Adjust based on features you extract
    
    features = zeros(n_windows, n_features);
    
    for w = 1:n_windows
        idx = w:(w+window_size-1);
        
        % CQI features
        features(w, 1) = mean(CQI_wb(idx));
        features(w, 2) = std(CQI_wb(idx));
        features(w, 3) = max(CQI_wb(idx));
        features(w, 4) = min(CQI_wb(idx));
        if window_size > 2
            p = polyfit(1:window_size, CQI_wb(idx)', 1);
            features(w, 5) = p(1);  % CQI trend
        end
        
        % SINR features
        features(w, 6) = mean(SINR_wb(idx));
        features(w, 7) = std(SINR_wb(idx));
        features(w, 8) = max(SINR_wb(idx));
        features(w, 9) = min(SINR_wb(idx));
        
        % RSS features
        features(w, 10) = mean(RSS_wb(idx));
        features(w, 11) = std(RSS_wb(idx));
        if window_size > 1
            features(w, 12) = mean(diff(RSS_wb(idx)));  % RSS rate of change
        end
        
        % CSI spectral features (average over time window)
        CSI_window = CSI_magnitude(:, idx);
        CSI_mean = mean(CSI_window, 2);  % [Nsc x 1]
        
        features(w, 13) = mean(CSI_mean);
        features(w, 14) = std(CSI_mean);
        features(w, 15) = max(CSI_mean);
        features(w, 16) = min(CSI_mean);
        features(w, 17) = var(CSI_mean);  % Frequency selectivity
        features(w, 18) = max(CSI_mean) - min(CSI_mean);  % Dynamic range
        
        % Coherence bandwidth estimate
        autocorr = xcorr(CSI_mean, 'normalized');
        Nsc = length(CSI_mean);
        coherence_idx = find(autocorr(Nsc:end) < 0.5, 1);
        features(w, 19) = coherence_idx / Nsc;  % Normalized
        
        % Spectral centroid and spread
        freq_axis = (1:Nsc)';
        spectral_centroid = sum(freq_axis .* CSI_mean) / sum(CSI_mean);
        features(w, 20) = spectral_centroid / Nsc;  % Normalized
        
        spectral_spread = sqrt(sum((freq_axis - spectral_centroid).^2 .* CSI_mean) / sum(CSI_mean));
        features(w, 21) = spectral_spread / Nsc;  % Normalized
        
        % Number of deep fades
        threshold = 0.3 * max(CSI_mean);
        features(w, 22) = sum(CSI_mean < threshold);
        
        % Estimated distance (simplified Friis)
        fc_GHz = 3.5;  % Adjust to your frequency
        TxPower_dBm = 0;  % Adjust to your Tx power
        features(w, 23) = 10^((TxPower_dBm - features(w,10) - 20*log10(fc_GHz) - 32.45) / 20);
        
        % Temporal change indicators
        if w > 1
            features(w, 24) = features(w, 1) - features(w-1, 1);  % CQI change
            features(w, 25) = features(w, 10) - features(w-1, 10);  % RSS change
        end
    end
    
    % Replace NaN/Inf with 0
    features(isnan(features) | isinf(features)) = 0;
end
```

---

## Phase 3: Machine Learning Pipeline

### 3.1 Dataset Preparation

```matlab
%% PREPARE ML DATASET

% Load all collected data
load('training_data/complete_training_data.mat', 'all_data');

% Extract features and labels
all_features = [];
all_labels = [];  % [x, y] positions

window_size = 5;  % Use 5 snapshots to predict current location

for i = 1:length(all_data)
    traj = all_data(i);
    
    % Extract features
    features = extract_features(traj.CSI_magnitude, traj.RSS, ...
                                 traj.SINR, traj.CQI, window_size);
    
    % Corresponding labels (positions)
    T = size(traj.positions, 2);
    n_samples = T - window_size + 1;
    labels = traj.positions(1:2, window_size:end)';  % [x, y] for each window
    
    all_features = [all_features; features];
    all_labels = [all_labels; labels];
end

% Normalize features
feature_means = mean(all_features, 1);
feature_stds = std(all_features, 1);
all_features_normalized = (all_features - feature_means) ./ (feature_stds + eps);

% Split into train/validation/test
n_samples = size(all_features, 1);
idx = randperm(n_samples);

train_ratio = 0.7;
val_ratio = 0.15;
test_ratio = 0.15;

train_end = floor(train_ratio * n_samples);
val_end = train_end + floor(val_ratio * n_samples);

train_idx = idx(1:train_end);
val_idx = idx(train_end+1:val_end);
test_idx = idx(val_end+1:end);

X_train = all_features_normalized(train_idx, :);
y_train = all_labels(train_idx, :);

X_val = all_features_normalized(val_idx, :);
y_val = all_labels(val_idx, :);

X_test = all_features_normalized(test_idx, :);
y_test = all_labels(test_idx, :);

fprintf('Dataset sizes:\n');
fprintf('  Training: %d samples\n', size(X_train, 1));
fprintf('  Validation: %d samples\n', size(X_val, 1));
fprintf('  Test: %d samples\n', size(X_test, 1));

% Save processed dataset
save('ml_dataset.mat', 'X_train', 'y_train', 'X_val', 'y_val', ...
     'X_test', 'y_test', 'feature_means', 'feature_stds');
```

### 3.2 Model Selection

**Option A: Traditional ML (MATLAB)**
```matlab
%% BASELINE MODEL: RANDOM FOREST

% Train Random Forest for X coordinate
rf_x = TreeBagger(100, X_train, y_train(:,1), ...
    'Method', 'regression', 'MinLeafSize', 5);

% Train Random Forest for Y coordinate
rf_y = TreeBagger(100, X_train, y_train(:,2), ...
    'Method', 'regression', 'MinLeafSize', 5);

% Predict on validation set
y_pred_x = predict(rf_x, X_val);
y_pred_y = predict(rf_y, X_val);
y_pred = [y_pred_x, y_pred_y];

% Compute error
errors = sqrt(sum((y_val - y_pred).^2, 2));  % Euclidean distance
mean_error = mean(errors);
median_error = median(errors);

fprintf('Random Forest Results:\n');
fprintf('  Mean localization error: %.2f meters\n', mean_error);
fprintf('  Median localization error: %.2f meters\n', median_error);
```

**Option B: Neural Network (MATLAB)**
```matlab
%% NEURAL NETWORK MODEL

% Create feedforward network
hidden_layers = [128, 64, 32];  % 3 hidden layers
net = feedforwardnet(hidden_layers, 'trainlm');

% Configure
net.trainParam.epochs = 500;
net.trainParam.lr = 0.01;
net.trainParam.showWindow = true;
net.divideParam.trainRatio = 0.85;
net.divideParam.valRatio = 0.15;
net.divideParam.testRatio = 0.0;

% Train
[net, tr] = train(net, X_train', y_train');

% Predict
y_pred = net(X_test')';

% Evaluate
errors = sqrt(sum((y_test - y_pred).^2, 2));
mean_error = mean(errors);

fprintf('Neural Network Results:\n');
fprintf('  Mean localization error: %.2f meters\n', mean_error);
```

**Option C: Deep Learning (Python/PyTorch)** - Recommended for best results
```python
import torch
import torch.nn as nn
import numpy as np
from scipy.io import loadmat

# Load MATLAB data
data = loadmat('ml_dataset.mat')
X_train = torch.FloatTensor(data['X_train'])
y_train = torch.FloatTensor(data['y_train'])
X_val = torch.FloatTensor(data['X_val'])
y_val = torch.FloatTensor(data['y_val'])

# Define model
class LocationPredictor(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.3),
            
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),
            
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.2),
            
            nn.Linear(64, 32),
            nn.ReLU(),
            
            nn.Linear(32, 2)  # Output: [x, y]
        )
    
    def forward(self, x):
        return self.network(x)

# Create model
model = LocationPredictor(input_dim=X_train.shape[1])
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# Training loop
num_epochs = 100
batch_size = 64

for epoch in range(num_epochs):
    model.train()
    for i in range(0, len(X_train), batch_size):
        batch_X = X_train[i:i+batch_size]
        batch_y = y_train[i:i+batch_size]
        
        # Forward pass
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    
    # Validation
    if (epoch + 1) % 10 == 0:
        model.eval()
        with torch.no_grad():
            val_pred = model(X_val)
            val_loss = criterion(val_pred, y_val)
            
            # Compute localization error
            errors = torch.sqrt(torch.sum((y_val - val_pred)**2, dim=1))
            mean_error = torch.mean(errors).item()
            
            print(f'Epoch {epoch+1}: Val Loss = {val_loss:.4f}, Mean Error = {mean_error:.2f}m')

# Save model
torch.save(model.state_dict(), 'location_predictor.pth')
```

### 3.3 Advanced: LSTM for Temporal Sequences

Since your data is sequential (trajectories), an LSTM can capture temporal dependencies:

```python
class LSTMLocationPredictor(nn.Module):
    def __init__(self, input_dim, hidden_dim=128, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, 
                            batch_first=True, dropout=0.2)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 2)
        )
    
    def forward(self, x):
        # x shape: [batch, sequence_length, features]
        lstm_out, _ = self.lstm(x)
        # Take last time step
        last_output = lstm_out[:, -1, :]
        return self.fc(last_output)
```

---

## Phase 4: Evaluation and Analysis

### 4.1 Performance Metrics

```matlab
%% EVALUATE MODEL PERFORMANCE

% Predict on test set
y_pred = predict_location(model, X_test);  % Your prediction function

% Euclidean distance error
errors = sqrt(sum((y_test - y_pred).^2, 2));

% Statistics
mean_error = mean(errors);
median_error = median(errors);
std_error = std(errors);
percentile_90 = prctile(errors, 90);

fprintf('=== Test Set Performance ===\n');
fprintf('Mean error: %.2f m\n', mean_error);
fprintf('Median error: %.2f m\n', median_error);
fprintf('Std deviation: %.2f m\n', std_error);
fprintf('90th percentile: %.2f m\n', percentile_90);

% CDF of errors
figure;
[f, x] = ecdf(errors);
plot(x, f*100, 'LineWidth', 2);
xlabel('Localization Error [m]');
ylabel('CDF [%]');
title('Cumulative Distribution of Localization Errors');
grid on;

% Scatter plot: true vs predicted
figure;
scatter(y_test(:,1), y_test(:,2), 30, errors, 'filled');
hold on;
scatter(y_pred(:,1), y_pred(:,2), 30, 'r', 'x');
colorbar;
xlabel('X [m]'); ylabel('Y [m]');
title('True Positions (colored by error) vs Predicted (red x)');
legend('True', 'Predicted');
axis equal; grid on;
```

### 4.2 Feature Importance Analysis

```matlab
%% FEATURE IMPORTANCE (for Random Forest)

% Get importance scores
importance = rf_x.OOBPermutedPredictorDeltaError;

% Feature names (define these based on your extract_features function)
feature_names = {'CQI_mean', 'CQI_std', 'CQI_max', 'CQI_min', ...
                 'SINR_mean', 'SINR_std', 'RSS_mean', ...
                 'CSI_spectral_centroid', 'estimated_distance', ...};  % etc.

% Plot
figure;
[~, idx] = sort(importance, 'descend');
barh(importance(idx(1:10)));
set(gca, 'YTick', 1:10, 'YTickLabel', feature_names(idx(1:10)));
xlabel('Importance Score');
title('Top 10 Most Important Features');
grid on;
```

---

## Phase 5: Next Steps and Improvements

### 5.1 Immediate Next Steps

1. **Start Simple**:
   - Run `my_ue_movement_experiment.m` to generate your first dataset
   - Extract basic features (CQI, SINR, RSS statistics)
   - Train a simple Random Forest model
   - Establish baseline performance

2. **Expand Dataset**:
   - Generate 50-100 diverse trajectories
   - Include multiple scenarios (LOS, NLOS)
   - Vary BS positions
   - Cover your entire area of interest

3. **Improve Features**:
   - Add CSI spectral features
   - Include temporal features (trends, rates of change)
   - Experiment with different window sizes
   - Feature selection (remove redundant/low-importance features)

4. **Model Optimization**:
   - Hyperparameter tuning (grid search, random search)
   - Try different architectures
   - Ensemble methods (combine multiple models)

### 5.2 Advanced Improvements

**A. Multi-BS Triangulation**:
```matlab
% Simulate 3-4 BS at different locations
BS_positions = [[0;0;25], [100;0;25], [50;100;25]];

% For each BS, collect CSI/CQI
% Combine features from all BS
% Model learns triangulation naturally
```

**B. Transfer Learning**:
- Train on simulated data (QuaDRiGa)
- Fine-tune on real measurements (if available)
- Domain adaptation techniques

**C. Uncertainty Estimation**:
```python
# Use Bayesian Neural Network or Ensemble
# Output prediction + confidence interval
# Useful for reliability assessment
```

**D. Real-Time Tracking**:
```matlab
% Use Kalman Filter or Particle Filter
% Combine ML predictions with motion model
% Smooth trajectories and handle outliers
```

**E. Environmental Fingerprinting**:
```matlab
% Instead of direct location prediction:
% 1. Create "fingerprint database" (CSI patterns at known locations)
% 2. Match observed CSI to closest fingerprint (k-NN)
% 3. Hybrid: ML + fingerprinting
```

### 5.3 Research Directions

1. **Investigate Impact of**:
   - Bandwidth (narrow vs. wide)
   - Number of subcarriers
   - Frequency band (sub-6 GHz vs. mmWave)
   - Number of base stations
   - Antenna configurations (MIMO)

2. **Compare Approaches**:
   - CSI-only vs. CQI-only vs. combined
   - Time-domain vs. frequency-domain features
   - Instantaneous vs. temporal window features
   - Supervised vs. semi-supervised learning

3. **Validate Generalization**:
   - Train on one scenario, test on another
   - Train in one area, test in different area
   - Cross-validation strategies

### 5.4 Publication/Thesis Contributions

**Potential Novel Contributions**:

1. **Comprehensive Feature Study**: 
   - "Which CSI features are most informative for location prediction?"
   - Compare 50+ different features systematically

2. **Simulation-to-Reality Gap**:
   - "How well do QuaDRiGa-trained models perform on real data?"
   - Develop domain adaptation techniques

3. **Temporal Modeling**:
   - "LSTM vs. Transformer vs. GRU for trajectory-based location prediction"
   - Exploit motion continuity

4. **Multi-User Scenarios**:
   - "Location prediction with interference from other UEs"
   - Realistic network conditions

5. **Hybrid Approaches**:
   - "Combining ML predictions with geometric triangulation"
   - Kalman filtering with ML observations

---

## Phase 6: Practical Implementation Roadmap

### Week 1-2: Setup and First Dataset
- [ ] Verify QuaDRiGa installation and scripts work
- [ ] Run `my_ue_movement_experiment.m` successfully
- [ ] Generate 10 simple trajectories
- [ ] Visualize and understand the data

### Week 3-4: Feature Engineering
- [ ] Implement `extract_features()` function
- [ ] Extract features from your 10 trajectories
- [ ] Visualize feature distributions
- [ ] Identify promising features

### Week 5-6: Baseline Model
- [ ] Prepare train/val/test split
- [ ] Train Random Forest model
- [ ] Evaluate performance
- [ ] Establish baseline error metric

### Week 7-8: Dataset Expansion
- [ ] Generate 50-100 diverse trajectories
- [ ] Include multiple scenarios (LOS, NLOS)
- [ ] Add noise/variability
- [ ] Re-train and evaluate

### Week 9-10: Model Improvement
- [ ] Try Neural Network
- [ ] Hyperparameter tuning
- [ ] Feature selection
- [ ] Compare models

### Week 11-12: Advanced Techniques
- [ ] Implement LSTM for temporal sequences
- [ ] Multi-BS setup
- [ ] Ensemble methods
- [ ] Final evaluation and comparison

### Week 13-14: Analysis and Documentation
- [ ] Performance analysis
- [ ] Feature importance study
- [ ] Visualization of results
- [ ] Write-up findings

---

## Useful Code Snippets

### Generate Diverse Trajectories
```matlab
function [P, type] = generate_random_trajectory(T, type)
    % Generate random realistic trajectory
    % type: 'linear', 'circular', 'random_walk', 'mixed'
    
    if nargin < 2
        types = {'linear', 'circular', 'random_walk'};
        type = types{randi(length(types))};
    end
    
    switch type
        case 'linear'
            start = [rand()*200-100; rand()*200-100; 1.5];
            direction = randn(2,1); direction = direction / norm(direction);
            distance = 50 + rand()*100;
            X = linspace(start(1), start(1) + direction(1)*distance, T);
            Y = linspace(start(2), start(2) + direction(2)*distance, T);
            
        case 'circular'
            center = [rand()*100-50; rand()*100-50];
            radius = 30 + rand()*40;
            theta = linspace(0, 2*pi*rand(), T);
            X = center(1) + radius * cos(theta);
            Y = center(2) + radius * sin(theta);
            
        case 'random_walk'
            start = [rand()*200-100; rand()*200-100];
            X = cumsum([start(1), randn(1,T-1)*5]);
            Y = cumsum([start(2), randn(1,T-1)*5]);
    end
    
    Z = 1.5 * ones(1, T);
    P = [X; Y; Z];
end
```

### Batch Processing
```matlab
function batch_generate_data(output_dir, n_trajectories, T_steps)
    % Generate many trajectories in parallel
    
    parfor i = 1:n_trajectories
        [P, type] = generate_random_trajectory(T_steps);
        
        % Run simulation
        [CSI_data, metrics] = run_quadriga_simulation(P, '3GPP_38.901_UMa_LOS');
        
        % Save individual file
        filename = sprintf('trajectory_%04d.mat', i);
        save_trajectory(fullfile(output_dir, filename), P, CSI_data, metrics, type);
    end
end
```

---

## Expected Results and Benchmarks

**Typical Localization Errors** (from literature):

- **Fingerprinting**: 3-10 meters (dense database)
- **CSI-based ML**: 2-8 meters (good features, large dataset)
- **Multi-BS triangulation**: 5-15 meters (depends on geometry)
- **RSS-only**: 10-25 meters (less accurate)

**Your Target** (realistic for master's project):
- Initial baseline: 15-20 meters
- After optimization: 5-10 meters
- Best case (ideal conditions): 2-5 meters

---

## Resources and References

### Key Papers to Read:
1. "Deep Learning for CSI Feedback and Beamforming" - foundations
2. "Indoor Localization Using CSI Fingerprinting" - practical approaches
3. "Machine Learning for 5G Location Services" - survey paper

### Tools:
- **QuaDRiGa**: Channel simulation
- **MATLAB**: Data generation, feature extraction, initial ML
- **Python (PyTorch/TensorFlow)**: Advanced deep learning
- **scikit-learn**: Classical ML algorithms

### Datasets (for comparison):
- Your own `indoor_location/` dataset (real measurements!)
- Public CSI datasets: AERPAW, Sigfox, LoRa datasets

---

## Success Criteria

**Minimum Viable Project**:
- ✅ Generate 100+ trajectories with QuaDRiGa
- ✅ Extract 15+ meaningful features
- ✅ Train working ML model
- ✅ Achieve < 20m mean localization error
- ✅ Document approach and results

**Strong Project**:
- ✅ Above + multiple scenarios (LOS/NLOS)
- ✅ Feature importance analysis
- ✅ Comparison of 3+ ML models
- ✅ < 10m mean localization error
- ✅ Validated on separate test set

**Excellent Project**:
- ✅ Above + multi-BS triangulation
- ✅ Temporal modeling (LSTM/RNN)
- ✅ Real-time tracking demonstration
- ✅ < 5m mean localization error
- ✅ Novel insights or techniques
- ✅ Validated on real data (if available)

---

## Final Tips

1. **Start simple, iterate quickly**: Don't aim for perfection on first try
2. **Visualize everything**: Plots help you understand what's working
3. **Version control**: Use Git to track your experiments
4. **Document as you go**: Future-you will thank present-you
5. **Validate assumptions**: Check if your features actually correlate with location
6. **Compare baselines**: Random guess, distance-only, etc.
7. **Handle edge cases**: What happens at boundaries, very close to BS, etc.

**Good luck with your project! 🚀📡📍**
