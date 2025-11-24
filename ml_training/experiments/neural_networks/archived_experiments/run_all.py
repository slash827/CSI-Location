"""
Run all neural network experiments sequentially.

Trains MLP, CNN, and ResNet and compares results.
"""

import subprocess
import sys
from pathlib import Path
import json
import time

# Models to train
MODELS = ['mlp', 'cnn', 'resnet']

# Training configuration
CONFIG = {
    'mlp': {
        'epochs': 100,
        'batch_size': 256,
        'lr': 0.001,
    },
    'cnn': {
        'epochs': 100,
        'batch_size': 256,
        'lr': 0.0005,
    },
    'resnet': {
        'epochs': 100,
        'batch_size': 128,
        'lr': 0.0005,
    }
}


def train_model(model_type):
    """Train a single model."""
    print(f"\n{'='*70}")
    print(f"TRAINING {model_type.upper()}")
    print(f"{'='*70}\n")
    
    config = CONFIG[model_type]
    
    cmd = [
        sys.executable,
        'experiments/neural_networks/train.py',
        '--model', model_type,
        '--epochs', str(config['epochs']),
        '--batch_size', str(config['batch_size']),
        '--lr', str(config['lr']),
    ]
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, check=True)
        elapsed = time.time() - start_time
        
        print(f"\n✓ {model_type.upper()} training completed in {elapsed/60:.1f} minutes")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {model_type.upper()} training failed: {e}")
        return False


def compare_results(output_dir):
    """Compare results from all trained models."""
    print(f"\n{'='*70}")
    print("COMPARING ALL MODELS")
    print(f"{'='*70}\n")
    
    results = {}
    
    # Find result files
    results_dir = Path(output_dir) / 'results'
    
    for model_type in MODELS:
        # Find most recent result for this model
        model_results = list(results_dir.glob(f'neural_net_{model_type}_*/results.json'))
        
        if not model_results:
            print(f"⚠️  No results found for {model_type}")
            continue
        
        # Get most recent
        latest_result = max(model_results, key=lambda p: p.stat().st_mtime)
        
        with open(latest_result, 'r') as f:
            data = json.load(f)
            results[model_type] = data['final_metrics']
    
    if not results:
        print("No results to compare!")
        return
    
    # Print comparison table
    print(f"{'Model':<15} {'Val MAE':<12} {'Val RMSE':<12} {'Val R²':<10}")
    print("-" * 70)
    
    for model_type in MODELS:
        if model_type in results:
            metrics = results[model_type]
            print(f"{model_type.upper():<15} "
                  f"{metrics['position_mae']:<12.2f} "
                  f"{metrics['position_rmse']:<12.2f} "
                  f"{metrics['r2']:<10.4f}")
    
    print("-" * 70)
    
    # Find best model
    best_model = min(results.items(), key=lambda x: x[1]['position_mae'])
    print(f"\n🏆 BEST MODEL: {best_model[0].upper()}")
    print(f"   Validation MAE: {best_model[1]['position_mae']:.2f} m")
    print(f"   Validation R²: {best_model[1]['r2']:.4f}")
    
    # Compare with baseline
    print(f"\n📊 COMPARISON WITH BASELINE:")
    print(f"   Random Forest: 20.10 m MAE")
    print(f"   {best_model[0].upper()}: {best_model[1]['position_mae']:.2f} m MAE")
    improvement = (20.10 - best_model[1]['position_mae']) / 20.10 * 100
    if improvement > 0:
        print(f"   Improvement: {improvement:.1f}% better ✅")
    else:
        print(f"   Change: {abs(improvement):.1f}% worse ❌")


def main():
    """Main function."""
    print("="*70)
    print("NEURAL NETWORK EXPERIMENTS - ALL MODELS")
    print("="*70)
    print(f"\nWill train: {', '.join([m.upper() for m in MODELS])}")
    print("\nEstimated time:")
    print("  MLP: ~10-15 minutes")
    print("  CNN: ~15-20 minutes")
    print("  ResNet: ~20-30 minutes")
    print("  Total: ~45-65 minutes")
    print()
    
    input("Press Enter to start training (or Ctrl+C to cancel)...")
    
    # Change to ml_training directory
    import os
    os.chdir(Path(__file__).parent.parent.parent)
    
    # Train all models
    successful = []
    for model_type in MODELS:
        if train_model(model_type):
            successful.append(model_type)
    
    # Compare results
    if successful:
        print(f"\n✓ Successfully trained: {', '.join([m.upper() for m in successful])}")
        compare_results('output')
    else:
        print("\n❌ No models trained successfully")
    
    print(f"\n{'='*70}")
    print("ALL EXPERIMENTS COMPLETE!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
