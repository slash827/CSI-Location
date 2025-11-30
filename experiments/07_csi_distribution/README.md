# Level 6: CSI Distribution Study

## 📊 Overview

This level focuses on understanding the **statistical distribution of CSI** at fixed locations in the environment. Instead of generating trajectories, we study how CSI varies when a UE remains at the same position, simulating multiple observations to characterize the probabilistic nature of wireless channels.

## 🎯 Learning Objectives

By completing this level, you will:

- Understand CSI variability at fixed locations
- Characterize statistical properties (mean, variance, distributions)
- Study spatial patterns of CSI across the environment
- Create probabilistic maps of signal quality
- Learn about channel fading and its statistics
- Prepare for probabilistic localization approaches

## 📁 Experiments

### Experiment 12: CSI Distribution Study
**File**: `exp12_csi_distribution.m`  
**Configuration**: `config_csi_distribution.m`  
**Time**: 30-90 minutes (depending on hardware)

#### What it does:
- Creates a **200×200m plane** with a single BS at the center
- Defines a **20×20 grid** (400 locations total)
- At each grid point, simulates **100 CSI observations**
- Uses **5G network at 3 GHz** with heterogeneous environment (LOS/NLOS)
- Computes statistical metrics at each location
- Generates spatial heatmaps and distribution plots

#### Key Parameters:
```matlab
Grid: 20×20 points over 200×200m area
Samples per point: 100
Total simulations: 40,000 (400 points × 100 samples)
BS position: Center of plane (100, 100, 25)m
Frequency: 3 GHz (5G mid-band)
Bandwidth: 100 MHz
Environment: Heterogeneous (50% LOS, 50% NLOS)
```

#### Output:
1. **Statistics** (saved in `statistics/` folder):
   - Mean RSS, SINR, CQI at each grid point
   - Standard deviation maps
   - Path loss analysis

2. **Raw Samples** (saved in `data/` folder):
   - All 100 CSI samples per grid point
   - Complete frequency response
   - Grid configuration

3. **Visualizations** (saved in `plots/` folder):
   - Mean RSS/SINR/CQI heatmaps
   - Variability (std) heatmaps
   - Distribution histograms at sample points
   - Path loss vs distance scatter plots
   - 3D surface plots

#### What you'll learn:

1. **Channel Variability**:
   - CSI changes even at fixed locations due to:
     - Fast fading (multipath)
     - Environmental dynamics
     - Noise and interference
   - Standard deviation quantifies uncertainty

2. **Spatial Patterns**:
   - RSS/SINR decreases with distance from BS
   - Variability may be location-dependent
   - LOS vs NLOS affects both mean and variance

3. **Statistical Distributions**:
   - CSI metrics may follow specific distributions
   - Different locations have different characteristics
   - Helps understand measurement reliability

4. **Applications**:
   - **Probabilistic localization**: Use distributions for Bayesian positioning
   - **Radio mapping**: Create fingerprint databases with uncertainty
   - **Network planning**: Understand coverage variability
   - **Model validation**: Compare simulated vs measured statistics

## 🚀 Quick Start

### Prerequisites
Before running this experiment, ensure you have:
- Completed experiments 01-04 (understand basic QuaDRiGa usage)
- QuaDRiGa properly installed
- `utils/` folder in MATLAB path
- At least 1-2 hours available for simulation

### Running the Experiment

```matlab
% 1. Navigate to experiment folder
cd experiments/06_csi_distribution

% 2. (Optional) Review/modify configuration
edit config_csi_distribution.m

% 3. Run the experiment
exp12_csi_distribution

% 4. Check results
% Results will be in: results/exp12_YYYY-MM-DD_HH-MM-SS/
```

### Expected Runtime
- **Grid points**: 400 (20×20)
- **Samples per point**: 100
- **Total simulations**: 40,000
- **Estimated time**: 30-90 minutes
  - Depends on CPU speed and QuaDRiGa performance
  - Progress updates every 5%

## 📊 Understanding the Results

### 1. Mean RSS Heatmap
Shows average received signal strength at each location:
- **Brighter colors**: Stronger signal
- **Pattern**: Generally decreases with distance from BS
- **Irregularities**: Due to LOS/NLOS variations

### 2. RSS Standard Deviation Heatmap
Shows measurement variability at each location:
- **High std**: Unreliable, high uncertainty
- **Low std**: Stable, predictable signal
- **Pattern**: May be higher in NLOS regions

### 3. Distribution Plots
Histograms at sample locations:
- **Shape**: May be Gaussian, Rayleigh, or other
- **Width**: Indicates variability
- **Center**: Mean value

### 4. Path Loss Analysis
Relationship between distance and signal:
- **Expected**: Path loss increases with distance
- **Scatter**: Due to environment heterogeneity
- **Helps**: Validate propagation models

## 🔧 Customization

### Modify Grid Resolution
```matlab
% In config_csi_distribution.m
config.grid.grid_points = [10, 10];  % Faster (10×10 = 100 points)
config.grid.grid_points = [30, 30];  % More detailed (30×30 = 900 points)
```

### Change Sampling Rate
```matlab
config.grid.n_samples_per_point = 50;   % Faster, less statistical confidence
config.grid.n_samples_per_point = 200;  % Slower, better statistics
```

### Adjust Environment
```matlab
% More LOS (open environment)
config.scenario.los_probability = 0.8;

% More NLOS (dense urban)
config.scenario.los_probability = 0.2;
```

### Change Frequency
```matlab
% Low frequency (better coverage)
config.scenario.frequency = 2e9;  % 2 GHz

% High frequency (mmWave)
config.scenario.frequency = 28e9;  % 28 GHz
```

