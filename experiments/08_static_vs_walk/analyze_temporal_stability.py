#!/usr/bin/env python3
"""
Analyze Temporal Stability Results - Experiment 13c
====================================================

This script analyzes CSI temporal stability for a stationary UE.
Creates detailed plots showing how stable the channel is over time.

Output: Plots saved to experiments/08_static_vs_walk/exp13c_plots/
"""

import os
import sys
import numpy as np
import h5py
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
from scipy import stats as scipy_stats
from typing import Dict, Any, Tuple


def load_mat_v73(filepath: str) -> Dict[str, Any]:
    """Load MATLAB v7.3 file using h5py."""
    data = {}
    with h5py.File(filepath, 'r') as f:
        for key in f.keys():
            data[key] = _convert_h5_item(f[key], f)
    return data


def _convert_h5_item(item, file_ref) -> Any:
    """Recursively convert HDF5 items to Python objects."""
    if isinstance(item, h5py.Dataset):
        arr = item[()]
        if arr.dtype == np.uint16 or arr.dtype == np.uint8:
            try:
                if len(arr.shape) == 1:
                    return ''.join(chr(c) for c in arr if c != 0)
                elif len(arr.shape) == 2 and arr.shape[0] == 1:
                    return ''.join(chr(c) for c in arr[0] if c != 0)
            except:
                pass
        if len(arr.shape) >= 2:
            arr = arr.T
        if arr.size == 1:
            return arr.item()
        return np.squeeze(arr)
    elif isinstance(item, h5py.Group):
        result = {}
        for key in item.keys():
            result[key] = _convert_h5_item(item[key], file_ref)
        return result
    elif isinstance(item, h5py.Reference):
        return _convert_h5_item(file_ref[item], file_ref)
    else:
        return item


def find_latest_results(results_dir: Path) -> Path:
    """Find the most recent exp13c results directory."""
    exp13c_dirs = sorted([d for d in results_dir.glob("exp13c*") if d.is_dir()])
    if not exp13c_dirs:
        raise FileNotFoundError("No exp13c results found in " + str(results_dir))
    return exp13c_dirs[-1]


def analyze_stability(data: Dict) -> Dict:
    """Compute stability statistics for each metric."""
    metrics = data['metrics']
    results = {}
    
    metric_names = ['RSS_wb', 'SINR_wb', 'CQI_wb', 'path_loss', 'rms_delay_spread']
    
    for name in metric_names:
        if name in metrics:
            vals = np.array(metrics[name]).flatten()
            
            # Basic statistics
            mean_val = np.mean(vals)
            std_val = np.std(vals)
            min_val = np.min(vals)
            max_val = np.max(vals)
            range_val = max_val - min_val
            cv = (std_val / abs(mean_val) * 100) if mean_val != 0 else 0
            
            # Normality test (Shapiro-Wilk)
            if len(vals) >= 3:
                shapiro_stat, shapiro_p = scipy_stats.shapiro(vals[:min(50, len(vals))])
            else:
                shapiro_stat, shapiro_p = np.nan, np.nan
            
            # Autocorrelation (lag 1)
            if len(vals) > 1:
                autocorr = np.corrcoef(vals[:-1], vals[1:])[0, 1]
            else:
                autocorr = np.nan
            
            results[name] = {
                'values': vals,
                'mean': mean_val,
                'std': std_val,
                'min': min_val,
                'max': max_val,
                'range': range_val,
                'cv': cv,
                'shapiro_stat': shapiro_stat,
                'shapiro_p': shapiro_p,
                'autocorr_lag1': autocorr
            }
    
    return results


