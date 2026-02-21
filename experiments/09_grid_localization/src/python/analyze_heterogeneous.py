"""
Heterogeneous Environment Analysis

Runs the existing localization pipelines on Voronoi-based heterogeneous data
and produces a comparison report showing how scenario diversity affects
localization performance.

Usage:
    python analyze_heterogeneous.py --data-dir <voronoi_sim_data_dir>
    python analyze_heterogeneous.py --data-dir results/grid_localization/grid_7x7/sim_data_voronoi_...

This script:
1. Loads the voronoi simulation data
2. Analyzes heterogeneity metrics (RSS range, per-area statistics)
3. Runs classification pipeline (Gaussian static, transition, Random Forest)
4. Runs regression pipeline (3D position error with history)
5. Generates combined comparison report + visualizations
"""

import argparse
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.io import loadmat
from datetime import datetime
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))
from read_jsonc import read_jsonc


def load_voronoi_data(data_dir):
    """Load simulation data and extract heterogeneity info"""
    data_dir = Path(data_dir)
    sim_file = data_dir / 'simulation_data.mat'

    if not sim_file.exists():
        raise FileNotFoundError(f"Simulation data not found: {sim_file}")

    print(f"Loading data from: {sim_file}")
    data = loadmat(str(sim_file), squeeze_me=True, struct_as_record=False)

    # Load config
    config_file = data_dir / 'data_generation_config.jsonc'
    if not config_file.exists():
        config_file = data_dir / 'config.jsonc'
    if not config_file.exists():
        config_file = data_dir / 'config.json'
    config = read_jsonc(config_file) if config_file.suffix == '.jsonc' else json.load(open(config_file, encoding='utf-8'))

    result = {
        'metrics': data['metrics'],
        'walk_path': data['walk_path'],
        'config': data['config'],
        'config_json': config,
        'data_dir': data_dir,
    }

    # Check for Voronoi cell assignments
    if hasattr(data['walk_path'], 'voronoi_cell_idx'):
        result['voronoi_cell_idx'] = data['walk_path'].voronoi_cell_idx
        result['voronoi_names'] = data['walk_path'].voronoi_names
        result['voronoi_scenarios'] = data['walk_path'].voronoi_scenarios
        result['voronoi_centers'] = data['walk_path'].voronoi_centers
        result['is_voronoi'] = True
    else:
        result['is_voronoi'] = False

    n_samples = len(data['metrics'].rss_wb)
    print(f"[OK] Loaded {n_samples} samples")
    if result['is_voronoi']:
        n_cells = len(np.unique(result['voronoi_cell_idx']))
        print(f"     Voronoi cells: {n_cells}")
    else:
        print(f"     Homogeneous scenario (no Voronoi cells)")

    return result


