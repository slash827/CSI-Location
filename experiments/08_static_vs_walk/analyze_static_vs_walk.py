#!/usr/bin/env python3
"""
Analyze Static vs Random Walk CSI Data - Experiment 13
======================================================

This script compares CSI measurements between:
1. Static grid positions (exp13a) - UEs measured at fixed positions
2. Random walk transitions (exp13b) - UE arriving at positions after movement

The goal is to determine if a UE arriving at position B shows the same CSI
as if it was simply placed at position B (static measurement).
"""

import os
import sys
import numpy as np
import h5py
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any


def load_matlab_data(results_dir: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load the MATLAB results from both experiments.
    Uses h5py for MATLAB v7.3 files (HDF5 format).
    
    Returns:
        Tuple of (static_data, walk_data) dictionaries
    """
    # Find most recent exp13a and exp13b directories
    results_path = Path(results_dir)
    
    exp13a_dirs = sorted([d for d in results_path.glob("exp13a*") if d.is_dir()])
    exp13b_dirs = sorted([d for d in results_path.glob("exp13b*") if d.is_dir()])
    
    if not exp13a_dirs:
        raise FileNotFoundError("No exp13a results found in " + str(results_dir))
    if not exp13b_dirs:
        raise FileNotFoundError("No exp13b results found in " + str(results_dir))
    
    # Use most recent
    static_dir = exp13a_dirs[-1]
    walk_dir = exp13b_dirs[-1]
    
    print(f"Loading static data from: {static_dir}")
    print(f"Loading walk data from: {walk_dir}")
    
    static_file = static_dir / "static_grid_results.mat"
    walk_file = walk_dir / "random_walk_results.mat"
    
    if not static_file.exists():
        raise FileNotFoundError(f"Static results file not found: {static_file}")
    if not walk_file.exists():
        raise FileNotFoundError(f"Walk results file not found: {walk_file}")
    
    # Load using h5py for MATLAB v7.3 files
    static_data = load_mat_v73(str(static_file))
    walk_data = load_mat_v73(str(walk_file))
    
    return static_data, walk_data


def load_mat_v73(filepath: str) -> Dict[str, Any]:
    """
    Load a MATLAB v7.3 file using h5py.
    Recursively converts HDF5 groups and datasets to Python dicts and arrays.
    """
    data = {}
    with h5py.File(filepath, 'r') as f:
        for key in f.keys():
            data[key] = _convert_h5_item(f[key], f)
    return data


def _convert_h5_item(item, file_ref) -> Any:
    """
    Recursively convert HDF5 items to Python objects.
    """
    if isinstance(item, h5py.Dataset):
        arr = item[()]
        # Handle MATLAB strings (stored as uint16 arrays)
        if arr.dtype == np.uint16 or arr.dtype == np.uint8:
            try:
                # Try to decode as string
                if len(arr.shape) == 1:
                    return ''.join(chr(c) for c in arr if c != 0)
                elif len(arr.shape) == 2 and arr.shape[0] == 1:
                    return ''.join(chr(c) for c in arr[0] if c != 0)
            except:
                pass
        # Transpose to match MATLAB's column-major order
        if len(arr.shape) >= 2:
            arr = arr.T
        # Squeeze single-element arrays
        if arr.size == 1:
            return arr.item()
        return np.squeeze(arr)
    elif isinstance(item, h5py.Group):
        # Check if it's a struct array or cell array
        result = {}
        for key in item.keys():
            result[key] = _convert_h5_item(item[key], file_ref)
        return result
    elif isinstance(item, h5py.Reference):
        # Dereference and convert
        return _convert_h5_item(file_ref[item], file_ref)
    else:
        return item


def extract_transition_data(static_data: Dict, walk_data: Dict) -> Dict:
    """
    Extract transition differences for comparison.
    
    For each adjacent pair A→B:
    - Static: CSI(B) - CSI(A) from 100 repetitions
    - Walk: CSI at step N+1 - CSI at step N for all A→B transitions
    
    This compares the distribution of CSI changes when transitioning between
    the same pair of points.
    """
    results = {}
    
    # Get adjacent pairs definition
    # Shape: (n_pairs, 2) where each row is [from_point, to_point]
    adjacent_pairs = np.array(static_data['adjacent_pairs']).astype(int)
    if len(adjacent_pairs.shape) == 1:
        n_pairs = len(adjacent_pairs) // 2
        adjacent_pairs = adjacent_pairs.reshape(n_pairs, 2)
    
    print(f"  Adjacent pairs shape: {adjacent_pairs.shape}")
    print(f"  Adjacent pairs: {adjacent_pairs.tolist()}")
    
    # Get static differences - shape: (n_pairs, n_reps) for each metric
    static_diffs = static_data['diffs']
    print(f"  Static diffs keys: {list(static_diffs.keys()) if isinstance(static_diffs, dict) else 'not a dict'}")
    
    # Get walk transitions
    walk_transitions = walk_data['transitions']
    walk_from = np.array(walk_transitions['from_point']).flatten().astype(int)
    walk_to = np.array(walk_transitions['to_point']).flatten().astype(int)
    print(f"  Walk transitions: {len(walk_from)} total")
    
    # Metrics to analyze
    metric_names = ['RSS_wb_diff', 'SINR_wb_diff', 'CQI_wb_diff', 'path_loss_diff']
    
    results['pairs'] = adjacent_pairs
    results['static'] = {}
    results['walk'] = {}
    results['pair_names'] = []
    
    n_pairs = adjacent_pairs.shape[0]
    
    for metric in metric_names:
        metric_base = metric.replace('_diff', '')
        
        # Get static differences for this metric
        if isinstance(static_diffs, dict) and metric in static_diffs:
            static_vals = np.array(static_diffs[metric])
            # Ensure shape is (n_pairs, n_reps)
            if static_vals.shape[0] != n_pairs and len(static_vals.shape) > 1:
                static_vals = static_vals.T
            print(f"  Static {metric} shape: {static_vals.shape}")
        else:
            print(f"  WARNING: {metric} not found in static diffs")
            continue
        
        # Get walk differences for this metric
        if isinstance(walk_transitions, dict) and metric in walk_transitions:
            walk_vals = np.array(walk_transitions[metric]).flatten()
            print(f"  Walk {metric} shape: {walk_vals.shape}")
        else:
            print(f"  WARNING: {metric} not found in walk transitions")
            continue
        
        # Organize by pair
        results['static'][metric_base] = {}
        results['walk'][metric_base] = {}
        
        for pair_idx in range(n_pairs):
            pt1, pt2 = adjacent_pairs[pair_idx]
            pair_key = f"{pt1}->{pt2}"
            
            if pair_idx == 0:
                results['pair_names'].append(pair_key)
            
            # Static: all 100 repetitions for this pair
            if len(static_vals.shape) == 2:
                results['static'][metric_base][pair_key] = static_vals[pair_idx, :]
            else:
                results['static'][metric_base][pair_key] = static_vals
            
            # Walk: find all transitions matching this pair (either direction)
            # Forward: from pt1 to pt2
            forward_mask = (walk_from == pt1) & (walk_to == pt2)
            # Backward: from pt2 to pt1 (negate the difference)
            backward_mask = (walk_from == pt2) & (walk_to == pt1)
            
            forward_diffs = walk_vals[forward_mask]
            backward_diffs = -walk_vals[backward_mask]  # Negate for same direction
            
            all_walk_diffs = np.concatenate([forward_diffs, backward_diffs])
            results['walk'][metric_base][pair_key] = all_walk_diffs
            
            if metric == 'RSS_wb_diff':
                print(f"    Pair {pair_key}: {len(results['static'][metric_base][pair_key])} static, "
                      f"{len(forward_diffs)} forward + {len(backward_diffs)} backward = {len(all_walk_diffs)} walk")
    
    return results


def compute_pair_statistics(results: Dict) -> Dict:
    """
    Compute statistics and perform tests for each pair and metric.
    """
    stats_results = {}
    
    for metric in results['static'].keys():
        stats_results[metric] = {}
        
        for pair_key in results['static'][metric].keys():
            static_diffs = results['static'][metric][pair_key]
            walk_diffs = results['walk'][metric][pair_key]
            
            if len(static_diffs) < 5 or len(walk_diffs) < 5:
                continue
            
            # Basic statistics
            static_mean = np.mean(static_diffs)
            static_std = np.std(static_diffs)
            walk_mean = np.mean(walk_diffs)
            walk_std = np.std(walk_diffs)
            
            # Kolmogorov-Smirnov test
            ks_result = stats.ks_2samp(static_diffs, walk_diffs)
            ks_stat: float = float(ks_result[0])  # type: ignore[arg-type]
            ks_pvalue: float = float(ks_result[1])  # type: ignore[arg-type]
            
            # Mann-Whitney U test
            mw_result = stats.mannwhitneyu(static_diffs, walk_diffs, alternative='two-sided')
            mw_stat: float = float(mw_result[0])  # type: ignore[arg-type]
            mw_pvalue: float = float(mw_result[1])  # type: ignore[arg-type]
            
            # Welch's t-test
            tt_result = stats.ttest_ind(static_diffs, walk_diffs, equal_var=False)
            tt_stat: float = float(tt_result[0])  # type: ignore[arg-type]
            tt_pvalue: float = float(tt_result[1])  # type: ignore[arg-type]
            
            # Effect size (Cohen's d)
            pooled_std = np.sqrt((static_std**2 + walk_std**2) / 2)
            cohens_d = (walk_mean - static_mean) / pooled_std if pooled_std > 0 else 0
            
            stats_results[metric][pair_key] = {
                'static_mean': static_mean,
                'static_std': static_std,
                'static_n': len(static_diffs),
                'walk_mean': walk_mean,
                'walk_std': walk_std,
                'walk_n': len(walk_diffs),
                'ks_stat': ks_stat,
                'ks_pvalue': ks_pvalue,
                'mw_stat': mw_stat,
                'mw_pvalue': mw_pvalue,
                'tt_stat': tt_stat,
                'tt_pvalue': tt_pvalue,
                'cohens_d': cohens_d
            }
    
    return stats_results


def aggregate_statistics(results: Dict, pair_stats: Dict) -> Dict:
    """
    Aggregate all pairs together for overall comparison.
    """
    agg_results = {}
    
    for metric in results['static'].keys():
        # Combine all pairs
        all_static = []
        all_walk = []
        
        for pair_key in results['static'][metric].keys():
            all_static.extend(results['static'][metric][pair_key])
            all_walk.extend(results['walk'][metric][pair_key])
        
        all_static = np.array(all_static)
        all_walk = np.array(all_walk)
        
        if len(all_static) < 5 or len(all_walk) < 5:
            continue
        
        # Statistics on aggregated data
        static_mean = np.mean(all_static)
        static_std = np.std(all_static)
        walk_mean = np.mean(all_walk)
        walk_std = np.std(all_walk)
        
        # Statistical tests
        ks_result = stats.ks_2samp(all_static, all_walk)
        mw_result = stats.mannwhitneyu(all_static, all_walk, alternative='two-sided')
        tt_result = stats.ttest_ind(all_static, all_walk, equal_var=False)
        
        pooled_std = np.sqrt((static_std**2 + walk_std**2) / 2)
        cohens_d = (walk_mean - static_mean) / pooled_std if pooled_std > 0 else 0
        
        agg_results[metric] = {
            'static_mean': static_mean,
            'static_std': static_std,
            'static_n': len(all_static),
            'walk_mean': walk_mean,
            'walk_std': walk_std,
            'walk_n': len(all_walk),
            'ks_stat': float(ks_result[0]),  # type: ignore[arg-type]
            'ks_pvalue': float(ks_result[1]),  # type: ignore[arg-type]
            'mw_stat': float(mw_result[0]),  # type: ignore[arg-type]
            'mw_pvalue': float(mw_result[1]),  # type: ignore[arg-type]
            'tt_stat': float(tt_result[0]),  # type: ignore[arg-type]
            'tt_pvalue': float(tt_result[1]),  # type: ignore[arg-type]
            'cohens_d': cohens_d,
            'all_static': all_static,
            'all_walk': all_walk
        }
    
    return agg_results


def print_results(agg_results: Dict, pair_stats: Dict, alpha: float = 0.05) -> List[str]:
    """
    Print and return formatted results.
    """
    lines = []
    
    # Print aggregated results
    lines.append("\n" + "=" * 70)
    lines.append("AGGREGATED RESULTS (All Pairs Combined)")
    lines.append("=" * 70)
    
    for metric, results in agg_results.items():
        lines.append(f"\n--- {metric.upper()} ---")
        lines.append(f"Static transitions: n={results['static_n']}, mean={results['static_mean']:.4f}, std={results['static_std']:.4f}")
        lines.append(f"Walk transitions:   n={results['walk_n']}, mean={results['walk_mean']:.4f}, std={results['walk_std']:.4f}")
        
        lines.append(f"\nStatistical Tests (α = {alpha}):")
        ks_sig = "SIGNIFICANT" if results['ks_pvalue'] < alpha else "not significant"
        mw_sig = "SIGNIFICANT" if results['mw_pvalue'] < alpha else "not significant"
        tt_sig = "SIGNIFICANT" if results['tt_pvalue'] < alpha else "not significant"
        
        lines.append(f"  KS test: D={results['ks_stat']:.4f}, p={results['ks_pvalue']:.4e} ({ks_sig})")
        lines.append(f"  Mann-Whitney U: U={results['mw_stat']:.1f}, p={results['mw_pvalue']:.4e} ({mw_sig})")
        lines.append(f"  Welch's t-test: t={results['tt_stat']:.4f}, p={results['tt_pvalue']:.4e} ({tt_sig})")
        
        d = abs(results['cohens_d'])
        effect = "negligible" if d < 0.2 else ("small" if d < 0.5 else ("medium" if d < 0.8 else "large"))
        lines.append(f"  Cohen's d: {results['cohens_d']:.4f} ({effect} effect)")
        
        sig_count = sum([results['ks_pvalue'] < alpha, results['mw_pvalue'] < alpha, results['tt_pvalue'] < alpha])
        if sig_count >= 2:
            lines.append(f"\n  CONCLUSION: Distributions are SIGNIFICANTLY DIFFERENT")
        else:
            lines.append(f"\n  CONCLUSION: Distributions are NOT significantly different")
    
    # Print per-pair summary
    lines.append("\n" + "=" * 70)
    lines.append("PER-PAIR SUMMARY")
    lines.append("=" * 70)
    
    for metric in pair_stats.keys():
        lines.append(f"\n--- {metric.upper()} ---")
        lines.append(f"{'Pair':<10} {'Static(n,μ,σ)':<25} {'Walk(n,μ,σ)':<25} {'KS p-value':<12} {'Sig?':<5}")
        lines.append("-" * 80)
        
        for pair_key, stats in pair_stats[metric].items():
            static_str = f"({stats['static_n']}, {stats['static_mean']:.3f}, {stats['static_std']:.3f})"
            walk_str = f"({stats['walk_n']}, {stats['walk_mean']:.3f}, {stats['walk_std']:.3f})"
            sig = "YES" if stats['ks_pvalue'] < alpha else "no"
            lines.append(f"{pair_key:<10} {static_str:<25} {walk_str:<25} {stats['ks_pvalue']:.2e}  {sig}")
    
    return lines


def create_visualizations(agg_results: Dict, transition_data: Dict, output_dir: str):
    """
    Create visualizations comparing static vs walk transition distributions.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    metrics = list(agg_results.keys())
    n_metrics = len(metrics)
    
    # Figure 1: Distribution comparison (aggregated)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for i, metric in enumerate(metrics):
        if i >= len(axes):
            break
            
        ax = axes[i]
        static = agg_results[metric]['all_static']
        walk = agg_results[metric]['all_walk']
        
        # Histogram comparison
        bins = np.linspace(min(static.min(), walk.min()), max(static.max(), walk.max()), 30)
        ax.hist(static, bins=bins, alpha=0.6, label=f'Static (n={len(static)})', density=True, color='blue')
        ax.hist(walk, bins=bins, alpha=0.6, label=f'Walk (n={len(walk)})', density=True, color='orange')
        ax.set_xlabel(f'{metric} Difference (dB)')
        ax.set_ylabel('Density')
        ax.set_title(f'{metric}: Static vs Walk Transitions')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Add p-value annotation
        p_val = agg_results[metric]['ks_pvalue']
        sig_text = f"KS p={p_val:.2e}"
        ax.annotate(sig_text, xy=(0.98, 0.98), xycoords='axes fraction', 
                    ha='right', va='top', fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    for i in range(len(metrics), len(axes)):
        axes[i].set_visible(False)
    
    plt.suptitle('CSI Transition Differences: Static vs Random Walk\n(Same A→B pairs compared)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'distribution_comparison.png'), dpi=150)
    plt.close()
    
    # Figure 2: Box plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for i, metric in enumerate(metrics):
        if i >= len(axes):
            break
            
        ax = axes[i]
        static = agg_results[metric]['all_static']
        walk = agg_results[metric]['all_walk']
        
        bp = ax.boxplot([static, walk], tick_labels=['Static', 'Walk'])
        ax.set_ylabel(f'{metric} Difference')
        ax.set_title(f'{metric}')
        ax.grid(True, alpha=0.3)
        
        # Add significance marker
        p_val = agg_results[metric]['ks_pvalue']
        sig_marker = '***' if p_val < 0.001 else ('**' if p_val < 0.01 else ('*' if p_val < 0.05 else 'ns'))
        y_max = max(static.max(), walk.max())
        ax.annotate(sig_marker, xy=(1.5, y_max * 1.05), ha='center', fontsize=14, fontweight='bold')
    
    for i in range(len(metrics), len(axes)):
        axes[i].set_visible(False)
    
    plt.suptitle('Box Plot Comparison (*** p<0.001, ** p<0.01, * p<0.05, ns: not significant)', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'boxplot_comparison.png'), dpi=150)
    plt.close()
    
    # Figure 3: Per-pair comparison for RSS
    if 'RSS_wb' in transition_data['static']:
        n_pairs = len(transition_data['static']['RSS_wb'])
        fig, axes = plt.subplots(3, 4, figsize=(16, 12))
        axes = axes.flatten()
        
        for i, pair_key in enumerate(transition_data['static']['RSS_wb'].keys()):
            if i >= len(axes):
                break
            
            ax = axes[i]
            static = transition_data['static']['RSS_wb'][pair_key]
            walk = transition_data['walk']['RSS_wb'][pair_key]
            
            if len(static) > 0 and len(walk) > 0:
                bins = np.linspace(min(static.min(), walk.min()), max(static.max(), walk.max()), 20)
                ax.hist(static, bins=bins, alpha=0.6, label='Static', density=True)
                ax.hist(walk, bins=bins, alpha=0.6, label='Walk', density=True)
            
            ax.set_title(f'Pair {pair_key}')
            ax.set_xlabel('RSS Diff (dB)')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
        
        for i in range(n_pairs, len(axes)):
            axes[i].set_visible(False)
        
        plt.suptitle('RSS Differences by Adjacent Pair: Static vs Walk', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'per_pair_rss.png'), dpi=150)
        plt.close()
    
    # Figure 4: Summary bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(metrics))
    width = 0.35
    
    static_means = [agg_results[m]['static_mean'] for m in metrics]
    walk_means = [agg_results[m]['walk_mean'] for m in metrics]
    static_stds = [agg_results[m]['static_std'] for m in metrics]
    walk_stds = [agg_results[m]['walk_std'] for m in metrics]
    
    bars1 = ax.bar(x - width/2, static_means, width, yerr=static_stds, label='Static', capsize=5)
    bars2 = ax.bar(x + width/2, walk_means, width, yerr=walk_stds, label='Walk', capsize=5)
    
    ax.set_xlabel('Metric')
    ax.set_ylabel('Mean Difference')
    ax.set_title('Mean Transition Differences: Static vs Walk')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'mean_comparison.png'), dpi=150)
    plt.close()
    
    print(f"Visualizations saved to: {output_dir}")


