"""
Baseline models experiment runner with timestamped results.

Usage:
    python experiments/run_baseline.py --n_features 500
    python experiments/run_baseline.py --no_feature_selection
"""

import numpy as np
import time
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import CSIDataLoader
from preprocessing import preprocess_dataset
from data.feature_selector import quick_feature_selection
from models.baseline_models import train_all_baseline_models
from config import BASELINE_MODELS, RANDOM_SEED


def create_experiment_dir(experiment_name='baseline'):
    """Create timestamped experiment directory."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    exp_dir = Path(__file__).parent.parent / 'results' / f"{experiment_name}_{timestamp}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (exp_dir / 'models').mkdir(exist_ok=True)
    (exp_dir / 'plots').mkdir(exist_ok=True)
    
    return exp_dir, timestamp


def save_experiment_config(exp_dir, config_dict):
    """Save experiment configuration."""
    config_file = exp_dir / 'config.json'
    with open(config_file, 'w') as f:
        json.dump(config_dict, f, indent=2, default=str)
    print(f"\n✓ Config saved: {config_file}")


def save_comparison_results(exp_dir, results):
    """Save model comparison to timestamped file."""
    lines = []
    lines.append("=" * 80)
    lines.append("BASELINE MODELS COMPARISON")
    lines.append("=" * 80)
    lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    comparison_file = exp_dir / "model_comparison.txt"
    with open(comparison_file, 'w') as f:
        f.write("\n".join(lines))
    
    print(f"\n✓ Comparison saved: {comparison_file}")


def main():
    """Main experiment runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run baseline models experiment')
    parser.add_argument('--dataset_path', type=str, default=None,
                       help='Path to dataset folder (default: from config)')
    parser.add_argument('--n_features', type=int, default=500,
                       help='Number of features to select (default: 500)')
    parser.add_argument('--selection_method', type=str, default='mutual_info',
                       choices=['mutual_info', 'f_test', 'pca', 'variance'],
                       help='Feature selection method (default: mutual_info)')
    parser.add_argument('--no_feature_selection', action='store_true',
                       help='Skip feature selection (use all 3,075 features)')
    parser.add_argument('--experiment_name', type=str, default='baseline',
                       help='Experiment name (default: baseline)')
    
    args = parser.parse_args()
    
    # Create experiment directory
    exp_dir, timestamp = create_experiment_dir(args.experiment_name)
    
    print("\n" + "=" * 70)
    print(f"BASELINE MODELS EXPERIMENT: {timestamp}")
    print("=" * 70)
    print(f"\n📁 Results directory: {exp_dir}")
    
    # Load and preprocess data
    print("\n" + "=" * 70)
    print("LOADING AND PREPROCESSING DATA")
    print("=" * 70)
    
    X_train, y_train, X_val, y_val, scaler = preprocess_dataset(args.dataset_path)
    
    print(f"\n✓ Data loaded:")
    print(f"  Training: X={X_train.shape}, y={y_train.shape}")
    print(f"  Validation: X={X_val.shape}, y={y_val.shape}")
    
    # Feature selection
    selector = None
    if not args.no_feature_selection:
        print("\n" + "=" * 70)
        print("FEATURE SELECTION")
        print("=" * 70)
        
        X_train, X_val, selector = quick_feature_selection(
            X_train, y_train, X_val, y_val,
            n_features=args.n_features,
            method=args.selection_method
        )
        
        # Save selector
        selector.save(exp_dir / 'feature_selector.pkl')
    else:
        print("\n⚠️  Skipping feature selection (using all features)")
    
    # Save experiment config
    config_dict = {
        'timestamp': timestamp,
        'experiment_name': args.experiment_name,
        'dataset_path': str(args.dataset_path) if args.dataset_path else 'default',
        'n_samples_train': int(X_train.shape[0]),
        'n_samples_val': int(X_val.shape[0]),
        'n_features_original': 3075,
        'n_features_selected': int(X_train.shape[1]),
        'feature_selection': {
            'enabled': not args.no_feature_selection,
            'method': args.selection_method if not args.no_feature_selection else None,
            'n_features': args.n_features if not args.no_feature_selection else None,
        },
        'models': {name: config for name, config in BASELINE_MODELS.items() if config['enabled']},
        'random_seed': RANDOM_SEED,
    }
    save_experiment_config(exp_dir, config_dict)
    
    # Train models
    print("\n" + "=" * 70)
    print("TRAINING MODELS")
    print("=" * 70)
    
    results = {}
    
    for model_name, config in BASELINE_MODELS.items():
        if not config['enabled']:
            continue
        
        print(f"\n{'='*70}")
        print(f"Training {model_name.upper()}")
        print(f"{'='*70}")
        
        from models.baseline_models import BaselineModel
        
        # Create and train model
        model = BaselineModel(model_name, config['params'])
        model.train(X_train, y_train)
        
        # Evaluate
        train_metrics = model.evaluate(X_train, y_train)
        val_metrics = model.evaluate(X_val, y_val)
        
        print(f"\n  Training Metrics:")
        print(f"    Position MAE: {train_metrics['position_mae']:.2f} m")
        print(f"    Position RMSE: {train_metrics['position_rmse']:.2f} m")
        print(f"    R² Score: {train_metrics['r2']:.4f}")
        
        print(f"\n  Validation Metrics:")
        print(f"    Position MAE: {val_metrics['position_mae']:.2f} m")
        print(f"    Position RMSE: {val_metrics['position_rmse']:.2f} m")
        print(f"    R² Score: {val_metrics['r2']:.4f}")
        print(f"    Overfitting gap: {val_metrics['position_mae'] - train_metrics['position_mae']:.2f} m")
        
        # Save model
        model_file = exp_dir / 'models' / f"{model_name}_model.pkl"
        model.save(model_file)
        
        # Store results
        results[model_name] = {
            'model': model,
            'train_metrics': train_metrics,
            'val_metrics': val_metrics
        }
    
    # Save comparison
    save_comparison_results(exp_dir, results)
    
    # Print summary
    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE!")
    print("=" * 70)
    
    # Find best model
    best_model = min(results.items(), key=lambda x: x[1]['val_metrics']['position_mae'])
    print(f"\n🏆 Best Model: {best_model[0]}")
    print(f"   Validation MAE: {best_model[1]['val_metrics']['position_mae']:.2f} m")
    print(f"   Validation R²: {best_model[1]['val_metrics']['r2']:.4f}")
    
    print(f"\n📁 All results saved to: {exp_dir}")
    print(f"\nTo compare with previous runs, check: ml_training/results/")


if __name__ == "__main__":
    main()