def analyze_heterogeneity(data, output_dir):
    """Compute and print heterogeneity statistics"""
    print(f"\n{'='*60}")
    print("HETEROGENEITY ANALYSIS")
    print(f"{'='*60}")

    rss = data['metrics'].rss_wb
    sinr = data['metrics'].sinr_wb

    # Overall statistics
    rss_range = np.ptp(rss)
    rss_std = np.std(rss)
    sinr_range = np.ptp(sinr)

    print(f"\nOverall Statistics:")
    print(f"  RSS:  {np.mean(rss):.1f} ± {rss_std:.1f} dBm  (range: {rss_range:.1f} dB)")
    print(f"  SINR: {np.mean(sinr):.1f} ± {np.std(sinr):.1f} dB  (range: {sinr_range:.1f} dB)")

    report_lines = []
    report_lines.append(f"## Heterogeneity Metrics\n")
    report_lines.append(f"| Metric | Mean | Std | Range |")
    report_lines.append(f"|:-------|:-----|:----|:------|")
    report_lines.append(f"| RSS (dBm) | {np.mean(rss):.1f} | {rss_std:.1f} | {rss_range:.1f} |")
    report_lines.append(f"| SINR (dB) | {np.mean(sinr):.1f} | {np.std(sinr):.1f} | {sinr_range:.1f} |")

    # Per-area statistics
    if data['is_voronoi']:
        cell_idx = data['voronoi_cell_idx']
        unique_cells = np.unique(cell_idx)

        # Convert voronoi_names/scenarios
        if hasattr(data['voronoi_names'], '__iter__') and not isinstance(data['voronoi_names'], str):
            names = [str(n) for n in data['voronoi_names']]
            scenarios = [str(s) for s in data['voronoi_scenarios']]
        else:
            names = [str(data['voronoi_names'])]
            scenarios = [str(data['voronoi_scenarios'])]

        print(f"\nPer-Area Statistics:")
        report_lines.append(f"\n### Per-Area Breakdown\n")
        report_lines.append(f"| Area | Type | Scenario | Samples | RSS Mean±Std | SINR Mean±Std |")
        report_lines.append(f"|:-----|:-----|:---------|:--------|:-------------|:--------------|")

        for c in unique_cells:
            c = int(c)
            mask = cell_idx == c
            n_in_area = np.sum(mask)
            rss_area = rss[mask]
            sinr_area = sinr[mask]

            name = names[c - 1] if c <= len(names) else f"Area_{c}"
            scenario = scenarios[c - 1] if c <= len(scenarios) else "unknown"

            print(f"  Cell {c} ({name}, {scenario}):")
            print(f"    Samples: {n_in_area}")
            print(f"    RSS:  {np.mean(rss_area):.1f} ± {np.std(rss_area):.1f} dBm")
            print(f"    SINR: {np.mean(sinr_area):.1f} ± {np.std(sinr_area):.1f} dB")

            report_lines.append(
                f"| {c} | {name} | {scenario.split('_')[-1]} | {n_in_area} | "
                f"{np.mean(rss_area):.1f} ± {np.std(rss_area):.1f} | "
                f"{np.mean(sinr_area):.1f} ± {np.std(sinr_area):.1f} |"
            )

        # Inter-area RSS separation
        area_means = [np.mean(rss[cell_idx == c]) for c in unique_cells]
        inter_area_spread = np.ptp(area_means)
        print(f"\n  Inter-area RSS spread: {inter_area_spread:.1f} dB")
        report_lines.append(f"\n**Inter-area RSS spread:** {inter_area_spread:.1f} dB")

    # Create heterogeneity visualization
    fig = create_heterogeneity_plot(data)
    fig.savefig(output_dir / 'heterogeneity_analysis.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\n[OK] Heterogeneity plot saved")

    return '\n'.join(report_lines), rss_range


def create_heterogeneity_plot(data):
    """Create figure showing spatial distribution of metrics"""
    positions = data['walk_path'].positions_jittered
    rss = data['metrics'].rss_wb
    sinr = data['metrics'].sinr_wb

    n_cols = 3 if data['is_voronoi'] else 2
    fig, axes = plt.subplots(1, n_cols, figsize=(6 * n_cols, 5))

    # RSS spatial distribution
    ax = axes[0]
    sc = ax.scatter(positions[:, 0], positions[:, 1], c=rss, s=3, cmap='RdYlGn', alpha=0.5)
    plt.colorbar(sc, ax=ax, label='RSS (dBm)')
    ax.set_xlabel('X [m]')
    ax.set_ylabel('Y [m]')
    ax.set_title('RSS Spatial Distribution')
    ax.set_aspect('equal')

    # SINR spatial distribution
    ax = axes[1]
    sc = ax.scatter(positions[:, 0], positions[:, 1], c=sinr, s=3, cmap='RdYlGn', alpha=0.5)
    plt.colorbar(sc, ax=ax, label='SINR (dB)')
    ax.set_xlabel('X [m]')
    ax.set_ylabel('Y [m]')
    ax.set_title('SINR Spatial Distribution')
    ax.set_aspect('equal')

    # Voronoi cell assignment
    if data['is_voronoi']:
        ax = axes[2]
        cell_idx = data['voronoi_cell_idx']
        sc = ax.scatter(positions[:, 0], positions[:, 1], c=cell_idx, s=3,
                       cmap='tab10', alpha=0.5)
        plt.colorbar(sc, ax=ax, label='Cell ID')

        # Plot cell centers
        if hasattr(data['voronoi_centers'], 'shape'):
            centers = data['voronoi_centers']
            if centers.ndim == 2:
                ax.scatter(centers[:, 0], centers[:, 1], c='red', s=200,
                          marker='*', edgecolors='black', linewidths=1.5, zorder=5)

        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        ax.set_title('Voronoi Cell Assignment')
        ax.set_aspect('equal')

    fig.suptitle('Heterogeneity Analysis', fontsize=14, fontweight='bold')
    fig.tight_layout()
    return fig


def run_classification(data_dir, split_method='temporal', max_history=3, n_jobs=4, max_depth=30):
    """Run existing classification pipeline and capture results"""
    print(f"\n{'='*60}")
    print("CLASSIFICATION PIPELINE")
    print(f"{'='*60}")

    import subprocess
    script = Path(__file__).parent / 'localization_pipeline.py'
    cmd = [
        sys.executable, str(script),
        '--data-dir', str(data_dir),
        '--split-method', split_method,
        '--model', 'random_forest',
        '--max-history', str(max_history),
        '--n-jobs', str(n_jobs),
        '--max-depth', str(max_depth),
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent.parent.parent))

    if result.returncode != 0:
        print(f"[ERROR] Classification pipeline failed:")
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
        return None

    print(result.stdout)
    return result.stdout


