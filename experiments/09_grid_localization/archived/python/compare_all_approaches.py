"""
Comprehensive Comparison: Gaussian vs Random Forest vs Metric Fusion

This script runs a complete comparison to answer:
1. Is Random Forest better than Gaussian for single metrics?
2. Does combining metrics (RSS+SINR) improve accuracy?
3. How much does history help with combined metrics?

Usage:
    python compare_all_approaches.py --data-dir results/sim_data_xxx
"""

import argparse
import json
import numpy as np
from pathlib import Path
from localization_pipeline import Pipeline
import matplotlib.pyplot as plt

def run_comparison(data_dir):
    """Run comprehensive comparison"""
    
    # Test configurations
    configs = [
        # Gaussian baselines
        {'name': 'Gaussian-RSS', 'model': 'gaussian', 'metrics': ['rss']},
        {'name': 'Gaussian-SINR', 'model': 'gaussian', 'metrics': ['sinr']},
        {'name': 'Gaussian-CQI', 'model': 'gaussian', 'metrics': ['cqi']},
        
        # Random Forest single metrics
        {'name': 'RF-RSS', 'model': 'random_forest', 'metrics': ['rss']},
        {'name': 'RF-SINR', 'model': 'random_forest', 'metrics': ['sinr']},
        {'name': 'RF-CQI', 'model': 'random_forest', 'metrics': ['cqi']},
        
        # Random Forest fusion (2 metrics)
        {'name': 'RF-RSS+SINR', 'model': 'random_forest', 'metrics': [['RSS', 'SINR']]},
        {'name': 'RF-RSS+CQI', 'model': 'random_forest', 'metrics': [['RSS', 'CQI']]},
        {'name': 'RF-SINR+CQI', 'model': 'random_forest', 'metrics': [['SINR', 'CQI']]},
        
        # Random Forest fusion (all 3 metrics)
        {'name': 'RF-All', 'model': 'random_forest', 'metrics': [['RSS', 'SINR', 'CQI']]},
    ]
    
    results = {}
    
    print("\n" + "="*80)
    print("COMPREHENSIVE COMPARISON: Gaussian vs Random Forest vs Metric Fusion")
    print("="*80)
    
    for i, config in enumerate(configs, 1):
        print(f"\n[{i}/{len(configs)}] Running: {config['name']}")
        print("-" * 80)
        
        # Create pipeline
        output_dir = Path(data_dir) / f"comparison_{config['name']}"
        pipeline = Pipeline(
            data_dir=data_dir,
            output_dir=output_dir,
            test_ratio=0.2,
            max_history=3
        )
        
        # Run
        try:
            pipeline.run(
                metrics_to_test=config['metrics'],
                model_type=config['model']
            )
            
            # Extract results
            metric_key = list(pipeline.results.keys())[0]
            static_acc = pipeline.results[metric_key]['static']['accuracy']
            trans_accs = [r['accuracy'] for r in pipeline.results[metric_key]['transition']]
            best_trans_acc = max(trans_accs)
            
            results[config['name']] = {
                'static': static_acc,
                'transition': best_trans_acc,
                'improvement': best_trans_acc - static_acc
            }
            
            print(f"  ✓ Static: {static_acc:.2f}%")
            print(f"  ✓ Best Transition: {best_trans_acc:.2f}%")
            print(f"  ✓ Improvement: {best_trans_acc - static_acc:+.2f}%")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[config['name']] = None
    
    # Generate comparison report
    print("\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)
    
    # Save to file
    report_path = Path(data_dir) / "COMPARISON_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Comprehensive Comparison Report\n\n")
        f.write("## Results Table\n\n")
        f.write("| Configuration | Static Acc | Best Trans Acc | Improvement |\n")
        f.write("|--------------|-----------|---------------|-------------|\n")
        
        for name, res in results.items():
            if res:
                f.write(f"| {name:20} | {res['static']:6.2f}% | {res['transition']:6.2f}% | {res['improvement']:+6.2f}% |\n")
        
        f.write("\n## Key Findings\n\n")
        
        # Analysis 1: Gaussian vs RF (same metric)
        f.write("### 1. Gaussian vs Random Forest (Single Metrics)\n\n")
        for metric in ['RSS', 'SINR', 'CQI']:
            gauss_name = f'Gaussian-{metric}'
            rf_name = f'RF-{metric}'
            if gauss_name in results and rf_name in results and results[gauss_name] and results[rf_name]:
                gauss_acc = results[gauss_name]['transition']
                rf_acc = results[rf_name]['transition']
                diff = rf_acc - gauss_acc
                winner = "RF" if diff > 0 else "Gaussian"
                f.write(f"**{metric}**: {winner} wins by {abs(diff):.2f}% ")
                f.write(f"({gauss_acc:.2f}% vs {rf_acc:.2f}%)\n\n")
        
        # Analysis 2: Single vs Combined metrics
        f.write("### 2. Single Metrics vs Combinations\n\n")
        if 'RF-RSS' in results and 'RF-RSS+SINR' in results and results['RF-RSS'] and results['RF-RSS+SINR']:
            rss_acc = results['RF-RSS']['transition']
            fusion_acc = results['RF-RSS+SINR']['transition']
            gain = fusion_acc - rss_acc
            f.write(f"**RSS+SINR vs RSS alone**: {gain:+.2f}% improvement\n")
            f.write(f"  - RSS alone: {rss_acc:.2f}%\n")
            f.write(f"  - RSS+SINR: {fusion_acc:.2f}%\n\n")
            
            if gain > 5:
                f.write("✓ **Conclusion**: Metric fusion provides significant benefit!\n\n")
            elif gain > 0:
                f.write("≈ **Conclusion**: Metric fusion provides modest benefit.\n\n")
            else:
                f.write("✗ **Conclusion**: Metrics may be highly correlated.\n\n")
        
        # Analysis 3: Effect of adding more metrics
        f.write("### 3. Two-Metric vs Three-Metric Fusion\n\n")
        if 'RF-RSS+SINR' in results and 'RF-All' in results and results['RF-RSS+SINR'] and results['RF-All']:
            two_metric = results['RF-RSS+SINR']['transition']
            three_metric = results['RF-All']['transition']
            gain = three_metric - two_metric
            f.write(f"**Adding CQI to RSS+SINR**: {gain:+.2f}% change\n")
            f.write(f"  - RSS+SINR: {two_metric:.2f}%\n")
            f.write(f"  - RSS+SINR+CQI: {three_metric:.2f}%\n\n")
        
        f.write("### 4. Best Overall Configuration\n\n")
        best_config = max(results.items(), key=lambda x: x[1]['transition'] if x[1] else 0)
        f.write(f"**Winner**: {best_config[0]}\n")
        f.write(f"  - Static: {best_config[1]['static']:.2f}%\n")
        f.write(f"  - Transition: {best_config[1]['transition']:.2f}%\n")
        f.write(f"  - Total Improvement: {best_config[1]['improvement']:+.2f}%\n")
    
    print(f"\n✓ Comparison report saved: {report_path}")
    
    # Create visualization
    create_comparison_plots(results, data_dir)
    
    return results


