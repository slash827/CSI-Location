"""
Baseline models for CSI-based localization.

Includes: Linear Regression, Ridge, Random Forest, KNN, XGBoost
"""

import numpy as np
import time
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import pickle

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error
from sklearn.multioutput import MultiOutputRegressor

from data_loader import CSIDataLoader
from preprocessing import preprocess_dataset
from config import BASELINE_MODELS, RANDOM_SEED, MODELS_DIR, RESULTS_DIR, OUTPUT_DIR


class BaselineModel:
    """Wrapper for baseline models."""
    
    def __init__(self, model_type: str, model_params: dict = None):
        """
        Initialize model.
        
        Args:
            model_type: Type of model ('linear', 'ridge', 'random_forest', 'knn', 'xgboost')
            model_params: Model parameters (optional)
        """
        self.model_type = model_type
        self.model_params = model_params or {}
        self.model = None
        self.training_time = 0.0
        
        # Create model
        self._create_model()
    
    def _create_model(self):
        """Create sklearn model based on type."""
        if self.model_type == 'linear':
            self.model = LinearRegression(**self.model_params)
        
        elif self.model_type == 'ridge':
            self.model = Ridge(**self.model_params)
        
        elif self.model_type == 'random_forest':
            # Use MultiOutputRegressor for x,y prediction
            rf = RandomForestRegressor(**self.model_params)
            self.model = MultiOutputRegressor(rf)
        
        elif self.model_type == 'knn':
            self.model = KNeighborsRegressor(**self.model_params)
        
        elif self.model_type == 'xgboost':
            try:
                from xgboost import XGBRegressor
                xgb = XGBRegressor(**self.model_params)
                self.model = MultiOutputRegressor(xgb)
            except ImportError:
                raise ImportError("XGBoost not installed. Install with: pip install xgboost")
        
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray):
        """
        Train model.
        
        Args:
            X_train: Training features [N, D]
            y_train: Training targets [N, 2]
        """
        print(f"\nTraining {self.model_type}...")
        start_time = time.time()
        
        self.model.fit(X_train, y_train)
        
        self.training_time = time.time() - start_time
        print(f"  ✓ Training completed in {self.training_time:.2f}s")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions.
        
        Args:
            X: Features [N, D]
        
        Returns:
            Predictions [N, 2]
        """
        return self.model.predict(X)
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model.
        
        Args:
            X: Features [N, D]
            y: True targets [N, 2]
        
        Returns:
            Dictionary with metrics
        """
        y_pred = self.predict(X)
        
        # Calculate Euclidean distance errors
        position_errors = np.linalg.norm(y - y_pred, axis=1)
        
        # Calculate coordinate-wise errors separately
        x_errors = np.abs(y[:, 0] - y_pred[:, 0])
        y_errors = np.abs(y[:, 1] - y_pred[:, 1])
        
        # Calculate metrics
        metrics = {
            'mae': mean_absolute_error(y, y_pred),
            'rmse': np.sqrt(mean_squared_error(y, y_pred)),
            'r2': r2_score(y, y_pred),
            'max_error_x': x_errors.max(),
            'max_error_y': y_errors.max(),
            'median_ae': median_absolute_error(y, y_pred),
            'position_mae': position_errors.mean(),
            'position_rmse': np.sqrt((position_errors**2).mean()),
            'position_max': position_errors.max(),
            'position_median': np.median(position_errors),
            'position_50th': np.percentile(position_errors, 50),
            'position_75th': np.percentile(position_errors, 75),
            'position_90th': np.percentile(position_errors, 90),
            'position_95th': np.percentile(position_errors, 95),
            'training_time': self.training_time,
        }
        
        return metrics
    
    def save(self, filepath: Path):
        """Save model to file."""
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
        print(f"Model saved to: {filepath}")
    
    @staticmethod
    def load(filepath: Path) -> 'BaselineModel':
        """Load model from file."""
        with open(filepath, 'rb') as f:
            model = pickle.load(f)
        print(f"Model loaded from: {filepath}")
        return model