def run_regression(data_dir, split_method='temporal', max_history=3, n_estimators=100, max_depth=None, 
                  min_samples_split=2, min_samples_leaf=1):
    """Run existing regression pipeline and capture results"""
    print(f"\n{'='*60}")
    print("REGRESSION PIPELINE")
    print(f"{'='*60}")

    import subprocess
    script = Path(__file__).parent / 'localization_pipeline_regression.py'
    
    # Convert to absolute path
    data_dir = Path(data_dir).absolute()
    
    cmd = [
        sys.executable, str(script),
        '--data-dir', str(data_dir),
        '--split-method', split_method,
        '--max-history', str(max_history),
        '--n-estimators', str(n_estimators),
        '--min-samples-split', str(min_samples_split),
        '--min-samples-leaf', str(min_samples_leaf),
    ]
    
    if max_depth is not None:
        cmd.extend(['--max-depth', str(max_depth)])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent.parent.parent))

    if result.returncode != 0:
        print(f"[ERROR] Regression pipeline failed:")
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
        return None, None

    print(result.stdout)
    
    # Extract output directory from stdout
    output_dir = None
    for line in result.stdout.split('\n'):
        if 'Output directory:' in line:
            output_dir_str = line.split('Output directory:')[1].strip()
            # Convert to absolute path (subprocess runs from project root)
            project_root = Path(__file__).parent.parent.parent.parent.parent
            output_dir = str((project_root / output_dir_str).absolute())
            break
    
    return result.stdout, output_dir


