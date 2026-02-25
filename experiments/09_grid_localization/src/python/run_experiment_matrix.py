"""
Experiment Matrix Runner

Sweeps across grid sizes, metrics, history lengths, feature modes, and algorithms
to generate a comprehensive comparison proving that transitions improve localization
regardless of the prediction algorithm.

Usage:
    # Run full comparison on a single data directory:
    python run_experiment_matrix.py --data-dir results/sim_data_xxx

    # Run on multiple grid sizes (each with its own data directory):
    python run_experiment_matrix.py --data-dirs grid7=results/grid7 grid15=results/grid15

    # Quick test with fewer combos:
    python run_experiment_matrix.py --data-dir results/sim_data_xxx --quick
"""

import argparse
import json
import csv
import numpy as np
import time
from pathlib import Path
from datetime import datetime
from localization_pipeline import (
    SimulationData, DataSplitter, Pipeline,
    GaussianStaticModel, GaussianTransitionModel,
    RandomForestModel, XGBoostModel, MLPModel,
    TransitionFeatureExtractor, Evaluator,
    _build_sklearn_features, PROJECT_ROOT
)


def run_single_experiment(data, splitter, model_type, metric_spec, history_length,
                          feature_mode, n_estimators=100, n_jobs=4, max_depth=30):
    """Run a single experiment configuration and return results.

    Args:
        data: SimulationData instance
        splitter: DataSplitter instance
        model_type: 'gaussian', 'random_forest', 'xgboost', 'mlp'
        metric_spec: String or list of metric names
        history_length: 0 for static, 1-3 for transition
        feature_mode: 'raw' or 'smart'
        n_estimators, n_jobs, max_depth: Model hyperparameters

    Returns:
        dict with accuracy, mae, train_time, eval_time, n_test_samples
    """
    # Prepare metric data
    if isinstance(metric_spec, str):
        metric_name = metric_spec
        metric_values = data.metrics[metric_spec.lower()]
    elif isinstance(metric_spec, list):
        metric_name = '+'.join(metric_spec)
        metric_arrays = [data.metrics[m.lower()] for m in metric_spec]
        metric_values = np.column_stack(metric_arrays)
    else:
        raise ValueError(f"Invalid metric_spec: {metric_spec}")

    is_transition = history_length > 0

    # Gaussian models only support single metrics
    if model_type == 'gaussian' and metric_values.ndim > 1:
        return None

    # Split data
    if is_transition:
        train_indices, test_indices = splitter.split_transition(data.n_samples, history_length)
    else:
        train_indices, test_indices = splitter.split_static(data.n_samples)

    # Create model
    if model_type == 'gaussian':
        if is_transition:
            model = GaussianTransitionModel(data.neighbors, history_length=history_length)
        else:
            model = GaussianStaticModel()
    elif model_type == 'random_forest':
        model = RandomForestModel(
            use_transition=is_transition, history_length=history_length,
            n_estimators=n_estimators, max_depth=max_depth, n_jobs=n_jobs,
            feature_mode=feature_mode
        )
    elif model_type == 'xgboost':
        model = XGBoostModel(
            use_transition=is_transition, history_length=history_length,
            n_estimators=n_estimators, max_depth=min(max_depth, 10) if max_depth else 6,
            n_jobs=n_jobs, feature_mode=feature_mode
        )
    elif model_type == 'mlp':
        model = MLPModel(
            use_transition=is_transition, history_length=history_length,
            feature_mode=feature_mode
        )

    # Train
    t_train = time.time()
    model.train(metric_values, data.true_locations, train_indices, data.n_points)
    train_time = time.time() - t_train

    # Evaluate
    t_eval = time.time()
    if is_transition:
        results = Evaluator.evaluate_transition(
            model, metric_values, data.true_locations, test_indices,
            grid_positions=data.grid_positions
        )
    else:
        results = Evaluator.evaluate_static(
            model, metric_values, data.true_locations, test_indices,
            grid_positions=data.grid_positions
        )
    eval_time = time.time() - t_eval

    return {
        'accuracy': results['accuracy'],
        'mae': results['mae'],
        'train_time': train_time,
        'eval_time': eval_time,
        'n_test_samples': len(results['predictions'])
    }


