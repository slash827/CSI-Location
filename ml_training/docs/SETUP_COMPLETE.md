# ML Training Setup Complete! 🎉

## ✅ What Was Created

A complete Python-based ML training pipeline for CSI-based indoor localization has been created in the `ml_training/` folder.

## 📁 Folder Structure

```
ml_training/
├── README.md                    # Comprehensive documentation
├── QUICKSTART.md               # Quick start guide (read this first!)
├── requirements.txt            # Python dependencies
├── .gitignore                  # Ignore large files and outputs
│
├── config.py                   # Configuration and paths (edit this to customize)
├── data_loader.py             # Load .mat files from QuaDRiGa
├── preprocessing.py           # Data preprocessing and feature engineering
├── eda.py                     # Exploratory Data Analysis
├── utils.py                   # Utility functions (plotting, metrics)
├── quickstart.py              # Interactive pipeline runner
│
├── models/
│   ├── __init__.py
│   ├── baseline_models.py     # Linear, Ridge, RF, KNN models
│   ├── neural_networks.py     # TODO: Deep learning models
│   └── advanced_models.py     # TODO: CNN, LSTM models
│
└── output/                    # Created automatically
    ├── plots/                 # EDA visualizations
    ├── saved_models/          # Trained model files
    ├── results/               # Evaluation reports
    └── processed_data/        # Pre-processed datasets
```

## 🚀 How to Use

### Option 1: Interactive Pipeline (Recommended)

```powershell
cd ml_training
pip install -r requirements.txt
python quickstart.py
```

Then select option 5 to run the complete pipeline!

### Option 2: Step-by-Step

```powershell
# 1. Inspect dataset
python data_loader.py --inspect

# 2. Generate EDA report (6 plots + summary)
python eda.py

# 3. Preprocess data
python preprocessing.py

# 4. Train baseline models
python models/baseline_models.py
```

### Option 3: Use as Python Module

```python
# In your own script or notebook
from data_loader import CSIDataLoader
from preprocessing import preprocess_dataset
from models.baseline_models import train_all_baseline_models

# Load and preprocess
X_train, y_train, X_val, y_val, _ = preprocess_dataset()

# Train models
results = train_all_baseline_models(X_train, y_train, X_val, y_val)
```

## 📊 What You'll Get

### 1. EDA Outputs (from `eda.py`)

6 comprehensive plots in `output/plots/eda/`:
- `01_spatial_distribution.png` - Where are the samples?
- `02_position_histograms.png` - X/Y distributions
- `03_wideband_features.png` - RSS, SINR, CQI, Distance
- `04_features_vs_distance.png` - How features change with distance
- `05_subcarrier_patterns.png` - Per-subcarrier CSI patterns
- `06_correlation_matrix.png` - Feature correlations

Plus `eda_summary.txt` with detailed statistics.

### 2. Trained Models (from `baseline_models.py`)

4 models trained and saved:
- `linear_model.pkl` - Simple linear regression baseline
- `ridge_model.pkl` - Ridge regression with regularization
- `random_forest_model.pkl` - Random Forest (best expected performance)
- `knn_model.pkl` - K-Nearest Neighbors

### 3. Evaluation Results

`baseline_comparison.txt` with:
- Model comparison table
- Detailed metrics for each model
- Training times
- Error percentiles (50th, 75th, 90th, 95th)

## 🎯 Expected Performance

Based on the Level 3 analysis document:

| Model | Expected MAE | Expected RMSE | Training Time |
|-------|--------------|---------------|---------------|
| Linear | 5-8 m | 6-10 m | < 1s |
| Ridge | 5-8 m | 6-10 m | < 1s |
| **Random Forest** | **3-5 m** | **4-6 m** | ~10s |
| KNN | 4-6 m | 5-7 m | < 1s |

**Random Forest** is expected to be the best baseline model!

## ⚙️ Customization

Edit `config.py` to customize:

```python
# Dataset path
DEFAULT_DATASET_PATH = "path/to/your/exp09/dataset"

# Normalization
NORMALIZATION = 'standard'  # or 'minmax', 'robust', None

# Feature selection
FEATURE_SELECTION = {
    'enabled': True,
    'method': 'mutual_info',  # or 'f_test', 'pca'
    'n_features': 100,
}

# Enable/disable models
BASELINE_MODELS['random_forest']['enabled'] = True
BASELINE_MODELS['xgboost']['enabled'] = False  # Requires xgboost installation
```

## 📈 Next Steps

1. **Run the pipeline** - Start with `python quickstart.py`
2. **Analyze results** - Check the plots and comparison report
3. **Tune models** - Modify parameters in `config.py`
4. **Try different features** - Use only wideband, only CSI, etc.
5. **Implement neural networks** - Create `models/neural_networks.py`
6. **Generate more data** - Run exp09 with larger n_trajectories
7. **Add NLOS scenarios** - Modify exp09 to include NLOS

## 🔬 Research Path

**Week 1: Baseline Models** ✅ (You are here!)
- Load data and run EDA
- Train simple models (Linear, RF, KNN)
- Establish baseline performance

**Week 2: Feature Engineering**
- Try different feature combinations
- Implement PCA dimensionality reduction
- Statistical features (mean, std, skewness of CSI)

**Week 3: Advanced Models**
- Implement Neural Networks (fully connected)
- Try CNN for spatial CSI patterns
- Experiment with LSTM for temporal tracking

**Week 4: Optimization**
- Hyperparameter tuning (GridSearch, RandomSearch)
- Ensemble methods
- Model compression for deployment

## 🎓 Integration with MATLAB

Your workflow is now:

```
QuaDRiGa (MATLAB) → .mat files → Python ML Pipeline → Results → Thesis
```

The Python pipeline automatically loads `.mat` files using `scipy.io.loadmat()`, so you can focus on ML while MATLAB handles channel simulations.

## 📝 Documentation Files

- **README.md** - Full documentation (features, usage, troubleshooting)
- **QUICKSTART.md** - Getting started in 5 minutes
- **This file** - Setup summary

## 🐛 Troubleshooting

**Dataset not found?**
```python
# Edit config.py, line ~20:
DEFAULT_DATASET_PATH = Path(r"D:\path\to\your\exp09\dataset")
```

**Missing packages?**
```powershell
pip install numpy scipy pandas matplotlib seaborn scikit-learn
```

**Want deep learning?**
```powershell
pip install torch torchvision  # Uncomment in requirements.txt
```

## 💡 Pro Tips

1. **Start small**: Run with default settings first to ensure everything works
2. **Check EDA**: Always look at the EDA plots before training models
3. **Save often**: Models and preprocessors are automatically saved
4. **Version control**: The `.gitignore` prevents committing large outputs
5. **Experiment**: Try different feature combinations using `data_loader.py`'s `feature_groups` parameter

## 🎉 You're Ready!

Everything is set up and ready to go. Start with:

```powershell
cd ml_training
python quickstart.py
```

And select option 5 to run the complete pipeline!

---

**Created:** November 5, 2025  
**Status:** Ready for ML experiments! 🚀  
**Questions?** Check README.md or QUICKSTART.md