def analyze_per_cell_performance(data, regression_output_dir, output_dir):
    """Analyze regression performance broken down by Voronoi cell"""
    if not data['is_voronoi']:
        return None
    
    print(f"\n{'='*60}")
    print("PER-CELL REGRESSION ANALYSIS")
    print(f"{'='*60}")
    
    # Load regression predictions (h=0 baseline)
    regression_output_dir = Path(regression_output_dir)
    results_file = regression_output_dir / 'results_h0.npz'
    
    if not results_file.exists():
        print(f"[WARNING] Regression results not found: {results_file}")
        return None
    
    results = np.load(results_file)
    y_test = results['y_test']
    y_pred = results['y_pred']
    test_indices = results['test_indices']
    
    # Get Voronoi cell assignments for test samples
    cell_idx = data['voronoi_cell_idx']
    test_cells = cell_idx[test_indices]
    
    # Get cell names and scenarios
    if hasattr(data['voronoi_names'], '__iter__') and not isinstance(data['voronoi_names'], str):
        names = [str(n) for n in data['voronoi_names']]
        scenarios = [str(s) for s in data['voronoi_scenarios']]
    else:
        names = [str(data['voronoi_names'])]
        scenarios = [str(data['voronoi_scenarios'])]
    
    unique_cells = np.unique(test_cells)
    
    # Compute per-cell metrics
    print("\nPer-Cell Performance (h=0 baseline):")
    report_lines = []
    report_lines.append("\n## Per-Cell Regression Performance\n")
    report_lines.append("Performance breakdown by Voronoi cell (h=0 baseline):\n")
    report_lines.append("\n| Cell | Type | Scenario | Samples | Distance MAE | Azimuth MAE | Elevation MAE | 3D Position MAE |")
    report_lines.append("|:-----|:-----|:---------|:--------|:-------------|:------------|:--------------|:----------------|")
    
    for c in unique_cells:
        c = int(c)
        mask = test_cells == c
        n_in_cell = np.sum(mask)
        
        if n_in_cell == 0:
            continue
        
        # Extract predictions and ground truth for this cell
        y_test_cell = y_test[mask]
        y_pred_cell = y_pred[mask]
        
        # Compute MAE for each target
        dist_mae = np.mean(np.abs(y_test_cell[:, 0] - y_pred_cell[:, 0]))
        az_mae = np.mean(np.abs(y_test_cell[:, 1] - y_pred_cell[:, 1]))
        el_mae = np.mean(np.abs(y_test_cell[:, 2] - y_pred_cell[:, 2]))
        
        # Compute 3D position error (convert distance/azimuth/elevation to XYZ)
        # Get BS position from config_json (JSONC) instead of config (MATLAB struct)
        bs_pos = np.array(data['config_json']['base_station']['position'])
        
        # Ground truth positions
        dist_true = y_test_cell[:, 0]
        az_true = np.radians(y_test_cell[:, 1])
        el_true = np.radians(y_test_cell[:, 2])
        x_true = bs_pos[0] + dist_true * np.cos(el_true) * np.cos(az_true)
        y_true = bs_pos[1] + dist_true * np.cos(el_true) * np.sin(az_true)
        z_true = bs_pos[2] - dist_true * np.sin(el_true)
        
        # Predicted positions
        dist_pred = y_pred_cell[:, 0]
        az_pred = np.radians(y_pred_cell[:, 1])
        el_pred = np.radians(y_pred_cell[:, 2])
        x_pred = bs_pos[0] + dist_pred * np.cos(el_pred) * np.cos(az_pred)
        y_pred_cart = bs_pos[1] + dist_pred * np.cos(el_pred) * np.sin(az_pred)
        z_pred = bs_pos[2] - dist_pred * np.sin(el_pred)
        
        # 3D position error
        pos_errors = np.sqrt((x_true - x_pred)**2 + (y_true - y_pred_cart)**2 + (z_true - z_pred)**2)
        pos_mae_3d = np.mean(pos_errors)
        
        # Get area name and scenario
        name = names[c - 1] if c <= len(names) else f"Area_{c}"
        scenario = scenarios[c - 1] if c <= len(scenarios) else "unknown"
        scenario_short = scenario.split('_')[-1] if '_' in scenario else scenario
        
        print(f"\n  Cell {c} ({name}, {scenario_short}):")
        print(f"    Samples: {n_in_cell}")
        print(f"    Distance MAE: {dist_mae:.3f} m")
        print(f"    Azimuth MAE: {az_mae:.3f}°")
        print(f"    Elevation MAE: {el_mae:.3f}°")
        print(f"    3D Position MAE: {pos_mae_3d:.3f} m")
        
        report_lines.append(
            f"| {c} | {name} | {scenario_short} | {n_in_cell} | "
            f"{dist_mae:.3f} m | {az_mae:.3f}° | {el_mae:.3f}° | {pos_mae_3d:.3f} m |"
        )
    
    print(f"\n[OK] Per-cell analysis complete")
    
    return '\n'.join(report_lines)


