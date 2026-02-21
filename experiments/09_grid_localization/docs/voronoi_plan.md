# GitHub Copilot Prompt: Heterogeneous Environment Implementation

## 🎯 OBJECTIVE

Integrate `AreaGenerator.m` to create a **heterogeneous Voronoi-based simulation environment** for 5G CSI localization, then run existing localization pipelines on the generated data.

---

## 📋 CONTEXT

### Current State:
- **Existing Project:** CSI-based indoor localization using QuaDRiGa + Machine Learning
- **Problem:** Current simulations use homogeneous environments (all points same scenario)
- **Impact:** Transition-based methods show only 3-4% improvement
- **Advisor Feedback:** Need heterogeneous environment (Voronoi tessellation) to see 20-40% improvements

### What We Have:
1. **AreaGenerator.m** - Ready-to-use Voronoi area generator (provided)
2. **Existing ML Pipeline:**
   - MATLAB: `generate_simulation_data.m` (QuaDRiGa data generation)
   - Python: `localization_pipeline.py` (ML models: Gaussian, Random Forest, XGBoost)
3. **Existing Models:** Static, Transition-based, Random Forest

### What We Need:
1. **GeometryUtils.m** - Helper class for Voronoi cell assignment
2. **Integration code** - Connect AreaGenerator → QuaDRiGa → ML Pipeline
3. **Updated pipeline** - Run localization on heterogeneous data

---

## 🔧 TASK 1: Create GeometryUtils.m

**File:** `utils/GeometryUtils.m`

**Requirements:**
```matlab
classdef GeometryUtils
    % GEOMETRYUTILS - Geometry helper functions for Voronoi areas
    %
    % Static methods:
    %   - find_area: Find which Voronoi area a point belongs to
    %   - check_if_in_bounds: Check if point is within bounds
    
    methods (Static)
        
        function area_idx = find_area(point, areas)
            % FIND_AREA Find which Voronoi area a point belongs to
            %
            % Input:
            %   point - [x, y] coordinate
            %   areas - struct array with .seed fields
            %
            % Output:
            %   area_idx - index of closest area (Voronoi cell assignment)
            %
            % Implementation:
            %   Uses nearest-neighbor (Euclidean distance to seeds)
            
            % TODO: Extract all seeds from areas
            % TODO: Compute distances from point to all seeds
            % TODO: Return index of minimum distance
        end
        
        
        function in_bounds = check_if_in_bounds(point, bounds)
            % CHECK_IF_IN_BOUNDS Check if point is within bounds
            %
            % Input:
            %   point  - [x, y] coordinate
            %   bounds - [x_min, x_max, y_min, y_max]
            %
            % Output:
            %   in_bounds - boolean
            
            % TODO: Check x >= x_min, x <= x_max
            % TODO: Check y >= y_min, y <= y_max
            % TODO: Return AND of all conditions
        end
        
    end
end
```

**Expected Implementation:**
- Use Euclidean distance for Voronoi assignment
- Simple bounds checking with logical operators
- No external dependencies

---

## 🔧 TASK 2: Create Heterogeneous Simulation Script

**File:** `experiments/heterogeneous_simulation.m`

**Requirements:**

### A. Configuration Section
```matlab
%% CONFIGURATION
clear all; close all;

% Simulation parameters
grid_size = 7;              % 7×7 grid of UE positions
spacing = 5;                % 5 meters between grid points
center_freq = 3.5e9;        % 3.5 GHz carrier

% Voronoi area configuration
config = struct();
config.area_bounds = [0, 50, 0, 50];  % [x_min, x_max, y_min, y_max]
config.num_areas = 4;                 % Number of Voronoi cells
config.area_types = {
    'shopping_center',
    'residential', 
    'office',
    'park'
};
config.transition_width = 5;          % Meters (not used in basic version)
config.random_seed = 42;              % For reproducibility

% Base station configuration
config.bs.positions = [25, 25, 25];   % Center BS [x, y, height]
```