### Modify Plane Size
```matlab
% Smaller area (faster)
config.grid.plane_size = [100, 100];

% Larger area (more coverage analysis)
config.grid.plane_size = [500, 500];
```

## 📈 Statistical Analysis Tips

### 1. Load Results
```matlab
% Load statistics
load('results/exp12_XXXX/statistics/csi_statistics.mat');

% Access mean RSS at point (i,j)
rss_mean = stats.mean_RSS(i, j);
rss_std = stats.std_RSS(i, j);

% Load all samples
load('results/exp12_XXXX/data/all_samples.mat');

% Get all RSS samples at point (i,j)
rss_samples = squeeze(all_samples.RSS(i, j, :));
```

### 2. Fit Distributions
```matlab
% Example: Fit Gaussian to RSS at a point
rss_samples = squeeze(all_samples.RSS(10, 10, :));

% Fit normal distribution
pd = fitdist(rss_samples, 'Normal');
fprintf('Mean: %.2f dBm, Std: %.2f dB\n', pd.mu, pd.sigma);

% Test goodness of fit
[h, p] = kstest(rss_samples, 'CDF', pd);
fprintf('Kolmogorov-Smirnov test: p-value = %.3f\n', p);
```

### 3. Spatial Correlation
```matlab
% Compute correlation between nearby points
[corr_x, corr_y] = meshgrid(1:size(stats.mean_RSS, 2), 1:size(stats.mean_RSS, 1));

% Example: correlation vs distance
distances = sqrt((corr_x - 10).^2 + (corr_y - 10).^2);
correlations = arrayfun(@(d) corr(stats.mean_RSS(10,10), stats.mean_RSS(d)), 1:numel(stats.mean_RSS));

plot(distances(:), correlations(:), '.');
xlabel('Distance (grid points)');
ylabel('Correlation');
```

## 🎓 Key Concepts

### Fast Fading
- **What**: Rapid fluctuations in signal due to multipath
- **Time scale**: Milliseconds
- **In this exp**: Captured by simulating multiple samples at same location
- **Statistics**: Often modeled as Rayleigh (NLOS) or Rician (LOS)

### Slow Fading (Shadowing)
- **What**: Gradual changes due to large obstacles
- **Time scale**: Seconds to minutes
- **In this exp**: Captured by spatial variations across grid
- **Statistics**: Often log-normal distribution

### Channel Stationarity
- **Assumption**: In this experiment, channel is stationary at each point
- **Reality**: In real systems, even fixed UE experiences time variations
- **Implication**: Our statistics represent "snapshot" distributions

## 🔍 Applications

### 1. Probabilistic Localization
Use CSI distributions for Bayesian positioning:
```matlab
% For a new measurement z at unknown location
% Compute likelihood p(z | position) using learned distributions
likelihood = normpdf(z, stats.mean_RSS(i,j), stats.std_RSS(i,j));
```

### 2. Radio Fingerprinting
Create a database of CSI "fingerprints" with uncertainty:
```matlab
fingerprint_db = struct();
fingerprint_db.positions = [grid_x(:), grid_y(:)];
fingerprint_db.mean_rss = stats.mean_RSS(:);
fingerprint_db.std_rss = stats.std_RSS(:);
```

### 3. Coverage Analysis
Identify areas with reliable vs unreliable signals:
```matlab
% Find unreliable areas (high variability)
unreliable_mask = stats.std_RSS > 5;  % Std > 5 dB

% Find coverage holes (low RSS)
coverage_holes = stats.mean_RSS < -100;  % RSS < -100 dBm
```

## ⚠️ Important Notes

### Computational Cost
- **40,000 simulations** take significant time
- Consider starting with smaller grid (e.g., 10×10) for testing
- Each QuaDRiGa channel generation takes ~0.1-0.2 seconds

### Memory Usage
- Raw samples can be large (400 points × 100 samples × 256 subcarriers)
- Disable `config.output.save_raw_samples = false` if memory is limited
- Statistics are much smaller and always saved

### Statistical Confidence
- 100 samples provides good statistical estimates
- For critical applications, may need 500-1000 samples
- Trade-off between accuracy and computation time

## 🎯 Completion Checklist

After running this experiment, you should be able to:

- [ ] Understand why CSI varies at fixed locations
- [ ] Interpret mean and variance heatmaps
- [ ] Recognize spatial patterns in signal quality
- [ ] Explain path loss vs distance relationship
- [ ] Load and analyze statistical results
- [ ] Understand applications in localization

## 📚 References

### Related Experiments
- **Exp01-03**: Basic CSI concepts
- **Exp07-09**: Trajectory-based data generation
- **Exp10-11**: Large-scale datasets

### Next Steps
After this experiment:
1. Analyze distribution shapes at different locations
2. Study correlation between nearby points
3. Compare with theoretical models (Rayleigh, Rician)
4. Use distributions for probabilistic ML models
5. Consider temporal variations (future work)

## 🆘 Troubleshooting

### Simulation is too slow
- Reduce grid size: `config.grid.grid_points = [10, 10]`
- Reduce samples: `config.grid.n_samples_per_point = 50`
- Disable raw sample saving: `config.output.save_raw_samples = false`

### Out of memory
- Disable raw samples: `config.output.save_raw_samples = false`
- Process in batches (modify script to save incrementally)
- Reduce grid size

### Unexpected results
- Check BS position is at center: `config.bs.position`
- Verify grid coordinates: `config.grid.x_coords`, `config.grid.y_coords`
- Check scenario type: `config.scenario.type`
- Review LOS probability: `config.scenario.los_probability`

---

**Good luck with your CSI distribution study!** 🚀

For questions or issues, refer to:
- `docs/TECHNICAL_FAQ.md`
- `docs/SCRIPTS_EXPLAINED.md`
- QuaDRiGa documentation
