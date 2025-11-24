"""
Optimized models experiment with smart hyperparameter choices.

Tests:
1. Random Forest with tuned hyperparameters
2. XGBoost (gradient boosting)
3. Keeps all 3,075 features (no feature selection)

Uses educated guesses instead of grid search for speed.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import time
from datetime import datetime
import json
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# XGBoost
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("⚠️  XGBoost not installed. Install with: pip install xgboost")

from config import (
    DEFAULT_DATASET_PATH, RANDOM_SEED,
    MODELS_DIR, OUTPUT_DIR
)
from data_loader import CSIDataLoader
from preprocessing import preprocess_dataset


def create_experiment_dir(experiment_name='optimized'):
    """Create timestamped experiment directory."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    exp_dir = Path(MODELS_DIR).parent / 'results' / f"{experiment_name}_{timestamp}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / 'models').mkdir(exist_ok=True)
    return exp_dir, timestamp


def save_experiment_config(exp_dir, config):
    """Save experiment configuration."""
    config_path = exp_dir / 'config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✓ Config saved: {config_path}")


def compute_metrics(y_true, y_pred):
    """Compute position-based metrics."""
    # Position errors (Euclidean distance)
    position_errors = np.sqrt(np.sum((y_true - y_pred)**2, axis=1))
    
    metrics = {
        'position_mae': np.mean(position_errors),
        'position_rmse': np.sqrt(np.mean(position_errors**2)),
        'x_mae': mean_absolute_error(y_true[:, 0], y_pred[:, 0]),
        'y_mae': mean_absolute_error(y_true[:, 1], y_pred[:, 1]),
        'r2': r2_score(y_true, y_pred),
    }
    return metrics


def train_random_forest_optimized(X_train, y_train, X_val, y_val, version='v1'):
    """
    Train Random Forest with optimized hyperparameters.
    
    Versions:
    - v1 (baseline): Current config (n_estimators=50, max_depth=15)
    - v2 (deeper): More trees, deeper (n_estimators=100, max_depth=25)
    - v3 (balanced): Balanced approach (n_estimators=75, max_depth=20)
    """
    print(f"\n{'='*70}")
    print(f"Training RANDOM_FOREST_{version.upper()}")
    print(f"{'='*70}\n")
    
    # Hyperparameter configurations
    configs = {
        'v1': {
            'n_estimators': 50,
            'max_depth': 15,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt',
            'description': 'Current baseline config'
        },
        'v2': {
            'n_estimators': 100,
            'max_depth': 25,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt',
            'description': 'More trees, deeper (better accuracy, slower)'
        },
        'v3': {
            'n_estimators': 75,
            'max_depth': 20,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt',
            'description': 'Balanced approach'
        },
        'v4': {
            'n_estimators': 100,
            'max_depth': 30,
            'min_samples_split': 3,
            'min_samples_leaf': 1,
            'max_features': 'sqrt',
            'description': 'Max capacity (may overfit)'
        },
    }
    
    config = configs[version]
    print(f"Config: {config['description']}")
    print(f"  n_estimators: {config['n_estimators']}")
    print(f"  max_depth: {config['max_depth']}")
    print(f"  max_features: {config['max_features']}")
    
    # Train
    model = RandomForestRegressor(
        n_estimators=config['n_estimators'],
        max_depth=config['max_depth'],
        min_samples_split=config['min_samples_split'],
        min_samples_leaf=config['min_samples_leaf'],
        max_features=config['max_features'],
        random_state=RANDOM_SEED,
        n_jobs=-1,
        verbose=1
    )
    
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time
    print(f"  ✓ Training completed in {train_time:.2f}s")
    
    # Evaluate
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)
    
    train_metrics = compute_metrics(y_train, train_pred)
    val_metrics = compute_metrics(y_val, val_pred)
    
    print(f"\n  Training Metrics:")
    print(f"    Position MAE: {train_metrics['position_mae']:.2f} m")
    print(f"    Position RMSE: {train_metrics['position_rmse']:.2f} m")
    print(f"    R² Score: {train_metrics['r2']:.4f}")
    
    print(f"\n  Validation Metrics:")
    print(f"    Position MAE: {val_metrics['position_mae']:.2f} m")
    print(f"    Position RMSE: {val_metrics['position_rmse']:.2f} m")
    print(f"    R² Score: {val_metrics['r2']:.4f}")
    print(f"    Overfitting gap: {val_metrics['position_mae'] - train_metrics['position_mae']:.2f} m")
    
    return model, train_metrics, val_metrics, train_time, config