### B. Area Generation
```matlab
%% GENERATE HETEROGENEOUS AREAS
fprintf('=== Generating Heterogeneous Areas ===\n');

% Generate Voronoi areas using AreaGenerator
areas = AreaGenerator.generate(config);

% Expected output from AreaGenerator:
%   areas(i).id           - Area identifier
%   areas(i).seed         - [x, y] Voronoi seed point  
%   areas(i).scenario     - QuaDRiGa scenario string (e.g., '3GPP_38.901_UMi_LOS')
%   areas(i).area_type    - Type string (e.g., 'shopping_center')
%   areas(i).transition_width - Transition width in meters
```

### C. QuaDRiGa Setup with Heterogeneous Scenarios
```matlab
%% QUADRIGA SETUP
fprintf('=== Setting up QuaDRiGa ===\n');

% Simulation parameters
s = qd_simulation_parameters;
s.center_frequency = center_freq;
s.sample_density = 2;
s.use_absolute_delays = 1;
s.show_progress_bars = 0;

% Create layout
l = qd_layout(s);

% Base station
l.no_tx = 1;
l.tx_position = config.bs.positions';
l.tx_array = qd_arrayant('3gpp-3d', 8, 8, center_freq);

%% CREATE GRID WITH HETEROGENEOUS SCENARIO ASSIGNMENT
fprintf('=== Creating UE Grid ===\n');

point_idx = 1;
grid_positions = [];
area_assignments = [];
scenario_per_point = {};

for ix = 1:grid_size
    for iy = 1:grid_size
        % Grid position
        x = (ix - 1) * spacing;
        y = (iy - 1) * spacing;
        
        % Create stationary track
        t = qd_track('linear', 0, 0);
        t.initial_position = [x; y; 1.5];
        
        % ⭐ KEY: Find which Voronoi area this point belongs to
        point = [x, y];
        area_idx = GeometryUtils.find_area(point, areas);
        
        % ⭐ Assign scenario from the area
        t.scenario = areas(area_idx).scenario;
        
        % Store metadata
        grid_positions(point_idx, :) = [x, y];
        area_assignments(point_idx) = area_idx;
        scenario_per_point{point_idx} = t.scenario;
        
        % Add track to layout
        l.rx_track(point_idx) = t;
        point_idx = point_idx + 1;
    end
end

l.no_rx = point_idx - 1;

fprintf('Created %d UE positions across %d areas\n', l.no_rx, length(areas));
```

### D. Channel Generation
```matlab
%% GENERATE CHANNELS
fprintf('=== Generating Channels ===\n');

% Apply scenarios to tracks
l.set_scenario();

% Initialize channel builder
cb = l.init_builder();

% Generate channel parameters
tic;
cb.gen_parameters();
fprintf('Channel generation time: %.1f seconds\n', toc);

% Get channels
channels = cb.get_channels();
```

### E. Extract Metrics
```matlab
%% EXTRACT CSI METRICS
fprintf('=== Extracting Metrics ===\n');

% Initialize arrays
rss_dbm = zeros(1, l.no_rx);
sinr_dbm = zeros(1, l.no_rx);
cqi = zeros(1, l.no_rx);

% Extract metrics for each UE
for i = 1:l.no_rx
    c = channels(i);
    
    % RSS (Received Signal Strength)
    coeff = c.coeff;
    power_linear = sum(abs(coeff(:)).^2);
    rss_dbm(i) = 10*log10(power_linear * 1000);  % Convert to dBm
    
    % SINR (Signal-to-Interference-plus-Noise Ratio)
    % For now, use simple approximation (can be improved)
    noise_power_dbm = -95;  % Thermal noise floor
    signal_linear = 10^(rss_dbm(i)/10);
    noise_linear = 10^(noise_power_dbm/10);
    sinr_linear = signal_linear / noise_linear;
    sinr_dbm(i) = 10*log10(sinr_linear);
    
    % CQI (Channel Quality Indicator) - quantized SINR
    cqi(i) = min(15, max(0, round((sinr_dbm(i) + 10) / 2)));
end
```

