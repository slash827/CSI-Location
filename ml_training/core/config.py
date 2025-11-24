"""
Configuration file for ML training pipeline.

Contains all paths, parameters, and settings.
"""

from pathlib import Path

# ============================================================================
# PATHS
# ============================================================================

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Default dataset path (exp11 NLOS-enhanced results)
DEFAULT_DATASET_PATH = PROJECT_ROOT / "results" / "exp11_2025-11-15_14-07-52" / "dataset"
# OLD: DEFAULT_DATASET_PATH = PROJECT_ROOT / "results" / "exp10_2025-11-07_12-40-00" / "dataset"

# Output directories
OUTPUT_DIR = Path(__file__).parent / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
MODELS_DIR = OUTPUT_DIR / "saved_models"
RESULTS_DIR = OUTPUT_DIR / "results"

# Create output directories if they don't exist
for dir_path in [OUTPUT_DIR, PLOTS_DIR, MODELS_DIR, RESULTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DATASET PARAMETERS
# ============================================================================

# Feature groups (771 total features from exp09, 3,072+ from exp10 with 4 BSs)
FEATURE_GROUPS = {
    'wideband': ['CQI_wb', 'RSRP', 'SINR_wb'],  # 3 features (changed RSS_wb to RSRP for exp10)
    'rss_per_sc': 'RSS_per_sc',                 # 256 features (exp09) or 1024 (exp10 with 4 BSs)
    'sinr_per_sc': 'SINR_per_sc',               # 256 features (exp09) or 1024 (exp10 with 4 BSs)
    'h_mag_per_sc': 'H_mag_per_sc',             # 256 features (exp09) or 1024 (exp10 with 4 BSs)
}

# Target variables
TARGETS = ['positions_x', 'positions_y']

# Metadata fields
METADATA_FIELDS = ['trajectory_id', 'snapshot_id', 'distances']

# ============================================================================
# PREPROCESSING PARAMETERS
# ============================================================================

# Normalization strategy
NORMALIZATION = 'standard'  # Options: 'standard', 'minmax', 'robust', None
# Back to standard scaler

# Feature selection
FEATURE_SELECTION = {
    'enabled': False,
    'method': 'mutual_info',  # Options: 'mutual_info', 'f_test', 'pca'
    'n_features': 100,  # Number of features to select
}

# PCA parameters
PCA_CONFIG = {
    'enabled': False,
    'n_components': 50,  # Or variance_threshold: 0.95
}

# Outlier detection
OUTLIER_DETECTION = {
    'enabled': False,  # Disabled for now - too aggressive
    'method': 'iqr',  # Options: 'iqr', 'zscore', 'isolation_forest'
    'threshold': 3.0,  # For zscore or IQR multiplier
}

# ============================================================================
# MODEL PARAMETERS
# ============================================================================

# Random seed for reproducibility
RANDOM_SEED = 42

# Train/val split (if not already split)
VAL_SPLIT = 0.2

# Baseline models configuration
BASELINE_MODELS = {
    'linear': {
        'enabled': True,
        'params': {}
    },
    'ridge': {
        'enabled': True,
        'params': {'alpha': 1.0}
    },
    'random_forest': {
        'enabled': True,
        'params': {
            'n_estimators': 50,        # Reduced from 100
            'max_depth': 15,           # Reduced from 20
            'min_samples_split': 10,   # Increased from 5 (faster)
            'min_samples_leaf': 4,     # Added to speed up
            'max_features': 'sqrt',    # Use sqrt(features) instead of all
            'n_jobs': -1,
            'random_state': RANDOM_SEED,
            'verbose': 1               # Show progress
        }
    },
    'knn': {
        'enabled': True,
        'params': {
            'n_neighbors': 5,
            'weights': 'distance'
        }
    },
    'xgboost': {
        'enabled': False,  # Optional, requires xgboost
        'params': {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': RANDOM_SEED
        }
    }
}

# Neural network configuration
NN_CONFIG = {
    'architecture': [256, 128, 64],  # Hidden layer sizes
    'activation': 'relu',
    'dropout': 0.2,
    'batch_size': 32,
    'epochs': 100,
    'learning_rate': 0.001,
    'early_stopping': True,
    'patience': 10,
}

# ============================================================================
# EVALUATION PARAMETERS
# ============================================================================

# Metrics to compute
METRICS = ['mae', 'rmse', 'r2', 'max_error', 'median_ae']

# Distance bins for error analysis (meters)
DISTANCE_BINS = [20, 30, 40, 50, 60, 70]

# Percentiles for error analysis
ERROR_PERCENTILES = [50, 75, 90, 95, 99]

# ============================================================================
# VISUALIZATION PARAMETERS
# ============================================================================

# Plot style
PLOT_STYLE = 'seaborn-v0_8-darkgrid'
FIGURE_SIZE = (12, 8)
DPI = 150

# Color schemes
COLOR_TRAIN = '#1f77b4'
COLOR_VAL = '#ff7f0e'
COLOR_PRED = '#2ca02c'
COLOR_ERROR = '#d62728'

# ============================================================================
# LOGGING
# ============================================================================

# Logging level
LOG_LEVEL = 'INFO'  # Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR'

# Log file
LOG_FILE = OUTPUT_DIR / 'training.log'

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_dataset_path(experiment_name=None):
    """
    Get dataset path for a specific experiment.
    
    Args:
        experiment_name: Name of experiment folder (e.g., 'exp09_2025-11-04_21-41-43')
                        If None, uses DEFAULT_DATASET_PATH
    
    Returns:
        Path object to dataset folder
    """
    if experiment_name is None:
        return DEFAULT_DATASET_PATH
    
    return PROJECT_ROOT / "results" / experiment_name / "dataset"


def print_config():
    """Print current configuration."""
    print("=" * 70)
    print("ML TRAINING CONFIGURATION")
    print("=" * 70)
    print(f"\nDataset Path: {DEFAULT_DATASET_PATH}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"\nNormalization: {NORMALIZATION}")
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"\nEnabled Models:")
    for model_name, config in BASELINE_MODELS.items():
        if config['enabled']:
            print(f"  - {model_name}")
    print("=" * 70)


if __name__ == "__main__":
    print_config()
