# ML Training - Getting Started Guide

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies

```powershell
# Navigate to ml_training folder
cd ml_training

# Install Python packages
pip install -r requirements.txt
```

### 2. Run Interactive Pipeline

```powershell
python quickstart.py
```

This will show you a menu to run:
1. Data Inspection - Quick overview of dataset
2. EDA - Generate comprehensive visualizations
3. Preprocessing - Normalize and prepare data
4. Train Models - Train baseline models
5. Run All - Complete pipeline

### 3. Or Run Individual Steps

```powershell
# Inspect dataset
python data_loader.py --inspect

# Generate EDA report and plots
python eda.py

# Preprocess data
python preprocessing.py

# Train baseline models
python models/baseline_models.py
```

## 📊 Expected Results

Based on the Level 3 analysis, you should see:

| Model | Expected MAE | Expected RMSE | Training Time |
|-------|--------------|---------------|---------------|
| **Linear Regression** | 5-8 m | 6-10 m | < 1s |
| **Ridge** | 5-8 m | 6-10 m | < 1s |
| **Random Forest** | 3-5 m | 4-6 m | ~10s |
| **KNN** | 4-6 m | 5-7 m | < 1s |

## 📁 Output Structure

After running, you'll have:

```
ml_training/
├── output/
│   ├── plots/
│   │   └── eda/
│   │       ├── 01_spatial_distribution.png
│   │       ├── 02_position_histograms.png
│   │       ├── 03_wideband_features.png
│   │       ├── 04_features_vs_distance.png
│   │       ├── 05_subcarrier_patterns.png
│   │       ├── 06_correlation_matrix.png
│   │       └── eda_summary.txt
│   ├── saved_models/
│   │   ├── linear_model.pkl
│   │   ├── ridge_model.pkl
│   │   ├── random_forest_model.pkl
│   │   └── knn_model.pkl
│   ├── results/
│   │   └── baseline_comparison.txt
│   └── processed_data/
│       ├── preprocessor.pkl
│       ├── processed_train.npz
│       └── processed_val.npz
```

## 🎯 Next Steps

1. **Analyze Results**: Check `output/results/baseline_comparison.txt`
2. **View Plots**: Open plots in `output/plots/eda/`
3. **Improve Models**: Modify `config.py` to tune hyperparameters
4. **Feature Engineering**: Try different feature combinations
5. **Deep Learning**: Implement neural networks (coming soon)

## ⚙️ Configuration

Edit `config.py` to customize:
- Dataset path
- Normalization method
- Feature selection
- Model parameters
- Output directories

## 🔧 Troubleshooting

**Problem**: Dataset not found
```
Solution: Update DEFAULT_DATASET_PATH in config.py to point to your exp09 dataset
```

**Problem**: Out of memory
```
Solution: Reduce feature dimensions using PCA in config.py
Set PCA_CONFIG['enabled'] = True
Set PCA_CONFIG['n_components'] = 50
```

**Problem**: Models training too slowly
```
Solution: Disable XGBoost in config.py
Set BASELINE_MODELS['xgboost']['enabled'] = False
```

## 📖 Learn More

- See `README.md` for full documentation
- Check `docs/` folder in project root for detailed guides
- Read `experiments/LEVEL3_RESULTS_ANALYSIS.md` for dataset insights

---

**Ready to start?** Run `python quickstart.py` and select option 5!