### F. Analysis & Validation
```matlab
%% HETEROGENEITY ANALYSIS
fprintf('\n=== Heterogeneity Analysis ===\n');

% Overall statistics
fprintf('\nOverall Statistics:\n');
fprintf('  Total RSS range: %.1f dB\n', range(rss_dbm));
fprintf('  RSS std: %.1f dB\n', std(rss_dbm));
fprintf('  Unique scenarios: %d\n', length(unique(scenario_per_point)));

% Per-area statistics
fprintf('\nPer-Area Statistics:\n');
for area_id = 1:length(areas)
    points_in_area = find(area_assignments == area_id);
    
    if isempty(points_in_area)
        continue;
    end
    
    rss_in_area = rss_dbm(points_in_area);
    
    fprintf('\n  Area %d (%s):\n', area_id, areas(area_id).area_type);
    fprintf('    Scenario: %s\n', areas(area_id).scenario);
    fprintf('    Points: %d\n', length(points_in_area));
    fprintf('    RSS: %.1f ± %.1f dBm\n', mean(rss_in_area), std(rss_in_area));
    fprintf('    Range: %.1f dB\n', range(rss_in_area));
end
```

### G. Visualization
```matlab
%% VISUALIZATION
fprintf('\n=== Creating Visualizations ===\n');

% Figure 1: Voronoi Areas with UE positions
fig1 = AreaGenerator.plot_areas_combined(areas, config, grid_positions);
saveas(fig1, 'results/heterogeneous_areas.png');

% Figure 2: RSS Heatmap
fig2 = figure('Position', [100, 100, 1200, 500]);

subplot(1,2,1);
AreaGenerator.plot_heatmap_only(areas, config, rss_dbm, 'RSS [dBm]');

subplot(1,2,2);
scatter(grid_positions(:,1), grid_positions(:,2), 100, rss_dbm, 'filled');
colorbar;
title('RSS by UE Position');
xlabel('X [m]'); ylabel('Y [m]');
clim([min(rss_dbm), max(rss_dbm)]);

saveas(fig2, 'results/rss_distribution.png');
```

### H. Save Data
```matlab
%% SAVE DATA FOR PYTHON PIPELINE
fprintf('\n=== Saving Data ===\n');

% Prepare data structure
simulation_data = struct();
simulation_data.grid_positions = grid_positions;
simulation_data.area_assignments = area_assignments;
simulation_data.scenarios = scenario_per_point;
simulation_data.rss_dbm = rss_dbm;
simulation_data.sinr_dbm = sinr_dbm;
simulation_data.cqi = cqi;
simulation_data.areas = areas;
simulation_data.config = config;

% Save in MATLAB v7 format (compatible with scipy.io.loadmat)
output_file = 'results/heterogeneous_simulation_data.mat';
save(output_file, 'simulation_data', '-v7');

fprintf('Data saved to: %s\n', output_file);
fprintf('\n✅ Heterogeneous simulation complete!\n');
```

---

## 🔧 TASK 3: Update Python Localization Pipeline

**File:** `ml_training/run_heterogeneous_localization.py`

**Requirements:**

