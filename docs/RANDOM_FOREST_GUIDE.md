# Random Forest and Metric Fusion Guide

## Overview

The pipeline now supports:
1. **Multiple Metrics Combined**: Classify using RSS+SINR together, not just separately
2. **Tree-Based Models**: Random Forest and Decision Trees for non-linear learning
3. **Feature Interactions**: Models can learn relationships between metrics

## Why Random Forest?

### Advantages over Gaussian Models:
- **Handles Multiple Features Natively**: Can take [RSS, SINR, CQI] as a single input
- **No Distribution Assumptions**: Doesn't assume Gaussian distributions
- **Learns Non-Linear Patterns**: Captures complex decision boundaries
- **Feature Interactions**: Automatically learns rules like "if RSS is high AND SINR is low → location X"
- **Robust to Outliers**: Tree-based splits are less sensitive to extreme values

### How It Works:

#### Single Metric (e.g., RSS only):
```
Feature Vector: [RSS_value]
Tree learns: "if RSS < -80 dBm → Location 1, else if RSS < -70 → Location 2, ..."
```

#### Combined Metrics (e.g., RSS + SINR):
```
Feature Vector: [RSS_value, SINR_value]
Tree learns: "if RSS < -80 AND SINR > 10 dB → Location 1"
             "if RSS > -70 AND SINR < 5 dB → Location 2"
             ...
```

#### With Transition History (h=2):
```
Feature Vector: [RSS_t-2, SINR_t-2, RSS_t-1, SINR_t-1, RSS_t, SINR_t]
Tree learns temporal + spatial patterns automatically
```

## Metric Combination Approaches

### 1. Feature Concatenation (Current Implementation)
**Best for**: Tree-based models, neural networks

```python
# Single metrics:
RSS_features = [RSS_sample1, RSS_sample2, ...]  # Shape: (n_samples,)
SINR_features = [SINR_sample1, SINR_sample2, ...]  # Shape: (n_samples,)

# Combined:
Combined_features = [[RSS_s1, SINR_s1],
                     [RSS_s2, SINR_s2],
                     ...]  # Shape: (n_samples, 2)
```

**Advantages**:
- Simple and effective
- Works with any ML model
- Model learns feature importance automatically

### 2. Posterior Fusion (Already in fusion_experiments.py)
**Best for**: Gaussian statistical models

Combine predictions from separate models:
- Train RSS model → P(location | RSS)
- Train SINR model → P(location | SINR)  
- Combine: P(location | RSS, SINR) ∝ P(location | RSS) × P(location | SINR)

**Advantages**:
- Works when metrics are independent
- Can weight different metrics differently
- Easier to interpret (see contribution of each metric)

### 3. Multivariate Gaussian (Not yet implemented)
**Best for**: When metrics have known correlations

Model joint distribution: P([RSS, SINR] | location) as 2D Gaussian per location

## Configuration

### Option 1: Config File (config_rf_fusion.json)

```json
{
  "classification": {
    "metrics": [
      "RSS",              // Single metric
      "SINR",             // Single metric
      ["RSS", "SINR"],    // Combined metrics
      ["RSS", "SINR", "CQI"]  // All three combined
    ],
    "model_type": "random_forest"
  }
}
```

### Option 2: Command Line

```bash
# Single metrics only (Gaussian models):
python localization_pipeline.py --data-dir results/sim_data_xxx --metrics RSS SINR

# Combined metrics (requires Random Forest):
python localization_pipeline.py \
  --data-dir results/sim_data_xxx \
  --model random_forest \
  --metrics RSS SINR "RSS,SINR"

# Test all combinations:
python localization_pipeline.py \
  --data-dir results/sim_data_xxx \
  --model random_forest \
  --metrics "RSS" "SINR" "CQI" "RSS,SINR" "RSS,SINR,CQI"
```

## Usage Examples

### Example 1: Compare Single vs Combined Metrics