def create_comparison_plots(results, data_dir):
    """Create comparison visualizations"""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Static accuracy comparison
    ax = axes[0, 0]
    names = [name for name, res in results.items() if res]
    static_accs = [res['static'] for name, res in results.items() if res]
    colors = ['blue' if 'Gaussian' in name else 'green' if 'RF-' in name and '+' not in name else 'red' 
              for name, res in results.items() if res]
    
    ax.barh(names, static_accs, color=colors, alpha=0.7)
    ax.set_xlabel('Static Accuracy (%)')
    ax.set_title('Static Mode Comparison')
    ax.grid(axis='x', alpha=0.3)
    
    # Plot 2: Transition accuracy comparison
    ax = axes[0, 1]
    trans_accs = [res['transition'] for name, res in results.items() if res]
    ax.barh(names, trans_accs, color=colors, alpha=0.7)
    ax.set_xlabel('Best Transition Accuracy (%)')
    ax.set_title('Transition Mode Comparison')
    ax.grid(axis='x', alpha=0.3)
    
    # Plot 3: Improvement from transition
    ax = axes[1, 0]
    improvements = [res['improvement'] for name, res in results.items() if res]
    ax.barh(names, improvements, color=colors, alpha=0.7)
    ax.set_xlabel('Improvement (Transition - Static) %')
    ax.set_title('Benefit of Using History')
    ax.axvline(0, color='black', linestyle='--', linewidth=0.5)
    ax.grid(axis='x', alpha=0.3)
    
    # Plot 4: Best configs summary
    ax = axes[1, 1]
    # Group by category
    categories = {
        'Gaussian': [name for name in results if 'Gaussian' in name and results[name]],
        'RF Single': [name for name in results if 'RF-' in name and '+' not in name and results[name]],
        'RF Fusion': [name for name in results if 'RF-' in name and '+' in name and results[name]]
    }
    
    cat_names = []
    cat_means = []
    cat_maxs = []
    for cat, members in categories.items():
        if members:
            cat_names.append(cat)
            accs = [results[m]['transition'] for m in members]
            cat_means.append(np.mean(accs))
            cat_maxs.append(np.max(accs))
    
    x = np.arange(len(cat_names))
    width = 0.35
    ax.bar(x - width/2, cat_means, width, label='Mean', alpha=0.7)
    ax.bar(x + width/2, cat_maxs, width, label='Best', alpha=0.7)
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Category Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(cat_names)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plot_path = Path(data_dir) / 'comparison_plots.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"✓ Comparison plots saved: {plot_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Run comprehensive comparison')
    parser.add_argument('--data-dir', required=True, help='Simulation data directory')
    
    args = parser.parse_args()
    
    results = run_comparison(args.data_dir)
    
    print("\n" + "="*80)
    print("COMPARISON COMPLETE!")
    print("="*80)
    print(f"\nResults saved in: {args.data_dir}/")
    print("  - COMPARISON_REPORT.md")
    print("  - comparison_plots.png")
    print("  - comparison_<config>/ (individual results)")


if __name__ == '__main__':
    main()
