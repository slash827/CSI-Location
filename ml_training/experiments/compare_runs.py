"""
Compare results from multiple experiment runs.

Usage:
    python experiments/compare_runs.py
    python experiments/compare_runs.py --pattern "baseline_2025-11-07*"
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_run_results(run_dir):
    """Load results from a single run."""
    config_file = run_dir / 'config.json'
    comparison_file = run_dir / 'model_comparison.txt'
    
    if not config_file.exists() or not comparison_file.exists():
        return None
    
    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Parse comparison file for best model
    with open(comparison_file, 'r') as f:
        lines = f.readlines()
    
    # Find validation results
    results = {}
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('=') and not line.startswith('-'):
            if 'Model' in line and 'Train MAE' in line:
                # Header line, skip
                continue
            parts = line.split()
            if len(parts) >= 5:
                try:
                    model_name = parts[0]
                    val_mae = float(parts[2])
                    val_r2 = float(parts[4])
                    results[model_name] = {'mae': val_mae, 'r2': val_r2}
                except:
                    pass
    
    return {
        'timestamp': config.get('timestamp', 'unknown'),
        'n_features': config.get('n_features_selected', 0),
        'feature_selection': config.get('feature_selection', {}),
        'results': results,
        'config': config
    }


def compare_runs(results_dir, pattern='baseline_*'):
    """Compare all runs matching pattern."""
    results_dir = Path(results_dir)
    
    # Find all matching runs
    runs = sorted(results_dir.glob(pattern))
    
    if not runs:
        print(f"No runs found matching pattern: {pattern}")
        return
    
    print("=" * 100)
    print("EXPERIMENT COMPARISON")
    print("=" * 100)
    print(f"\nFound {len(runs)} runs:\n")
    
    # Load all runs
    run_data = []
    for run_dir in runs:
        data = load_run_results(run_dir)
        if data:
            run_data.append((run_dir.name, data))
    
    if not run_data:
        print("No valid results found.")
        return
    
    # Print header
    print(f"{'Run':<35} {'Features':<10} {'Best Model':<15} {'Val MAE':<10} {'Val R²':<10}")
    print("-" * 100)
    
    # Print each run
    for run_name, data in run_data:
        n_features = data['n_features']
        
        # Find best model (lowest MAE)
        if data['results']:
            best_model = min(data['results'].items(), key=lambda x: x[1]['mae'])
            best_name = best_model[0]
            best_mae = best_model[1]['mae']
            best_r2 = best_model[1]['r2']
        else:
            best_name = 'N/A'
            best_mae = float('nan')
            best_r2 = float('nan')
        
        print(f"{run_name:<35} {n_features:<10} {best_name:<15} {best_mae:<10.2f} {best_r2:<10.4f}")
    
    print("\n" + "=" * 100)
    
    # Detailed comparison
    print("\nDETAILED COMPARISON BY MODEL")
    print("=" * 100)
    
    # Get all unique models
    all_models = set()
    for _, data in run_data:
        all_models.update(data['results'].keys())
    
    for model in sorted(all_models):
        print(f"\n{model.upper()}:")
        print("-" * 60)
        print(f"{'Run':<35} {'Features':<10} {'Val MAE':<10} {'Val R²':<10}")
        print("-" * 60)
        
        for run_name, data in run_data:
            if model in data['results']:
                mae = data['results'][model]['mae']
                r2 = data['results'][model]['r2']
                n_features = data['n_features']
                print(f"{run_name:<35} {n_features:<10} {mae:<10.2f} {r2:<10.4f}")
        
    print("\n" + "=" * 100)
    
    # Feature selection analysis
    print("\nFEATURE SELECTION IMPACT")
    print("=" * 100)
    
    feature_runs = {}
    for run_name, data in run_data:
        n_feat = data['n_features']
        if n_feat not in feature_runs:
            feature_runs[n_feat] = []
        
        # Get best model for this run
        if data['results']:
            best_model = min(data['results'].items(), key=lambda x: x[1]['mae'])
            feature_runs[n_feat].append({
                'name': run_name,
                'mae': best_model[1]['mae'],
                'r2': best_model[1]['r2'],
                'model': best_model[0]
            })
    
    print(f"\n{'Features':<10} {'Avg MAE':<12} {'Avg R²':<12} {'Best MAE':<12} {'# Runs':<10}")
    print("-" * 60)
    
    for n_feat in sorted(feature_runs.keys()):
        runs = feature_runs[n_feat]
        avg_mae = sum(r['mae'] for r in runs) / len(runs)
        avg_r2 = sum(r['r2'] for r in runs) / len(runs)
        best_mae = min(r['mae'] for r in runs)
        
        print(f"{n_feat:<10} {avg_mae:<12.2f} {avg_r2:<12.4f} {best_mae:<12.2f} {len(runs):<10}")
    
    print("\n" + "=" * 100)
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 60)
    
    # Find best performing run
    best_run = min(run_data, key=lambda x: min(r['mae'] for r in x[1]['results'].values()) 
                   if x[1]['results'] else float('inf'))
    best_name = best_run[0]
    best_data = best_run[1]
    best_model = min(best_data['results'].items(), key=lambda x: x[1]['mae'])
    
    print(f"\n🏆 Best Overall Run: {best_name}")
    print(f"   Features: {best_data['n_features']}")
    print(f"   Best Model: {best_model[0]}")
    print(f"   Val MAE: {best_model[1]['mae']:.2f} m")
    print(f"   Val R²: {best_model[1]['r2']:.4f}")
    
    # Feature selection recommendation
    if len(feature_runs) > 1:
        print(f"\n📊 Feature Selection Analysis:")
        
        # Compare different feature counts
        sorted_features = sorted(feature_runs.items(), key=lambda x: x[0])
        
        for i in range(len(sorted_features) - 1):
            n_feat1, runs1 = sorted_features[i]
            n_feat2, runs2 = sorted_features[i + 1]
            
            avg_mae1 = sum(r['mae'] for r in runs1) / len(runs1)
            avg_mae2 = sum(r['mae'] for r in runs2) / len(runs2)
            
            if avg_mae1 < avg_mae2:
                improvement = ((avg_mae2 - avg_mae1) / avg_mae2) * 100
                print(f"   {n_feat1} features: {improvement:.1f}% better MAE than {n_feat2} features")
        
        # Sweet spot
        best_feature_count = min(feature_runs.items(), 
                                key=lambda x: sum(r['mae'] for r in x[1]) / len(x[1]))[0]
        print(f"\n   ✅ Recommended: {best_feature_count} features (best accuracy/speed trade-off)")
    
    print("\n" + "=" * 100)


def main():
    """Main comparison script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Compare experiment runs')
    parser.add_argument('--results_dir', type=str, 
                       default=str(Path(__file__).parent.parent / 'results'),
                       help='Results directory')
    parser.add_argument('--pattern', type=str, default='baseline_*',
                       help='Glob pattern to match run names')
    
    args = parser.parse_args()
    
    compare_runs(args.results_dir, args.pattern)


if __name__ == "__main__":
    main()