def train_xgboost(X_train, y_train, X_val, y_val, version='v1'):
    """
    Train XGBoost with optimized hyperparameters.
    
    Versions:
    - v1 (conservative): Safe defaults
    - v2 (aggressive): More trees, deeper
    """
    if not HAS_XGBOOST:
        print("❌ XGBoost not available, skipping...")
        return None, None, None, None, None
    
    print(f"\n{'='*70}")
    print(f"Training XGBOOST_{version.upper()}")
    print(f"{'='*70}\n")
    
    # Hyperparameter configurations
    configs = {
        'v1': {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'min_child_weight': 3,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'description': 'Conservative defaults (fast, stable)'
        },
        'v2': {
            'n_estimators': 200,
            'max_depth': 8,
            'learning_rate': 0.05,
            'min_child_weight': 1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'description': 'More iterations, deeper (better accuracy)'
        },
        'v3': {
            'n_estimators': 150,
            'max_depth': 7,
            'learning_rate': 0.075,
            'min_child_weight': 2,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'description': 'Balanced approach'
        },
    }
    
    config = configs[version]
    print(f"Config: {config['description']}")
    print(f"  n_estimators: {config['n_estimators']}")
    print(f"  max_depth: {config['max_depth']}")
    print(f"  learning_rate: {config['learning_rate']}")
    
    # Train separate models for X and Y coordinates
    models = []
    train_preds = []
    val_preds = []
    total_time = 0
    
    for coord_idx, coord_name in enumerate(['X', 'Y']):
        print(f"\n  Training {coord_name} coordinate model...")
        
        model = xgb.XGBRegressor(
            n_estimators=config['n_estimators'],
            max_depth=config['max_depth'],
            learning_rate=config['learning_rate'],
            min_child_weight=config['min_child_weight'],
            subsample=config['subsample'],
            colsample_bytree=config['colsample_bytree'],
            random_state=RANDOM_SEED,
            n_jobs=-1,
            verbosity=1
        )
        
        start_time = time.time()
        model.fit(
            X_train, y_train[:, coord_idx],
            eval_set=[(X_val, y_val[:, coord_idx])],
            verbose=False
        )
        total_time += time.time() - start_time
        
        models.append(model)
        train_preds.append(model.predict(X_train))
        val_preds.append(model.predict(X_val))
    
    print(f"\n  ✓ Training completed in {total_time:.2f}s")
    
    # Combine predictions
    train_pred = np.column_stack(train_preds)
    val_pred = np.column_stack(val_preds)
    
    # Evaluate
    train_metrics = compute_metrics(y_train, train_pred)
    val_metrics = compute_metrics(y_val, val_pred)
    
    print(f"\n  Training Metrics:")
    print(f"    Position MAE: {train_metrics['position_mae']:.2f} m")
    print(f"    Position RMSE: {train_metrics['position_rmse']:.2f} m")
    print(f"    R² Score: {train_metrics['r2']:.4f}")
    
    print(f"\n  Validation Metrics:")
    print(f"    Position MAE: {val_metrics['position_mae']:.2f} m")
    print(f"    Position RMSE: {val_metrics['position_rmse']:.2f} m")
    print(f"    R² Score: {val_metrics['r2']:.4f}")
    print(f"    Overfitting gap: {val_metrics['position_mae'] - train_metrics['position_mae']:.2f} m")
    
    return models, train_metrics, val_metrics, total_time, config