def train_all_baseline_models(X_train, y_train, X_val, y_val) -> Dict[str, BaselineModel]:
    """
    Train all enabled baseline models.
    
    Args:
        X_train: Training features
        y_train: Training targets
        X_val: Validation features
        y_val: Validation targets
    
    Returns:
        Dictionary of trained models
    """
    print("\n" + "=" * 70)
    print("TRAINING BASELINE MODELS")
    print("=" * 70)
    
    results = {}
    
    for model_name, config in BASELINE_MODELS.items():
        if not config['enabled']:
            print(f"\nSkipping {model_name} (disabled)")
            continue
        
        # Create and train model
        model = BaselineModel(model_name, config['params'])
        model.train(X_train, y_train)
        
        # Evaluate on training set
        train_metrics = model.evaluate(X_train, y_train)
        print(f"\n  Training Metrics:")
        print(f"    Position MAE: {train_metrics['position_mae']:.2f} m")
        print(f"    Position RMSE: {train_metrics['position_rmse']:.2f} m")
        print(f"    R² Score: {train_metrics['r2']:.4f}")
        
        # Evaluate on validation set
        if X_val is not None:
            val_metrics = model.evaluate(X_val, y_val)
            print(f"\n  Validation Metrics:")
            print(f"    Position MAE: {val_metrics['position_mae']:.2f} m")
            print(f"    Position RMSE: {val_metrics['position_rmse']:.2f} m")
            print(f"    R² Score: {val_metrics['r2']:.4f}")
            print(f"    50th/75th/90th/95th percentile: "
                  f"{val_metrics['position_50th']:.2f} / "
                  f"{val_metrics['position_75th']:.2f} / "
                  f"{val_metrics['position_90th']:.2f} / "
                  f"{val_metrics['position_95th']:.2f} m")
        
        # Save model
        model_file = MODELS_DIR / f"{model_name}_model.pkl"
        model.save(model_file)
        
        # Store results
        results[model_name] = {
            'model': model,
            'train_metrics': train_metrics,
            'val_metrics': val_metrics if X_val is not None else None
        }
    
    # Save comparison results
    save_comparison_results(results)
    
    print("\n" + "=" * 70)
    print("BASELINE TRAINING COMPLETE!")
    print("=" * 70 + "\n")
    
    return results


