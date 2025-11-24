"""
Compare different feature selection strategies.

Tests multiple combinations of:
- Feature importance methods (mutual_info, f_test, random_forest)
- Number of features (20, 50, 100, 200)
- Trains simple Linear Regression on each

Goal: Find optimal feature selection strategy for best performance.
"""

import numpy as np
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
import time
import sys

sys.path.insert(0, str(Path(__file__).parent))

from generate_and_filter_data import DataGenerator
from config import RANDOM_SEED


def quick_evaluate(X_train, y_train, X_val, y_val):
    """Quick linear regression evaluation."""
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_val)
    errors = np.sqrt(np.sum((y_pred - y_val)**2, axis=1))
    mae = errors.mean()
    r2 = r2_score(y_val, y_pred)
    
    return mae, r2


def main():
    print("=" * 80)
    print("FEATURE SELECTION STRATEGY COMPARISON")
    print("=" * 80)
    
    # Initialize generator
    generator = DataGenerator()
    generator.load_data()
    
    # Test configurations
    methods = ['mutual_info', 'f_test', 'random_forest']
    n_features_list = [10, 20, 30, 50, 75, 100, 150, 200]
    
    results = []
    
    # Baseline: All features
    print("\n" + "-" * 80)
    print(f"Testing BASELINE (all {generator.X_train.shape[1]} features)")
    mae, r2 = quick_evaluate(generator.X_train, generator.y_train,
                             generator.X_val, generator.y_val)
    results.append({
        'method': 'baseline',
        'n_features': generator.X_train.shape[1],
        'mae': mae,
        'r2': r2
    })
    print(f"  MAE: {mae:.2f} m, R²: {r2:.4f}")
    
    # Test each method
    for method in methods:
        print("\n" + "-" * 80)
        print(f"Testing method: {method.upper()}")
        print("-" * 80)
        
        # Analyze importance once per method
        generator.analyze_feature_importance(method=method)
        
        for n_features in n_features_list:
            if n_features > generator.X_train.shape[1]:
                continue
            
            print(f"\n  Testing with {n_features} features...", end=" ")
            
            # Select features
            generator.select_features(n_features=n_features)
            X_train_filtered, y_train, X_val_filtered, y_val = generator.apply_feature_selection()
            
            # Evaluate
            mae, r2 = quick_evaluate(X_train_filtered, y_train, 
                                     X_val_filtered, y_val)
            
            results.append({
                'method': method,
                'n_features': n_features,
                'mae': mae,
                'r2': r2
            })
            
            print(f"MAE: {mae:.2f} m, R²: {r2:.4f}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY - SORTED BY MAE")
    print("=" * 80)
    print(f"\n{'Method':<15} {'Features':<10} {'MAE (m)':<12} {'R²':<10} {'vs Baseline':<12}")
    print("-" * 80)
    
    # Sort by MAE
    sorted_results = sorted(results, key=lambda x: x['mae'])
    baseline_mae = results[0]['mae']
    
    for i, result in enumerate(sorted_results[:20], 1):  # Top 20
        improvement = baseline_mae - result['mae']
        marker = "🏆" if i == 1 else "⭐" if i <= 5 else ""
        
        print(f"{marker} {result['method']:<15} {result['n_features']:<10} "
              f"{result['mae']:<12.2f} {result['r2']:<10.4f} {improvement:+.2f} m")
    
    # Best per method
    print("\n" + "=" * 80)
    print("BEST CONFIGURATION PER METHOD")
    print("=" * 80)
    
    for method in ['baseline'] + methods:
        method_results = [r for r in results if r['method'] == method]
        if not method_results:
            continue
        
        best = min(method_results, key=lambda x: x['mae'])
        print(f"\n{method.upper()}:")
        print(f"  Best features: {best['n_features']}")
        print(f"  MAE: {best['mae']:.2f} m")
        print(f"  R²: {best['r2']:.4f}")
        print(f"  Improvement: {baseline_mae - best['mae']:+.2f} m")
    
    # Save results
    output_dir = Path(__file__).parent / "output" / "generated_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    import pandas as pd
    df = pd.DataFrame(results)
    csv_file = output_dir / "feature_selection_comparison.csv"
    df.to_csv(csv_file, index=False)
    print(f"\n✓ Results saved to: {csv_file}")
    
    # Recommendation
    best = sorted_results[0]
    print("\n" + "=" * 80)
    print("🎯 RECOMMENDATION")
    print("=" * 80)
    print(f"\nBest strategy: {best['method'].upper()} with {best['n_features']} features")
    print(f"Expected MAE: {best['mae']:.2f} m")
    print(f"Improvement: {baseline_mae - best['mae']:.2f} m ({100*(baseline_mae - best['mae'])/baseline_mae:.1f}%)")
    print(f"\nCommand to generate:")
    print(f"  python generate_and_filter_data.py --method {best['method']} "
          f"--n_features {best['n_features']} --output_name optimal_dataset")


if __name__ == "__main__":
    main()