def save_comparison_results(exp_dir, results):
    """Save model comparison to text file."""
    output_path = exp_dir / 'model_comparison.txt'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("OPTIMIZED MODELS COMPARISON\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Dataset: exp10 (3,075 features, no feature selection)\n")
        f.write(f"Training samples: 32,000\n")
        f.write(f"Validation samples: 8,000\n\n")
        
        # Table header
        f.write("-"*70 + "\n")
        f.write(f"{'Model':<25} {'Val MAE':<12} {'Val R²':<10} {'Time (s)':<10}\n")
        f.write("-"*70 + "\n")
        
        # Sort by validation MAE
        sorted_results = sorted(results.items(), key=lambda x: x[1]['val_metrics']['position_mae'])
        
        for model_name, result in sorted_results:
            mae = result['val_metrics']['position_mae']
            r2 = result['val_metrics']['r2']
            time_s = result['train_time']
            f.write(f"{model_name:<25} {mae:<12.2f} {r2:<10.4f} {time_s:<10.2f}\n")
        
        f.write("-"*70 + "\n\n")
        
        # Best model
        best_model = sorted_results[0]
        f.write(f"\n🏆 BEST MODEL: {best_model[0]}\n")
        f.write(f"   Validation MAE: {best_model[1]['val_metrics']['position_mae']:.2f} m\n")
        f.write(f"   Validation R²: {best_model[1]['val_metrics']['r2']:.4f}\n")
        f.write(f"   Training time: {best_model[1]['train_time']:.2f}s\n\n")
        
        # Detailed results
        f.write("\n" + "="*70 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("="*70 + "\n\n")
        
        for model_name, result in sorted_results:
            f.write(f"\n{model_name}\n")
            f.write("-"*70 + "\n")
            if 'config' in result:
                f.write(f"Configuration: {result['config']['description']}\n")
                for key, value in result['config'].items():
                    if key != 'description':
                        f.write(f"  {key}: {value}\n")
            
            f.write(f"\nTraining Metrics:\n")
            for key, value in result['train_metrics'].items():
                f.write(f"  {key}: {value:.4f}\n")
            
            f.write(f"\nValidation Metrics:\n")
            for key, value in result['val_metrics'].items():
                f.write(f"  {key}: {value:.4f}\n")
            
            f.write(f"\nTraining time: {result['train_time']:.2f}s\n")
            f.write(f"Overfitting gap: {result['val_metrics']['position_mae'] - result['train_metrics']['position_mae']:.2f} m\n")
    
    print(f"✓ Comparison saved: {output_path}")


def main():
    """Run optimized models experiment."""
    print("="*70)
    print("OPTIMIZED MODELS EXPERIMENT")
    print("="*70)
    print()
    print("Testing:")
    print("  - Random Forest (3 configurations)")
    print("  - XGBoost (2 configurations)")
    print("  - Using all 3,075 features (no feature selection)")
    print()
    
    # Create experiment directory
    exp_dir, timestamp = create_experiment_dir('optimized')
    print(f"📁 Results directory: {exp_dir}\n")
    
    # Load data
    print("="*70)
    print("LOADING AND PREPROCESSING DATA")
    print("="*70)
    print()
    
    # Preprocess dataset (loads and normalizes)
    X_train, y_train, X_val, y_val, preprocessor = preprocess_dataset(DEFAULT_DATASET_PATH)
    
    print(f"\n✓ Data loaded and preprocessed:")
    print(f"  Training: X={X_train.shape}, y={y_train.shape}")
    print(f"  Validation: X={X_val.shape}, y={y_val.shape}")
    print(f"  Using all {X_train.shape[1]} features (no feature selection)")
    
    # Save config
    exp_config = {
        'timestamp': timestamp,
        'dataset': str(DEFAULT_DATASET_PATH),
        'n_features': X_train.shape[1],
        'feature_selection': 'none',
        'train_samples': X_train.shape[0],
        'val_samples': X_val.shape[0],
        'random_seed': RANDOM_SEED,
    }
    save_experiment_config(exp_dir, exp_config)
    
    # Train models
    print(f"\n{'='*70}")
    print("TRAINING MODELS")
    print("="*70)
    
    results = {}
    
    # Random Forest versions
    rf_versions = ['v1', 'v2', 'v3', 'v4']
    for version in rf_versions:
        try:
            model, train_metrics, val_metrics, train_time, config = train_random_forest_optimized(
                X_train, y_train, X_val, y_val, version=version
            )
            
            # Save model
            model_path = exp_dir / 'models' / f'random_forest_{version}_model.pkl'
            joblib.dump(model, model_path)
            print(f"Model saved to: {model_path}")
            
            results[f'random_forest_{version}'] = {
                'model': model,
                'train_metrics': train_metrics,
                'val_metrics': val_metrics,
                'train_time': train_time,
                'config': config
            }
        except Exception as e:
            print(f"❌ Error training Random Forest {version}: {e}")
    
    # XGBoost versions
    if HAS_XGBOOST:
        xgb_versions = ['v1', 'v2', 'v3']
        for version in xgb_versions:
            try:
                models, train_metrics, val_metrics, train_time, config = train_xgboost(
                    X_train, y_train, X_val, y_val, version=version
                )
                
                if models is not None:
                    # Save models (X and Y)
                    for idx, coord in enumerate(['x', 'y']):
                        model_path = exp_dir / 'models' / f'xgboost_{version}_{coord}_model.pkl'
                        joblib.dump(models[idx], model_path)
                    print(f"Models saved to: {exp_dir / 'models' / f'xgboost_{version}_*.pkl'}")
                    
                    results[f'xgboost_{version}'] = {
                        'model': models,
                        'train_metrics': train_metrics,
                        'val_metrics': val_metrics,
                        'train_time': train_time,
                        'config': config
                    }
            except Exception as e:
                print(f"❌ Error training XGBoost {version}: {e}")
    
    # Save comparison
    save_comparison_results(exp_dir, results)
    
    # Print summary
    print(f"\n{'='*70}")
    print("EXPERIMENT COMPLETE!")
    print("="*70)
    
    # Find best model
    best_model = min(results.items(), key=lambda x: x[1]['val_metrics']['position_mae'])
    print(f"\n🏆 Best Model: {best_model[0]}")
    print(f"   Validation MAE: {best_model[1]['val_metrics']['position_mae']:.2f} m")
    print(f"   Validation R²: {best_model[1]['val_metrics']['r2']:.4f}")
    
    print(f"\n📁 All results saved to: {exp_dir}")
    print(f"\nTo compare with baseline, check: ml_training/results/")


if __name__ == "__main__":
    main()