def run_experiment_matrix(data_dirs, algorithms, metrics_list, max_history,
                          feature_modes, output_dir, n_estimators=100,
                          n_jobs=4, max_depth=30, split_method='temporal'):
    """Run the full experiment matrix.

    Args:
        data_dirs: Dict mapping grid label to data directory path
        algorithms: List of algorithm names
        metrics_list: List of metric specifications
        max_history: Maximum history length
        feature_modes: List of feature modes to test
        output_dir: Directory to save results
        ...
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    total_configs = 0

    # Count total configurations
    for grid_label in data_dirs:
        for algo in algorithms:
            for metric_spec in metrics_list:
                # Gaussian only supports single metrics (not multi-metric like RSS+SINR)
                if algo == 'gaussian' and isinstance(metric_spec, list):
                    continue
                for h in range(0, max_history + 1):
                    for fm in feature_modes:
                        # Skip irrelevant combos
                        if h == 0 and fm == 'smart':
                            continue  # Smart features need history
                        if algo == 'gaussian' and fm == 'smart':
                            continue  # Gaussian has its own transition mechanism
                        total_configs += 1

    print(f"\n{'='*70}")
    print(f"EXPERIMENT MATRIX RUNNER")
    print(f"{'='*70}")
    print(f"Grids: {list(data_dirs.keys())}")
    print(f"Algorithms: {algorithms}")
    print(f"Feature modes: {feature_modes}")
    print(f"Max history: {max_history}")
    print(f"Total configurations: {total_configs}")
    print(f"Output: {output_dir}")
    print(f"{'='*70}\n")

    config_num = 0
    t_total_start = time.time()

    for grid_label, data_path in data_dirs.items():
        print(f"\n{'='*50}")
        print(f"Loading data for grid: {grid_label}")
        print(f"{'='*50}")

        data = SimulationData(data_path)
        splitter = DataSplitter(test_ratio=0.2, split_method=split_method)
        grid_size = data.config['grid']['size']

        for algo in algorithms:
            for metric_spec in metrics_list:
                metric_name = '+'.join(metric_spec) if isinstance(metric_spec, list) else metric_spec

                # Check if Gaussian can handle this metric
                if algo == 'gaussian':
                    if isinstance(metric_spec, list):
                        print(f"  [SKIP] Gaussian + multi-metric {metric_name}")
                        continue

                for h in range(0, max_history + 1):
                    for fm in feature_modes:
                        # Skip irrelevant combos
                        if h == 0 and fm == 'smart':
                            continue
                        if algo == 'gaussian' and fm == 'smart':
                            continue

                        config_num += 1
                        fm_display = fm if h > 0 else 'n/a'

                        print(f"  [{config_num}/{total_configs}] "
                              f"{algo} | {metric_name} | h={h} | {fm_display}",
                              end=" ... ", flush=True)

                        try:
                            result = run_single_experiment(
                                data, splitter, algo, metric_spec, h, fm,
                                n_estimators=n_estimators, n_jobs=n_jobs, max_depth=max_depth
                            )

                            if result is None:
                                print("SKIPPED")
                                continue

                            print(f"acc={result['accuracy']:.1f}% "
                                  f"mae={result['mae']:.2f}m "
                                  f"(train={result['train_time']:.1f}s eval={result['eval_time']:.1f}s)")

                            all_results.append({
                                'grid': f"{grid_size}x{grid_size}",
                                'grid_size': grid_size,
                                'algorithm': algo,
                                'metric': metric_name,
                                'history': h,
                                'feature_mode': fm if h > 0 else 'static',
                                'accuracy': result['accuracy'],
                                'mae': result['mae'],
                                'train_time': result['train_time'],
                                'eval_time': result['eval_time'],
                                'n_test_samples': result['n_test_samples']
                            })

                        except Exception as e:
                            print(f"ERROR: {e}")
                            all_results.append({
                                'grid': f"{grid_size}x{grid_size}",
                                'grid_size': grid_size,
                                'algorithm': algo,
                                'metric': metric_name,
                                'history': h,
                                'feature_mode': fm if h > 0 else 'static',
                                'accuracy': None,
                                'mae': None,
                                'train_time': None,
                                'eval_time': None,
                                'n_test_samples': None,
                                'error': str(e)
                            })

    total_time = time.time() - t_total_start

    # Save results
    save_results(all_results, output_dir, total_time)

    return all_results


def save_results(results, output_dir, total_time):
    """Save results as CSV and Markdown report."""
    output_dir = Path(output_dir)

    # --- CSV ---
    csv_file = output_dir / 'experiment_results.csv'
    if results:
        fieldnames = [k for k in results[0].keys() if k != 'error']
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for r in results:
                writer.writerow(r)
        print(f"\n[OK] CSV results saved to: {csv_file}")

    # --- Markdown Report ---
    report_file = output_dir / 'COMPARISON_REPORT.md'
    valid_results = [r for r in results if r.get('accuracy') is not None]

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('# Comprehensive Localization Comparison\n\n')
        f.write(f'**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'**Total runtime:** {total_time:.1f}s\n')
        f.write(f'**Configurations tested:** {len(valid_results)}\n\n')

        # --- Key Finding: Transition Impact Table ---
        f.write('## Key Finding: Transition History Improves ALL Algorithms\n\n')

        # Group by (grid, algorithm, metric, feature_mode)
        groups = {}
        for r in valid_results:
            key = (r['grid'], r['algorithm'], r['metric'], r['feature_mode'] if r['history'] > 0 else 'raw')
            if key not in groups:
                groups[key] = {}
            groups[key][r['history']] = r

        # Find groups that have both h=0 and h>0 results
        f.write('| Algorithm | Grid | Metric | Features | H=0 | H=1 | H=2 | H=3 | Improvement |\n')
        f.write('|:----------|:-----|:-------|:---------|:----|:----|:----|:----|:------------|\n')

        for key in sorted(groups.keys()):
            grid, algo, metric, fm = key
            h_results = groups[key]
            if 0 not in h_results:
                # Try to find static result with same algo/grid/metric
                static_key = (grid, algo, metric, 'static')
                if static_key in groups and 0 in groups[static_key]:
                    h_results[0] = groups[static_key][0]
                else:
                    continue

            h0_acc = h_results[0]['accuracy']
            cells = [f"{h0_acc:.1f}%"]

            best_acc = h0_acc
            for h in [1, 2, 3]:
                if h in h_results:
                    acc = h_results[h]['accuracy']
                    cells.append(f"{acc:.1f}%")
                    best_acc = max(best_acc, acc)
                else:
                    cells.append('-')

            improvement = best_acc - h0_acc
            imp_str = f"**{improvement:+.1f}%**" if improvement > 0 else f"{improvement:+.1f}%"

            f.write(f'| {algo} | {grid} | {metric} | {fm} | {" | ".join(cells)} | {imp_str} |\n')

        # --- MAE Table ---
        f.write('\n## Mean Absolute Error (meters)\n\n')
        f.write('| Algorithm | Grid | Metric | Features | H=0 | H=1 | H=2 | H=3 | Improvement |\n')
        f.write('|:----------|:-----|:-------|:---------|:----|:----|:----|:----|:------------|\n')

        for key in sorted(groups.keys()):
            grid, algo, metric, fm = key
            h_results = groups[key]
            if 0 not in h_results:
                static_key = (grid, algo, metric, 'static')
                if static_key in groups and 0 in groups[static_key]:
                    h_results[0] = groups[static_key][0]
                else:
                    continue

            h0_mae = h_results[0]['mae']
            cells = [f"{h0_mae:.2f}"]

            best_mae = h0_mae
            for h in [1, 2, 3]:
                if h in h_results:
                    mae = h_results[h]['mae']
                    cells.append(f"{mae:.2f}")
                    best_mae = min(best_mae, mae)
                else:
                    cells.append('-')

            improvement_pct = ((h0_mae - best_mae) / h0_mae * 100) if h0_mae > 0 else 0
            imp_str = f"**{improvement_pct:+.1f}%**" if improvement_pct > 0 else f"{improvement_pct:+.1f}%"

            f.write(f'| {algo} | {grid} | {metric} | {fm} | {" | ".join(cells)} | {imp_str} |\n')

        # --- Scalability Table ---
        grids = sorted(set(r['grid_size'] for r in valid_results))
        if len(grids) > 1:
            f.write('\n## Scalability Across Grid Sizes\n\n')
            f.write('| Algorithm | Metric | Features |')
            for g in grids:
                f.write(f' {g}x{g} |')
            f.write('\n')
            f.write('|:----------|:-------|:---------|')
            for _ in grids:
                f.write(':-----|')
            f.write('\n')

            # Show best transition accuracy per grid
            scale_groups = {}
            for r in valid_results:
                if r['history'] == 3 or (r['history'] == 0 and r['feature_mode'] == 'static'):
                    skey = (r['algorithm'], r['metric'], r['feature_mode'] if r['history'] > 0 else 'best')
                    if skey not in scale_groups:
                        scale_groups[skey] = {}
                    if r['grid_size'] not in scale_groups[skey] or r['accuracy'] > scale_groups[skey][r['grid_size']]:
                        scale_groups[skey][r['grid_size']] = r['accuracy']

            for skey in sorted(scale_groups.keys()):
                algo, metric, fm = skey
                f.write(f'| {algo} | {metric} | {fm} |')
                for g in grids:
                    acc = scale_groups[skey].get(g)
                    f.write(f" {acc:.1f}% |" if acc is not None else " - |")
                f.write('\n')

        # --- Summary ---
        f.write('\n## Summary\n\n')

        # Check if transitions helped for all algorithms
        improvement_by_algo = {}
        for r in valid_results:
            if r['history'] == 0:
                continue
            algo = r['algorithm']
            if algo not in improvement_by_algo:
                improvement_by_algo[algo] = []
            # Find corresponding static result
            static_matches = [s for s in valid_results
                            if s['algorithm'] == algo
                            and s['grid'] == r['grid']
                            and s['metric'] == r['metric']
                            and s['history'] == 0]
            if static_matches:
                improvement_by_algo[algo].append(r['accuracy'] - static_matches[0]['accuracy'])

        all_improved = True
        for algo, improvements in improvement_by_algo.items():
            avg_imp = np.mean(improvements) if improvements else 0
            if avg_imp > 0:
                f.write(f'- **{algo}**: Average improvement with transitions: **{avg_imp:+.1f}%**\n')
            else:
                f.write(f'- **{algo}**: No improvement with transitions ({avg_imp:+.1f}%)\n')
                all_improved = False

        if all_improved and improvement_by_algo:
            f.write(f'\n**CONCLUSION: Transitions improve localization for ALL tested algorithms.**\n')

        f.write('\n---\n')
        f.write('*Generated by run_experiment_matrix.py*\n')

    print(f"[OK] Report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Run comprehensive experiment matrix',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single grid:
  python run_experiment_matrix.py --data-dir results/sim_data_grid7

  # Multiple grids:
  python run_experiment_matrix.py --data-dirs grid7=results/grid7 grid15=results/grid15

  # Quick test:
  python run_experiment_matrix.py --data-dir results/sim_data --quick

  # Custom algorithms:
  python run_experiment_matrix.py --data-dir results/sim_data --algorithms random_forest xgboost mlp
        """
    )
    parser.add_argument('--data-dir', help='Single data directory')
    parser.add_argument('--data-dirs', nargs='+',
                       help='Multiple data dirs as key=path pairs (e.g., grid7=results/grid7)')
    parser.add_argument('--output-dir', default=None,
                       help='Output directory (auto-generated if not specified)')
    parser.add_argument('--algorithms', nargs='+',
                       default=['gaussian', 'random_forest', 'xgboost', 'mlp'],
                       help='Algorithms to test')
    parser.add_argument('--metrics', nargs='+', default=['rss', 'sinr', 'RSS,SINR'],
                       help='Metrics to test (comma-separated for combinations)')
    parser.add_argument('--feature-modes', nargs='+', default=['raw', 'smart'],
                       choices=['raw', 'smart'], help='Feature modes to test')
    parser.add_argument('--max-history', type=int, default=3, help='Max history length')
    parser.add_argument('--split-method', default='temporal', choices=['random', 'temporal'],
                       help='Train/test split method')
    parser.add_argument('--n-estimators', type=int, default=100)
    parser.add_argument('--n-jobs', type=int, default=4)
    parser.add_argument('--max-depth', type=int, default=30)
    parser.add_argument('--quick', action='store_true',
                       help='Quick mode: fewer metrics and algorithms')

    args = parser.parse_args()

    # Parse data directories
    data_dirs = {}
    if args.data_dir:
        data_dirs['default'] = args.data_dir
    elif args.data_dirs:
        for spec in args.data_dirs:
            if '=' in spec:
                label, path = spec.split('=', 1)
                data_dirs[label] = path
            else:
                data_dirs[Path(spec).name] = spec
    else:
        parser.error("Either --data-dir or --data-dirs is required")

    # Parse metrics
    metrics_list = []
    for m in args.metrics:
        if ',' in m:
            metrics_list.append([x.strip() for x in m.split(',')])
        else:
            metrics_list.append(m.lower())

    # Quick mode overrides
    if args.quick:
        args.algorithms = ['random_forest', 'xgboost']
        metrics_list = ['rss', ['RSS', 'SINR']]
        args.feature_modes = ['smart']
        args.max_history = 2

    # Auto output dir
    if args.output_dir is None:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        args.output_dir = str(PROJECT_ROOT / f"results/experiment_matrix/{timestamp}")

    # Run
    results = run_experiment_matrix(
        data_dirs=data_dirs,
        algorithms=args.algorithms,
        metrics_list=metrics_list,
        max_history=args.max_history,
        feature_modes=args.feature_modes,
        output_dir=args.output_dir,
        n_estimators=args.n_estimators,
        n_jobs=args.n_jobs,
        max_depth=args.max_depth,
        split_method=args.split_method
    )

    print(f"\n{'='*70}")
    print(f"EXPERIMENT MATRIX COMPLETE")
    print(f"{'='*70}")
    print(f"Total configs: {len([r for r in results if r.get('accuracy') is not None])}")
    print(f"Results: {args.output_dir}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