def generate_report(agg_results: Dict, result_lines: List[str], output_dir: str):
    """
    Generate a comprehensive analysis report.
    """
    report_path = os.path.join(output_dir, 'analysis_report.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("STATIC vs RANDOM WALK CSI TRANSITION ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("EXPERIMENT DESCRIPTION\n")
        f.write("-" * 40 + "\n")
        f.write("This analysis compares CSI TRANSITION DIFFERENCES between:\n")
        f.write("1. Static: CSI(B) - CSI(A) when both A and B are measured statically\n")
        f.write("2. Walk: CSI(step N+1) - CSI(step N) when UE walks from A to B\n\n")
        f.write("Research Question: Is the CSI change during a walk transition (A→B)\n")
        f.write("the same as the CSI difference between static measurements at A and B?\n\n")
        
        f.write("ANALYSIS RESULTS\n")
        f.write("-" * 40 + "\n")
        for line in result_lines:
            f.write(line + "\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("INTERPRETATION\n")
        f.write("=" * 80 + "\n\n")
        
        n_metrics = len(agg_results)
        n_sig = sum(1 for m, r in agg_results.items() if r['ks_pvalue'] < 0.05)
        
        if n_sig == 0:
            f.write("MAIN FINDING: No significant differences detected.\n\n")
            f.write("The distribution of CSI changes during walk transitions matches\n")
            f.write("the distribution of CSI differences between static positions.\n")
            f.write("This suggests that the CSI change when walking A→B is the same\n")
            f.write("as the difference between static CSI at A and B.\n")
        elif n_sig == n_metrics:
            f.write("MAIN FINDING: Significant differences detected for ALL metrics.\n\n")
            f.write("The distribution of CSI changes during walk transitions differs\n")
            f.write("from static position differences. This could indicate:\n")
            f.write("- Temporal channel correlation during movement\n")
            f.write("- Doppler effects from UE motion\n")
            f.write("- Different multipath patterns during transitions\n")
        else:
            f.write(f"MAIN FINDING: Mixed results - {n_sig}/{n_metrics} metrics differ.\n\n")
            f.write("Some metrics show different distributions while others don't.\n")
    
    print(f"Report saved to: {report_path}")


def main():
    """
    Main analysis pipeline.
    """
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    results_dir = project_root / "results"
    output_dir = script_dir / "analysis_output"
    
    print("=" * 60)
    print("Static vs Random Walk CSI Transition Analysis - Experiment 13")
    print("=" * 60)
    print("\nComparing: CSI differences for A→B transitions")
    print("  Static: CSI(B) - CSI(A) from 100 repetitions")
    print("  Walk: CSI change when walking from A to B")
    
    try:
        # Load data
        print("\n[1/5] Loading MATLAB data...")
        static_data, walk_data = load_matlab_data(str(results_dir))
        
        # Extract transition data
        print("\n[2/5] Extracting transition differences...")
        transition_data = extract_transition_data(static_data, walk_data)
        
        # Compute per-pair statistics
        print("\n[3/5] Computing per-pair statistics...")
        pair_stats = compute_pair_statistics(transition_data)
        
        # Aggregate statistics
        print("\n[4/5] Computing aggregate statistics...")
        agg_results = aggregate_statistics(transition_data, pair_stats)
        
        # Print results
        result_lines = print_results(agg_results, pair_stats)
        for line in result_lines:
            print(line)
        
        # Visualizations
        print("\n[5/5] Creating visualizations...")
        create_visualizations(agg_results, transition_data, str(output_dir))
        generate_report(agg_results, result_lines, str(output_dir))
        
        print("\n" + "=" * 60)
        print("Analysis complete!")
        print(f"Output directory: {output_dir}")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease run the MATLAB experiments first:")
        print("  1. Run exp13a_static_grid.m")
        print("  2. Run exp13b_random_walk.m")
        print("Then run this analysis script.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