### A. Load Heterogeneous Data
```python
"""
Run localization on heterogeneous environment data.

This script:
1. Loads data from heterogeneous QuaDRiGa simulation
2. Prepares features and labels
3. Runs existing localization models (Gaussian, Random Forest)
4. Compares results to homogeneous baseline
"""

import numpy as np
import scipy.io
import matplotlib.pyplot as plt
from pathlib import Path

# Import existing pipeline modules
from localization_pipeline import (
    GaussianStaticModel,
    GaussianTransitionModel,
    RandomForestModel
)

def load_heterogeneous_data(mat_file_path):
    """
    Load heterogeneous simulation data from MATLAB .mat file.
    
    Args:
        mat_file_path: Path to .mat file
        
    Returns:
        dict with keys: rss, sinr, cqi, positions, areas, scenarios
    """
    print(f"Loading data from: {mat_file_path}")
    
    # Load .mat file
    mat_data = scipy.io.loadmat(mat_file_path)
    sim_data = mat_data['simulation_data'][0, 0]  # Unpack struct
    
    # Extract arrays
    data = {
        'rss': sim_data['rss_dbm'].flatten(),
        'sinr': sim_data['sinr_dbm'].flatten(),
        'cqi': sim_data['cqi'].flatten(),
        'positions': sim_data['grid_positions'],
        'area_assignments': sim_data['area_assignments'].flatten(),
        'scenarios': [s[0] for s in sim_data['scenarios'].flatten()],
    }
    
    # Extract areas info
    areas_struct = sim_data['areas']
    data['areas'] = []
    for i in range(len(areas_struct)):
        area = {
            'id': int(areas_struct[i]['id'][0, 0]),
            'seed': areas_struct[i]['seed'].flatten(),
            'scenario': areas_struct[i]['scenario'][0],
            'area_type': areas_struct[i]['area_type'][0],
        }
        data['areas'].append(area)
    
    print(f"  Loaded {len(data['rss'])} data points")
    print(f"  Areas: {len(data['areas'])}")
    print(f"  Unique scenarios: {len(set(data['scenarios']))}")
    
    return data


def prepare_features_labels(data, grid_size=7):
    """
    Prepare features (RSS, SINR, CQI) and labels (grid indices).
    
    Args:
        data: Dictionary from load_heterogeneous_data
        grid_size: Size of grid (e.g., 7 for 7×7)
        
    Returns:
        X: Feature matrix [N, 3] (RSS, SINR, CQI)
        y: Labels [N] (location indices 0 to grid_size²-1)
        positions: [N, 2] actual (x, y) positions
    """
    # Features
    X = np.column_stack([
        data['rss'],
        data['sinr'],
        data['cqi']
    ])
    
    # Labels: map (x, y) positions to grid indices
    positions = data['positions']
    spacing = positions[1, 0] - positions[0, 0]  # Assume uniform spacing
    
    y = []
    for pos in positions:
        ix = int(round(pos[0] / spacing))
        iy = int(round(pos[1] / spacing))
        idx = iy * grid_size + ix  # Row-major indexing
        y.append(idx)
    
    y = np.array(y)
    
    print(f"\nFeature preparation:")
    print(f"  X shape: {X.shape}")
    print(f"  y shape: {y.shape}")
    print(f"  Location range: {y.min()} to {y.max()}")
    
    return X, y, positions


def analyze_heterogeneity(data):
    """
    Analyze and print heterogeneity statistics.
    """
    print("\n=== Heterogeneity Analysis ===")
    
    # RSS variation
    print(f"\nRSS Statistics:")
    print(f"  Range: {np.ptp(data['rss']):.1f} dB")
    print(f"  Mean: {np.mean(data['rss']):.1f} dBm")
    print(f"  Std: {np.std(data['rss']):.1f} dB")
    
    # Per-area statistics
    print(f"\nPer-Area Statistics:")
    for area in data['areas']:
        area_id = area['id']
        mask = data['area_assignments'] == area_id
        
        if not np.any(mask):
            continue
        
        rss_in_area = data['rss'][mask]
        print(f"\n  Area {area_id} ({area['area_type']}):")
        print(f"    Scenario: {area['scenario']}")
        print(f"    Points: {np.sum(mask)}")
        print(f"    RSS: {np.mean(rss_in_area):.1f} ± {np.std(rss_in_area):.1f} dBm")


def run_localization_models(X, y, positions):
    """
    Run all localization models and compare results.
    
    Args:
        X: Features [N, 3]
        y: Labels [N]
        positions: Actual positions [N, 2]
        
    Returns:
        results: Dictionary of model results
    """
    print("\n=== Running Localization Models ===")
    
    # Split data (80/20 train/test)
    n_samples = len(y)
    n_train = int(0.8 * n_samples)
    
    indices = np.random.permutation(n_samples)
    train_idx = indices[:n_train]
    test_idx = indices[n_train:]
    
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    pos_train, pos_test = positions[train_idx], positions[test_idx]
    
    print(f"  Train: {len(train_idx)} samples")
    print(f"  Test: {len(test_idx)} samples")
    
    # Initialize models
    models = {
        'Static (RSS only)': GaussianStaticModel(),
        'Transition-based': GaussianTransitionModel(history_length=2),
        'Random Forest': RandomForestModel(n_estimators=100)
    }
    
    results = {}
    
    # Train and evaluate each model
    for name, model in models.items():
        print(f"\n  Training {name}...")
        
        # Train
        model.train(X_train, y_train)
        
        # Predict
        y_pred = model.predict(X_test)
        
        # Evaluate
        accuracy = np.mean(y_pred == y_test)
        
        # Compute MAE (mean absolute error in meters)
        # Convert predictions to positions and compute Euclidean distance
        mae = compute_mae(y_pred, y_test, pos_test)
        
        results[name] = {
            'accuracy': accuracy,
            'mae': mae,
            'predictions': y_pred
        }
        
        print(f"    Accuracy: {accuracy*100:.1f}%")
        print(f"    MAE: {mae:.2f} meters")
    
    return results


def compute_mae(y_pred, y_true, positions, grid_size=7, spacing=5):
    """
    Compute Mean Absolute Error in meters.
    
    Args:
        y_pred: Predicted location indices
        y_true: True location indices
        positions: True positions [N, 2]
        grid_size: Grid size
        spacing: Grid spacing in meters
        
    Returns:
        mae: Mean absolute error in meters
    """
    errors = []
    
    for pred_idx, true_idx, true_pos in zip(y_pred, y_true, positions):
        # Convert predicted index to position
        pred_ix = pred_idx % grid_size
        pred_iy = pred_idx // grid_size
        pred_pos = np.array([pred_ix * spacing, pred_iy * spacing])
        
        # Euclidean distance
        distance = np.linalg.norm(pred_pos - true_pos)
        errors.append(distance)
    
    return np.mean(errors)


def visualize_results(data, results):
    """
    Create visualizations of results.
    """
    print("\n=== Creating Visualizations ===")
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Plot 1: RSS distribution by area
    ax = axes[0]
    for area in data['areas']:
        area_id = area['id']
        mask = data['area_assignments'] == area_id
        positions = data['positions'][mask]
        rss = data['rss'][mask]
        
        ax.scatter(positions[:, 0], positions[:, 1], 
                  c=rss, s=100, label=f"Area {area_id}")
    
    ax.set_title('RSS Distribution (Heterogeneous)')
    ax.set_xlabel('X [m]')
    ax.set_ylabel('Y [m]')
    ax.legend()
    
    # Plot 2: Model comparison
    ax = axes[1]
    model_names = list(results.keys())
    accuracies = [results[name]['accuracy'] * 100 for name in model_names]
    
    ax.bar(range(len(model_names)), accuracies)
    ax.set_xticks(range(len(model_names)))
    ax.set_xticklabels(model_names, rotation=45, ha='right')
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Model Comparison')
    ax.grid(axis='y', alpha=0.3)
    
    # Plot 3: MAE comparison
    ax = axes[2]
    maes = [results[name]['mae'] for name in model_names]
    
    ax.bar(range(len(model_names)), maes)
    ax.set_xticks(range(len(model_names)))
    ax.set_xticklabels(model_names, rotation=45, ha='right')
    ax.set_ylabel('MAE (meters)')
    ax.set_title('Localization Error')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('results/heterogeneous_localization_results.png', dpi=300)
    print("  Saved: results/heterogeneous_localization_results.png")


def main():
    """
    Main execution function.
    """
    print("=" * 60)
    print("Heterogeneous Environment Localization")
    print("=" * 60)
    
    # Load data
    data_file = 'results/heterogeneous_simulation_data.mat'
    data = load_heterogeneous_data(data_file)
    
    # Analyze heterogeneity
    analyze_heterogeneity(data)
    
    # Prepare features and labels
    X, y, positions = prepare_features_labels(data, grid_size=7)
    
    # Run localization models
    results = run_localization_models(X, y, positions)
    
    # Visualize results
    visualize_results(data, results)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Heterogeneity: {np.ptp(data['rss']):.1f} dB RSS range")
    print(f"Areas: {len(data['areas'])} with different scenarios")
    
    print("\nModel Performance:")
    for name, res in results.items():
        print(f"  {name}:")
        print(f"    Accuracy: {res['accuracy']*100:.1f}%")
        print(f"    MAE: {res['mae']:.2f}m")
    
    print("\n✅ Analysis complete!")


if __name__ == '__main__':
    main()
```