def generate_report(output_dir, heterogeneity_report, classification_output, regression_output, rss_range, per_cell_report=None):
    """Generate combined markdown report"""
    report_file = output_dir / 'HETEROGENEOUS_ANALYSIS_REPORT.md'

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('# Heterogeneous Environment Analysis\n\n')
        f.write(f'**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write(f'---\n\n')

        # Heterogeneity section
        f.write(heterogeneity_report)
        f.write('\n\n---\n\n')

        # Validation
        f.write('## Validation\n\n')
        rss_check = '✅' if rss_range > 20 else '⚠️'
        f.write(f'- {rss_check} RSS range: {rss_range:.1f} dB (target: >20 dB)\n')
        f.write('\n---\n\n')

        # Classification results
        if classification_output:
            f.write('## Classification Results\n\n')
            f.write('```\n')
            # Extract the results portion
            lines = classification_output.split('\n')
            in_results = False
            for line in lines:
                if 'Random Forest' in line or 'Accuracy' in line or 'MAE' in line or 'history' in line.lower():
                    in_results = True
                if in_results:
                    f.write(line + '\n')
            f.write('```\n\n')

        # Regression results
        if regression_output:
            f.write('## Regression Results\n\n')
            f.write('```\n')
            lines = regression_output.split('\n')
            in_results = False
            for line in lines:
                if 'Features:' in line or 'Target' in line or 'Distance' in line or \
                   'Azimuth' in line or 'Elevation' in line or '3D Position' in line or \
                   '---' in line:
                    in_results = True
                if in_results:
                    f.write(line + '\n')
            f.write('```\n\n')

        # Per-cell breakdown
        if per_cell_report:
            f.write(per_cell_report)
            f.write('\n\n')

        f.write('---\n\n')
        f.write('*Generated by analyze_heterogeneous.py*\n')

    print(f"\n[OK] Report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description='Heterogeneous Environment Analysis')
    parser.add_argument('--data-dir', required=True, help='Path to voronoi simulation data')
    parser.add_argument('--split-method', choices=['random', 'temporal'], default='temporal')
    parser.add_argument('--max-history', type=int, default=3)
    parser.add_argument('--skip-classification', action='store_true', default=True,
                        help='Skip classification pipeline (default: True, does not scale to large grids)')
    parser.add_argument('--run-classification', action='store_true',
                        help='Force running classification pipeline (only practical for small grids)')
    parser.add_argument('--skip-regression', action='store_true', help='Skip regression pipeline')
    parser.add_argument('--max-samples', type=int, default=None,
                        help='Limit sample count (subsamples data for large datasets)')
    
    # Random Forest hyperparameters
    parser.add_argument('--n-estimators', type=int, default=300,
                       help='Number of trees in Random Forest (default: 300)')
    parser.add_argument('--max-depth', type=int, default=None,
                       help='Maximum depth of trees (default: None = unlimited)')
    parser.add_argument('--min-samples-split', type=int, default=2,
                       help='Minimum samples required to split a node (default: 2)')
    parser.add_argument('--min-samples-leaf', type=int, default=1,
                       help='Minimum samples required at leaf node (default: 1)')

    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    # Create output directory
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    output_dir = data_dir / f'analysis_{timestamp}'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    data = load_voronoi_data(data_dir)

    # Analyze heterogeneity
    heterogeneity_report, rss_range = analyze_heterogeneity(data, output_dir)

    # Run pipelines
    classification_output = None
    regression_output = None
    regression_output_dir = None
    per_cell_report = None

    run_clf = args.run_classification and not args.skip_classification
    if run_clf:
        classification_output = run_classification(
            data_dir, args.split_method, args.max_history,
            n_jobs=4, max_depth=30)

    if not args.skip_regression:
        regression_output, regression_output_dir = run_regression(
            data_dir, args.split_method, args.max_history,
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            min_samples_split=args.min_samples_split,
            min_samples_leaf=args.min_samples_leaf)
        
        # Analyze per-cell performance if Voronoi data
        if regression_output_dir and data['is_voronoi']:
            per_cell_report = analyze_per_cell_performance(
                data, regression_output_dir, output_dir)

    # Generate combined report
    generate_report(output_dir, heterogeneity_report,
                   classification_output, regression_output, rss_range, per_cell_report)

    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Output: {output_dir}")


if __name__ == '__main__':
    main()