def save_comparison_results(results: Dict):
    """Save model comparison to file."""
    lines = []
    lines.append("=" * 80)
    lines.append("BASELINE MODELS COMPARISON")
    lines.append("=" * 80)
    lines.append("")
    
    # Header
    lines.append(f"{'Model':<20} {'Train MAE':<12} {'Val MAE':<12} {'Val RMSE':<12} "
                f"{'Val R²':<10} {'Time (s)':<10}")
    lines.append("-" * 80)
    
    # Results for each model
    for model_name, result in results.items():
        train_mae = result['train_metrics']['position_mae']
        val_mae = result['val_metrics']['position_mae'] if result['val_metrics'] else float('nan')
        val_rmse = result['val_metrics']['position_rmse'] if result['val_metrics'] else float('nan')
        val_r2 = result['val_metrics']['r2'] if result['val_metrics'] else float('nan')
        train_time = result['train_metrics']['training_time']
        
        lines.append(f"{model_name:<20} {train_mae:<12.2f} {val_mae:<12.2f} {val_rmse:<12.2f} "
                    f"{val_r2:<10.4f} {train_time:<10.2f}")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append("")
    
    # Detailed validation results
    lines.append("DETAILED VALIDATION METRICS")
    lines.append("=" * 80)
    
    for model_name, result in results.items():
        if result['val_metrics'] is None:
            continue
        
        lines.append(f"\n{model_name.upper()}:")
        lines.append("-" * 40)
        vm = result['val_metrics']
        lines.append(f"  Position MAE:  {vm['position_mae']:.2f} m")
        lines.append(f"  Position RMSE: {vm['position_rmse']:.2f} m")
        lines.append(f"  Position Max:  {vm['position_max']:.2f} m")
        lines.append(f"  R² Score:      {vm['r2']:.4f}")
        lines.append(f"  Error Percentiles:")
        lines.append(f"    50th: {vm['position_50th']:.2f} m")
        lines.append(f"    75th: {vm['position_75th']:.2f} m")
        lines.append(f"    90th: {vm['position_90th']:.2f} m")
        lines.append(f"    95th: {vm['position_95th']:.2f} m")
        lines.append(f"  Training time: {vm['training_time']:.2f} s")
    
    lines.append("")
    lines.append("=" * 80)
    
    # Save to file
    comparison_file = RESULTS_DIR / "baseline_comparison.txt"
    with open(comparison_file, 'w') as f:
        f.write("\n".join(lines))
    
    print(f"\nComparison results saved to: {comparison_file}")


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train baseline models')
    parser.add_argument('--dataset_path', type=str, default=None,
                       help='Path to dataset folder (default: from config)')
    parser.add_argument('--use_processed', action='store_true',
                       help='Use pre-processed data if available')
    parser.add_argument('--use_filtered', type=str, default=None,
                       help='Use filtered dataset by name (e.g., dataset_top50)')
    
    args = parser.parse_args()
    
    # Load or preprocess data
    if args.use_filtered:
        # Load filtered dataset from generate_and_filter_data.py
        filtered_dir = OUTPUT_DIR / "generated_data"
        train_file = filtered_dir / f"{args.use_filtered}_train.npz"
        val_file = filtered_dir / f"{args.use_filtered}_val.npz"
        
        if train_file.exists() and val_file.exists():
            print(f"\nLoading filtered dataset: {args.use_filtered}")
            print("=" * 70)
            
            train_data = np.load(train_file)
            X_train, y_train = train_data['X'], train_data['y']
            print(f"✓ Loaded training data: X={X_train.shape}, y={y_train.shape}")
            
            val_data = np.load(val_file)
            X_val, y_val = val_data['X'], val_data['y']
            print(f"✓ Loaded validation data: X={X_val.shape}, y={y_val.shape}")
            
            # Load metadata if available
            metadata_file = filtered_dir / f"{args.use_filtered}_metadata.pkl"
            if metadata_file.exists():
                with open(metadata_file, 'rb') as f:
                    metadata = pickle.load(f)
                print(f"\n📊 Dataset Info:")
                print(f"  Original features: {metadata['n_features_original']}")
                print(f"  Selected features: {metadata['n_features_selected']}")
                print(f"  Reduction: {100 * (1 - metadata['n_features_selected']/metadata['n_features_original']):.1f}%")
            print("=" * 70 + "\n")
        else:
            raise FileNotFoundError(
                f"Filtered dataset not found: {args.use_filtered}\n"
                f"Expected files:\n"
                f"  - {train_file}\n"
                f"  - {val_file}\n"
                f"Run: python generate_and_filter_data.py --output_name {args.use_filtered}"
            )
    
    elif args.use_processed:
        processed_dir = OUTPUT_DIR / "processed_data"
        if (processed_dir / "processed_train.npz").exists():
            print("Loading pre-processed data...")
            train_data = np.load(processed_dir / "processed_train.npz")
            X_train, y_train = train_data['X'], train_data['y']
            
            if (processed_dir / "processed_val.npz").exists():
                val_data = np.load(processed_dir / "processed_val.npz")
                X_val, y_val = val_data['X'], val_data['y']
            else:
                X_val, y_val = None, None
        else:
            print("Pre-processed data not found, running preprocessing...")
            X_train, y_train, X_val, y_val, _ = preprocess_dataset(args.dataset_path)
    else:
        # Preprocess data
        X_train, y_train, X_val, y_val, _ = preprocess_dataset(args.dataset_path)
    
    # Train models
    results = train_all_baseline_models(X_train, y_train, X_val, y_val)
    
    # Print best model
    if results:
        best_model = min(results.items(), 
                        key=lambda x: x[1]['val_metrics']['position_mae'] 
                        if x[1]['val_metrics'] else float('inf'))
        print(f"\n🏆 Best Model: {best_model[0]}")
        print(f"   Validation MAE: {best_model[1]['val_metrics']['position_mae']:.2f} m")


if __name__ == "__main__":
    main()