---

## 📊 EXPECTED OUTCOMES

### Heterogeneity Metrics:
```
Before (Homogeneous):
  RSS range: ~8 dB
  All same scenario
  
After (Heterogeneous):
  RSS range: 25-35 dB ✓
  4 different scenarios ✓
  Voronoi cell structure ✓
```

### Localization Performance:
```
Expected improvements with heterogeneous environment:

Static baseline:     65% → 75% accuracy
Transition-based:    69% → 85% accuracy (+20% relative!)
Random Forest:       73% → 90% accuracy

MAE improvements:
Static:        3.5m → 2.8m
Transition:    3.2m → 1.9m  (-40% error!)
Random Forest: 2.9m → 1.5m
```

---

## ✅ VALIDATION CHECKLIST

After implementation, verify:

- [ ] GeometryUtils.m compiles without errors
- [ ] AreaGenerator.generate(config) runs successfully
- [ ] QuaDRiGa generates channels for all grid points
- [ ] RSS range > 20 dB (heterogeneity achieved)
- [ ] Different scenarios assigned to different areas
- [ ] Python pipeline loads MATLAB data successfully
- [ ] All localization models run without errors
- [ ] Results show improved performance vs homogeneous baseline
- [ ] Visualizations created (areas plot, RSS heatmap, results plot)
- [ ] Data saved in MATLAB v7 format (-v7 flag)

