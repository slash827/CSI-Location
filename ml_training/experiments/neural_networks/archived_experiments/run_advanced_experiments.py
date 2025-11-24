"""
Run multiple advanced training experiments and compare results.

This script tests different optimization strategies to push beyond R²=0.8.
"""

import sys
from pathlib import Path
import subprocess
import json
import pandas as pd
from datetime import datetime

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import OUTPUT_DIR


def run_experiment(config_name, device='auto'):
    """Run a single experiment."""
    print("\n" + "=" * 70)
    print(f"RUNNING EXPERIMENT: {config_name}")
    print("=" * 70 + "\n")
    
    cmd = [
        sys.executable,
        'experiments/neural_networks/train_advanced.py',
        '--config', config_name,
        '--device', device
    ]
    
    try:
        result = subprocess.run(cmd, check=True, cwd=Path(__file__).parent.parent.parent)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {config_name}: {e}")
        return False


def collect_results():
    """Collect results from all experiments."""
    results_dir = OUTPUT_DIR / 'results'
    all_results = []
    
    for result_folder in sorted(results_dir.glob('neural_net_advanced_*')):
        results_file = result_folder / 'results.json'
        if results_file.exists():
            with open(results_file, 'r') as f:
                data = json.load(f)
                
                all_results.append({
                    'config': data['config'],
                    'model': data['model_type'],
                    'scheduler': data['training_config']['scheduler'],
                    'epochs': data['training_config']['epochs'],
                    'lr': data['training_config']['lr'],
                    'batch_size': data['training_config']['batch_size'],
                    'weight_decay': data['training_config']['weight_decay'],
                    'final_mae': data['final_metrics']['val_mae'],
                    'final_r2': data['final_metrics']['val_r2'],
                    'best_r2': data['best_metrics']['best_r2'],
                    'best_mae': data['best_metrics']['best_mae'],
                    'timestamp': result_folder.name.split('_')[-2] + '_' + result_folder.name.split('_')[-1],
                })
    
    return pd.DataFrame(all_results)


def print_comparison(df):
    """Print comparison table."""
    print("\n" + "=" * 100)
    print("EXPERIMENT RESULTS COMPARISON")
    print("=" * 100 + "\n")
    
    # Sort by final R²
    df_sorted = df.sort_values('final_r2', ascending=False)
    
    print(f"{'Config':<30} {'Model':<8} {'Scheduler':<20} {'Final R²':<12} {'Final MAE':<12} {'Best R²':<12}")
    print("-" * 100)
    
    for _, row in df_sorted.iterrows():
        config = row['config'][:29]
        print(f"{config:<30} {row['model']:<8} {row['scheduler']:<20} "
              f"{row['final_r2']:.4f}       {row['final_mae']:.2f} m       {row['best_r2']:.4f}")
    
    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)
    print(f"Best R²: {df_sorted.iloc[0]['final_r2']:.4f} ({df_sorted.iloc[0]['config']})")
    print(f"Best MAE: {df['final_mae'].min():.2f} m ({df.loc[df['final_mae'].idxmin(), 'config']})")
    print(f"Average R²: {df['final_r2'].mean():.4f} (±{df['final_r2'].std():.4f})")
    print(f"Average MAE: {df['final_mae'].mean():.2f} m (±{df['final_mae'].std():.2f})")
    print("=" * 100 + "\n")


def save_comparison(df, filename='advanced_experiments_comparison.csv'):
    """Save comparison to CSV."""
    output_path = OUTPUT_DIR / filename
    df.to_csv(output_path, index=False)
    print(f"Comparison saved to: {output_path}")


def main():
    """Run all experiments and compare."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run advanced neural network experiments')
    parser.add_argument('--configs', nargs='+', default=None,
                       help='Specific configs to run (default: all)')
    parser.add_argument('--device', type=str, default='auto',
                       choices=['auto', 'cuda', 'cpu'],
                       help='Compute device')
    parser.add_argument('--compare-only', action='store_true',
                       help='Only compare existing results')
    
    args = parser.parse_args()
    
    # Available configurations (ordered by priority)
    all_configs = [
        'resnet_cosine_100',        # Extended training with cosine
        'resnet_onecycle',          # Fast convergence
        'resnet_warmup_cosine',     # Warmup + cosine
        'resnet_cosine_restarts',   # Cosine with restarts
        'mlp_aggressive',           # High-capacity MLP
        'cnn_onecycle',             # CNN with OneCycle
        'baseline_resnet',          # Your current setup (for comparison)
    ]
    
    configs_to_run = args.configs if args.configs else all_configs
    
    print("=" * 70)
    print("ADVANCED NEURAL NETWORK EXPERIMENTS")
    print("=" * 70)
    print(f"Device: {args.device}")
    print(f"Configurations to run: {len(configs_to_run)}")
    print(f"Configs: {', '.join(configs_to_run)}")
    print()
    
    if not args.compare_only:
        # Run experiments
        successful = []
        failed = []
        
        for i, config in enumerate(configs_to_run, 1):
            print(f"\n{'*' * 70}")
            print(f"Experiment {i}/{len(configs_to_run)}: {config}")
            print(f"{'*' * 70}")
            
            if run_experiment(config, args.device):
                successful.append(config)
            else:
                failed.append(config)
        
        print("\n" + "=" * 70)
        print("EXPERIMENTS SUMMARY")
        print("=" * 70)
        print(f"Successful: {len(successful)}/{len(configs_to_run)}")
        print(f"Failed: {len(failed)}/{len(configs_to_run)}")
        if failed:
            print(f"Failed configs: {', '.join(failed)}")
        print()
    
    # Collect and compare results
    print("Collecting results...")
    df = collect_results()
    
    if len(df) == 0:
        print("No results found!")
        return
    
    print_comparison(df)
    save_comparison(df)
    
    print("\n✅ All experiments completed!")


if __name__ == '__main__':
    main()