def create_plots(data: Dict, stats: Dict, output_dir: Path):
    """Create comprehensive temporal stability plots."""
    os.makedirs(output_dir, exist_ok=True)
    
    metrics = data['metrics']
    time = np.array(metrics.get('time', np.arange(len(stats['RSS_wb']['values'])))).flatten()
    
    config = data.get('config', {})
    ue_pos = config.get('ue_position', [0, 0, 0])
    if isinstance(ue_pos, np.ndarray):
        ue_pos = ue_pos.flatten()
    scenario = config.get('scenario', 'Unknown')
    
    # Set style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # ===========================================
    # Figure 1: Time series of all metrics
    # ===========================================
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    
    plot_configs = [
        ('RSS_wb', 'RSS (dBm)', 'blue'),
        ('SINR_wb', 'SINR (dB)', 'green'),
        ('path_loss', 'Path Loss (dB)', 'red'),
        ('CQI_wb', 'CQI', 'purple'),
        ('rms_delay_spread', 'RMS Delay Spread (ns)', 'orange'),
    ]
    
    for idx, (metric, ylabel, color) in enumerate(plot_configs):
        if idx >= 6:
            break
        ax = axes.flatten()[idx]
        if metric in stats:
            s = stats[metric]
            vals = s['values']
            
            ax.plot(time, vals, color=color, linewidth=1, alpha=0.8)
            ax.axhline(s['mean'], color='black', linestyle='--', linewidth=1.5, label=f'Mean: {s["mean"]:.3f}')
            ax.fill_between(time, s['mean'] - s['std'], s['mean'] + s['std'], 
                           alpha=0.2, color=color, label=f'±1σ: {s["std"]:.4f}')
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(ylabel)
            ax.set_title(f'{metric}: μ={s["mean"]:.3f}, σ={s["std"]:.4f}, CV={s["cv"]:.2f}%')
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(True, alpha=0.3)
    
    # Hide unused subplot
    axes.flatten()[5].set_visible(False)
    
    fig.suptitle(f'Temporal Stability: Stationary UE at [{ue_pos[0]:.0f}, {ue_pos[1]:.0f}] m\n({scenario})', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'temporal_timeseries.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # ===========================================
    # Figure 2: Distributions (histograms + KDE)
    # ===========================================
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    
    for idx, (metric, ylabel, color) in enumerate(plot_configs):
        if idx >= 6:
            break
        ax = axes.flatten()[idx]
        if metric in stats:
            s = stats[metric]
            vals = s['values']
            
            # Histogram with KDE
            ax.hist(vals, bins=20, density=True, alpha=0.6, color=color, edgecolor='black')
            
            # KDE
            if len(np.unique(vals)) > 1:
                kde_x = np.linspace(vals.min(), vals.max(), 100)
                kde = scipy_stats.gaussian_kde(vals)
                ax.plot(kde_x, kde(kde_x), color='black', linewidth=2, label='KDE')
            
            # Normal distribution overlay
            if s['std'] > 0:
                norm_x = np.linspace(vals.min(), vals.max(), 100)
                norm_y = scipy_stats.norm.pdf(norm_x, s['mean'], s['std'])
                ax.plot(norm_x, norm_y, 'r--', linewidth=1.5, label='Normal fit')
            
            ax.axvline(s['mean'], color='black', linestyle='-', linewidth=2)
            ax.set_xlabel(ylabel)
            ax.set_ylabel('Density')
            ax.set_title(f'{metric}\nShapiro p={s["shapiro_p"]:.4f}')
            ax.legend(fontsize=8)
    
    axes.flatten()[5].set_visible(False)
    
    fig.suptitle('Distribution of CSI Metrics Over Time', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'temporal_distributions.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # ===========================================
    # Figure 3: Stability summary (bar chart)
    # ===========================================
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    
    # Standard deviation comparison
    ax = axes[0]
    metric_names = [m for m, _, _ in plot_configs if m in stats]
    stds = [stats[m]['std'] for m in metric_names]
    colors = ['blue', 'green', 'red', 'purple', 'orange'][:len(metric_names)]
    bars = ax.bar(metric_names, stds, color=colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Standard Deviation')
    ax.set_title('Temporal Variability (σ)')
    ax.tick_params(axis='x', rotation=45)
    for bar, std in zip(bars, stds):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{std:.4f}', 
                ha='center', va='bottom', fontsize=9)
    
    # Coefficient of variation
    ax = axes[1]
    cvs = [stats[m]['cv'] for m in metric_names]
    bars = ax.bar(metric_names, cvs, color=colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Coefficient of Variation (%)')
    ax.set_title('Relative Variability (CV%)')
    ax.tick_params(axis='x', rotation=45)
    for bar, cv in zip(bars, cvs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{cv:.2f}%', 
                ha='center', va='bottom', fontsize=9)
    
    # Autocorrelation
    ax = axes[2]
    autocorrs = [stats[m]['autocorr_lag1'] for m in metric_names]
    bars = ax.bar(metric_names, autocorrs, color=colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Autocorrelation (lag=1)')
    ax.set_title('Temporal Correlation')
    ax.axhline(0, color='black', linestyle='-', linewidth=0.5)
    ax.set_ylim(-1, 1)
    ax.tick_params(axis='x', rotation=45)
    for bar, ac in zip(bars, autocorrs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{ac:.3f}', 
                ha='center', va='bottom' if ac >= 0 else 'top', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'temporal_stability_summary.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # ===========================================
    # Figure 4: RSS focused analysis
    # ===========================================
    if 'RSS_wb' in stats:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        rss = stats['RSS_wb']['values']
        
        # Time series with rolling mean
        ax = axes[0, 0]
        ax.plot(time, rss, 'b-', alpha=0.5, label='RSS')
        window = min(10, len(rss)//5)
        if window > 1:
            rolling_mean = np.convolve(rss, np.ones(window)/window, mode='valid')
            ax.plot(time[window-1:], rolling_mean, 'r-', linewidth=2, label=f'Rolling mean (w={window})')
        ax.axhline(stats['RSS_wb']['mean'], color='black', linestyle='--', label='Overall mean')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('RSS (dBm)')
        ax.set_title('RSS Over Time with Rolling Mean')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Difference from mean
        ax = axes[0, 1]
        diff = rss - stats['RSS_wb']['mean']
        ax.plot(time, diff, 'g-', linewidth=1)
        ax.axhline(0, color='black', linestyle='-')
        ax.axhline(stats['RSS_wb']['std'], color='red', linestyle='--', label='+1σ')
        ax.axhline(-stats['RSS_wb']['std'], color='red', linestyle='--', label='-1σ')
        ax.fill_between(time, -stats['RSS_wb']['std'], stats['RSS_wb']['std'], alpha=0.2, color='red')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('RSS - Mean (dB)')
        ax.set_title('Deviation from Mean')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Autocorrelation function
        ax = axes[1, 0]
        max_lag = min(30, len(rss)//3)
        acf = [1.0]  # lag 0
        for lag in range(1, max_lag):
            acf.append(np.corrcoef(rss[:-lag], rss[lag:])[0, 1])
        ax.bar(range(max_lag), acf, color='blue', alpha=0.7)
        ax.axhline(0, color='black', linewidth=0.5)
        ax.axhline(1.96/np.sqrt(len(rss)), color='red', linestyle='--', label='95% CI')
        ax.axhline(-1.96/np.sqrt(len(rss)), color='red', linestyle='--')
        ax.set_xlabel('Lag')
        ax.set_ylabel('Autocorrelation')
        ax.set_title('Autocorrelation Function')
        ax.legend()
        
        # Q-Q plot
        ax = axes[1, 1]
        scipy_stats.probplot(rss, dist="norm", plot=ax)
        ax.set_title('Q-Q Plot (Normal)')
        ax.grid(True, alpha=0.3)
        
        fig.suptitle('RSS Temporal Stability Analysis', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_dir / 'rss_detailed_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
    
    # ===========================================
    # Figure 5: Comparison with expected stability
    # ===========================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create comparison data
    metric_names = ['RSS_wb', 'SINR_wb', 'path_loss']
    measured_std = [stats[m]['std'] for m in metric_names if m in stats]
    expected_std = [0.5, 0.5, 0.5]  # Expected for stable channel
    threshold_std = [1.0, 1.0, 1.0]  # Threshold for "unstable"
    
    x = np.arange(len(metric_names))
    width = 0.25
    
    bars1 = ax.bar(x - width, measured_std, width, label='Measured σ', color='blue', alpha=0.7)
    bars2 = ax.bar(x, expected_std, width, label='Expected σ (stable)', color='green', alpha=0.7)
    bars3 = ax.bar(x + width, threshold_std, width, label='Threshold σ (unstable)', color='red', alpha=0.7)
    
    ax.set_ylabel('Standard Deviation (dB)')
    ax.set_title('Stability Assessment: Measured vs Expected')
    ax.set_xticks(x)
    ax.set_xticklabels(metric_names)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add assessment text
    for i, (meas, exp, thresh) in enumerate(zip(measured_std, expected_std, threshold_std)):
        if meas <= exp:
            assessment = "✓ Stable"
            color = 'green'
        elif meas <= thresh:
            assessment = "~ OK"
            color = 'orange'
        else:
            assessment = "⚠ Unstable"
            color = 'red'
        ax.annotate(assessment, xy=(i, max(meas, exp, thresh) + 0.1), 
                   ha='center', fontsize=10, color=color, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'stability_assessment.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Plots saved to: {output_dir}")


def generate_report(stats: Dict, output_dir: Path):
    """Generate a text report of the stability analysis."""
    report_path = output_dir / 'stability_report.txt'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("TEMPORAL STABILITY ANALYSIS REPORT - Experiment 13c\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'Metric':<20} {'Mean':>12} {'Std':>12} {'CV(%)':>10} {'Autocorr':>10}\n")
        f.write("-" * 70 + "\n")
        
        for metric, s in stats.items():
            f.write(f"{metric:<20} {s['mean']:>12.4f} {s['std']:>12.4f} {s['cv']:>10.2f} {s['autocorr_lag1']:>10.3f}\n")
        
        f.write("\n" + "=" * 70 + "\n")
        f.write("STABILITY ASSESSMENT\n")
        f.write("=" * 70 + "\n\n")
        
        # Assess each metric
        assessments = []
        for metric in ['RSS_wb', 'SINR_wb', 'path_loss']:
            if metric in stats:
                std = stats[metric]['std']
                if std < 0.5:
                    assessments.append(f"✓ {metric}: STABLE (σ = {std:.4f} dB)")
                elif std < 1.0:
                    assessments.append(f"~ {metric}: ACCEPTABLE (σ = {std:.4f} dB)")
                else:
                    assessments.append(f"⚠ {metric}: HIGH VARIANCE (σ = {std:.4f} dB)")
        
        for a in assessments:
            f.write(a + "\n")
        
        f.write("\n" + "-" * 70 + "\n")
        f.write("INTERPRETATION:\n")
        f.write("-" * 70 + "\n")
        
        rss_std = stats.get('RSS_wb', {}).get('std', 0)
        if rss_std < 0.5:
            f.write("The channel is highly stable for a stationary UE.\n")
            f.write("QuaDRiGa's temporal modeling is working correctly.\n")
            f.write("Small variations are due to numerical precision and small-scale fading.\n")
        elif rss_std < 1.0:
            f.write("The channel shows moderate stability.\n")
            f.write("Some temporal variation exists, possibly due to:\n")
            f.write("  - Small-scale fading in NLOS scenario\n")
            f.write("  - Track-based generation introducing minor variations\n")
        else:
            f.write("WARNING: The channel shows higher than expected variation.\n")
            f.write("Possible causes:\n")
            f.write("  - Fallback to independent samples (no temporal correlation)\n")
            f.write("  - NLOS scenario with significant multipath variation\n")
            f.write("  - Check QuaDRiGa track configuration\n")
    
    print(f"Report saved to: {report_path}")


def main():
    """Main analysis pipeline."""
    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    results_dir = project_root / "results"
    output_dir = script_dir / "exp13c_plots"
    
    print("=" * 60)
    print("Temporal Stability Analysis - Experiment 13c")
    print("=" * 60)
    
    try:
        # Find latest results
        print("\n[1/4] Finding results...")
        results_path = find_latest_results(results_dir)
        print(f"  Using: {results_path}")
        
        # Load data
        print("\n[2/4] Loading data...")
        mat_file = results_path / "temporal_stability_results.mat"
        data = load_mat_v73(str(mat_file))
        print(f"  Loaded {len(data)} fields")
        
        # Analyze stability
        print("\n[3/4] Analyzing stability...")
        stats = analyze_stability(data)
        
        # Print summary
        print("\n" + "=" * 60)
        print("STABILITY SUMMARY")
        print("=" * 60)
        print(f"{'Metric':<20} {'Mean':>12} {'Std':>12} {'CV(%)':>10}")
        print("-" * 60)
        for metric, s in stats.items():
            print(f"{metric:<20} {s['mean']:>12.4f} {s['std']:>12.4f} {s['cv']:>10.2f}")
        
        # Create plots
        print("\n[4/4] Creating plots...")
        create_plots(data, stats, output_dir)
        generate_report(stats, output_dir)
        
        print("\n" + "=" * 60)
        print("Analysis complete!")
        print(f"Output directory: {output_dir}")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease run exp13c_temporal_stability.m first in MATLAB.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