---

## 📝 NOTES

### File Locations:
- **MATLAB code:** `experiments/heterogeneous_simulation.m`
- **Utils:** `utils/GeometryUtils.m`, `utils/AreaGenerator.m`
- **Python:** `ml_training/run_heterogeneous_localization.py`
- **Results:** `results/heterogeneous_*.{mat,png}`

### Dependencies:
- **MATLAB:** QuaDRiGa, AreaGenerator.m (provided), GeometryUtils.m (to create)
- **Python:** scipy, numpy, matplotlib, existing pipeline modules

### Key Integration Points:
1. **AreaGenerator → QuaDRiGa:** Scenario assignment via `track.scenario`
2. **QuaDRiGa → Python:** MATLAB v7 .mat file with struct
3. **Python → Models:** Existing `localization_pipeline.py` classes

---

## 🎯 SUCCESS CRITERIA

**Primary Goal:** Demonstrate that heterogeneous environment significantly improves transition-based localization

**Metrics:**
- ✅ RSS range > 25 dB (vs ~8 dB homogeneous)
- ✅ Transition improvement > 15% (vs 3-4% homogeneous)
- ✅ Random Forest MAE < 2.0m (vs ~3.0m homogeneous)

**Deliverables:**
1. Working heterogeneous simulation script
2. Python analysis with model comparisons
3. Visualizations showing heterogeneity and results
4. Data files for future experiments

---

## 💡 IMPLEMENTATION TIPS

1. **Start with GeometryUtils** - It's the simplest, validate first
2. **Test AreaGenerator** - Run standalone to verify output
3. **Small grid first** - Use 3×3 to debug, then scale to 7×7
4. **Check scenarios** - Print assigned scenarios, verify variety
5. **Validate RSS range** - Should be 3-4x larger than homogeneous
6. **Python integration** - Test data loading separately first

---

## 🔄 ITERATION PLAN

### Phase 1: Basic Implementation (Day 1)
- Create GeometryUtils.m
- Create heterogeneous_simulation.m skeleton
- Test area generation only

### Phase 2: QuaDRiGa Integration (Day 2)
- Add QuaDRiGa channel generation
- Extract RSS/SINR/CQI
- Verify heterogeneity metrics

### Phase 3: Python Pipeline (Day 3)
- Create run_heterogeneous_localization.py
- Load data, run models
- Generate visualizations

### Phase 4: Analysis & Comparison (Day 4)
- Compare to homogeneous baseline
- Document improvements
- Prepare presentation for advisors

---

END OF PROMPT