```bash
# Generate simulation data (MATLAB):
matlab -batch "cd experiments/09_grid_localization; generate_simulation_data"

# Test RSS alone, SINR alone, and RSS+SINR together:
cd experiments/09_grid_localization
python localization_pipeline.py \
  --data-dir ../../results/sim_data_LOS_2026-01-10_xxx \
  --model random_forest \
  --metrics RSS SINR "RSS,SINR"
```

**Expected Results:**
- RSS alone: ~60-70% accuracy (spatial signal strength patterns)
- SINR alone: ~65-75% accuracy (interference patterns)
- RSS+SINR: ~75-85% accuracy (model learns to use both!)

### Example 2: Test All Combinations with History

```bash
python localization_pipeline.py \
  --data-dir results/sim_data_xxx \
  --model random_forest \
  --metrics "RSS,SINR" \
  --max-history 3
```

This will test:
- Static: [RSS_t, SINR_t] → 2 features
- History h=1: [RSS_t-1, SINR_t-1, RSS_t, SINR_t] → 4 features
- History h=2: [RSS_t-2, SINR_t-2, RSS_t-1, SINR_t-1, RSS_t, SINR_t] → 6 features
- History h=3: 8 features

### Example 3: Compare Gaussian vs Random Forest

```bash
# Gaussian on single metrics:
python localization_pipeline.py \
  --data-dir results/sim_data_xxx \
  --model gaussian \
  --metrics RSS SINR

# Random Forest on same data:
python localization_pipeline.py \
  --data-dir results/sim_data_xxx \
  --model random_forest \
  --metrics RSS SINR

# Random Forest with fusion:
python localization_pipeline.py \
  --data-dir results/sim_data_xxx \
  --model random_forest \
  --metrics "RSS,SINR"
```

## Understanding the Results

### Output Files:
- `pipeline_results.npz`: Numerical results for each configuration
- `SUMMARY_REPORT.md`: Human-readable comparison
- Feature importance (future): Which metric contributes most?

### Interpreting Improvements:

**If RSS+SINR > RSS alone:**
- Combined features provide complementary information
- Tree learned useful interactions between metrics

**If RSS+SINR ≈ RSS alone:**
- SINR doesn't add new information (highly correlated with RSS)
- Or: not enough training data to learn interactions

**If History helps (h=3 > h=1):**
- Temporal patterns are informative
- Movement constraints help localization

## Advanced: Adding More Models

The architecture is designed for easy extension:

```python
class MyCustomModel(LocalizationModel):
    def train(self, metric_values, true_locations, train_indices, n_points):
        # metric_values can be 1D or 2D (combined metrics)
        # Your training code here
        pass
    
    def predict(self, metric_value, previous_values=None):
        # Return probability distribution over locations
        pass
    
    def get_name(self):
        return "My Custom Model"
```

Then use it in the pipeline:
```python
model = MyCustomModel()
model.train(metric_values, ...)
results = Evaluator.evaluate_static(model, ...)
```

## Tips for Best Performance

1. **Start with Random Forest**: More robust than Gaussian, handles combined metrics
2. **Test combinations systematically**: RSS, SINR, RSS+SINR to see if fusion helps
3. **Use enough data**: Tree-based models need sufficient training samples (aim for >100 per location)
4. **Check feature correlations**: If RSS and SINR are highly correlated, fusion may not help much
5. **Monitor overfitting**: If transition accuracy >> static, may be overfitting to movement patterns

## Troubleshooting

### "WARNING: Gaussian models only support single metrics"
- You specified combined metrics like ["RSS", "SINR"] with --model gaussian
- Solution: Use --model random_forest

### Low accuracy with combined metrics
- May not have enough training data
- Try increasing steps_per_point in config
- Check if metrics are highly correlated (plot RSS vs SINR)

### Random Forest slower than Gaussian
- Expected: RF trains 100 trees, more computation
- Benefit: Better accuracy and flexibility
- Tip: Use n_estimators parameter to trade speed/accuracy

## Next Steps

- Implement feature importance analysis (see which metric matters most)
- Try other tree-based models (Gradient Boosting, XGBoost)
- Implement multivariate Gaussian for combined metrics
- Add neural networks for even more complex patterns
