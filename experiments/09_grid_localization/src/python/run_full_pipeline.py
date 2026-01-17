"""
Full Grid Localization Pipeline
Orchestrates: Data Generation (MATLAB) -> Localization (Python) -> Visualization (Python)
"""

import argparse
import subprocess
import sys
from pathlib import Path
import json
import re
from datetime import datetime


def run_matlab_data_generation(grid_size, scenario, n_samples):
    """Run MATLAB script to generate simulation data
    
    Args:
        grid_size: Grid size (e.g., '10x10', '7x7', '3x3')
        scenario: 'LOS' or 'NLOS'
        n_samples: Number of samples to generate
    
    Returns:
        Path to generated data directory
    """
    print(f"\n{'='*70}")
    print(f"STEP 1: MATLAB DATA GENERATION")
    print(f"{'='*70}")
    print(f"Grid Size: {grid_size}")
    print(f"Scenario: {scenario}")
    print(f"Samples: {n_samples}")
    
    # Build MATLAB command
    matlab_cmd = (
        f"cd experiments/09_grid_localization/src/matlab; "
        f"config.grid_size = '{grid_size}'; "
        f"config.scenario = '{scenario}'; "
        f"config.n_samples = {n_samples}; "
        f"data_path = generate_simulation_data(config); "
        f"fprintf('DATA_PATH:%s\\n', data_path);"
    )
    
    # Run MATLAB
    result = subprocess.run(
        ['matlab', '-batch', matlab_cmd],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )
    
    if result.returncode != 0:
        print(f"\n❌ MATLAB data generation failed!")
        print(result.stderr)
        sys.exit(1)
    
    # Extract data path from MATLAB output
    output = result.stdout
    match = re.search(r'DATA_PATH:(.+)', output)
    if not match:
        print(f"\n❌ Could not extract data path from MATLAB output!")
        print("MATLAB output:")
        print(output)
        sys.exit(1)
    
    data_path = match.group(1).strip()
    print(f"\n✅ Data generated successfully!")
    print(f"   Path: {data_path}")
    
    return data_path


def run_localization_pipeline(data_dir, model_type, metrics, max_history):
    """Run Python localization pipeline
    
    Args:
        data_dir: Path to simulation data
        model_type: 'gaussian' or 'random_forest'
        metrics: List of metrics to test
        max_history: Maximum history length
    
    Returns:
        Path to results directory
    """
    print(f"\n{'='*70}")
    print(f"STEP 2: LOCALIZATION PIPELINE")
    print(f"{'='*70}")
    print(f"Data Dir: {data_dir}")
    print(f"Model: {model_type}")
    print(f"Metrics: {metrics}")
    print(f"Max History: {max_history}")
    
    # Build command
    cmd = [
        'python',
        'experiments/09_grid_localization/src/python/localization_pipeline.py',
        '--data-dir', data_dir,
        '--model', model_type,
        '--max-history', str(max_history),
        '--metrics'
    ] + metrics
    
    # Run pipeline
    result = subprocess.run(cmd, cwd=Path.cwd())
    
    if result.returncode != 0:
        print(f"\n❌ Localization pipeline failed!")
        sys.exit(1)
    
    # Find the output directory (most recent in the appropriate grid size folder)
    data_path = Path(data_dir)
    
    # Load config to get grid size and scenario
    config_file = data_path / 'config.json'
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    grid_config = config['grid']
    grid_size = f"{grid_config['nx']}x{grid_config['ny']}"
    scenario = 'LOS' if 'LOS' in config['channel']['scenario'] else 'NLOS'
    
    # Find output directory
    results_base = Path('results/grid_localization') / f'grid_{grid_size}'
    if not results_base.exists():
        print(f"\n❌ Results directory not found: {results_base}")
        sys.exit(1)
    
    # Get most recent exp directory
    exp_dirs = sorted([d for d in results_base.iterdir() if d.is_dir() and d.name.startswith('exp')])
    if not exp_dirs:
        print(f"\n❌ No experiment directories found in {results_base}")
        sys.exit(1)
    
    output_dir = exp_dirs[-1]
    
    print(f"\n✅ Localization complete!")
    print(f"   Results: {output_dir}")
    
    return str(output_dir)


def run_plotting(results_dir):
    """Run plotting script to generate visualizations
    
    Args:
        results_dir: Path to results directory
    """
    print(f"\n{'='*70}")
    print(f"STEP 3: VISUALIZATION")
    print(f"{'='*70}")
    print(f"Results Dir: {results_dir}")
    
    # Run plotting script
    cmd = [
        'python',
        'experiments/09_grid_localization/src/python/plot_pipeline_results.py',
        results_dir
    ]
    
    result = subprocess.run(cmd, cwd=Path.cwd())
    
    if result.returncode != 0:
        print(f"\n❌ Plotting failed!")
        sys.exit(1)
    
    print(f"\n✅ Plots generated successfully!")


def main():
    parser = argparse.ArgumentParser(
        description='Full Grid Localization Pipeline: Data Generation -> Localization -> Visualization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with default settings (10x10 NLOS, 40k samples):
  python run_full_pipeline.py
  
  # Generate new 7x7 LOS data:
  python run_full_pipeline.py --grid-size 7x7 --scenario LOS --n-samples 20000
  
  # Use existing data only (skip MATLAB):
  python run_full_pipeline.py --data-dir results/grid_localization/grid_10x10/sim_data_NLOS_2026-01-11_22-43-07
  
  # Use existing data and skip localization (only plot):
  python run_full_pipeline.py --results-dir results/grid_localization/grid_10x10/exp13e_NLOS_2026-01-12_07-40-39 --skip-pipeline
  
  # Random Forest with combined metrics:
  python run_full_pipeline.py --model random_forest --metrics RSS,SINR CQI
  
  # Skip plotting:
  python run_full_pipeline.py --skip-plots
"""
    )
    
    # Data generation options
    parser.add_argument('--data-dir', type=str, 
                       help='Use existing data directory (skip MATLAB generation)')
    parser.add_argument('--grid-size', type=str, default='10x10',
                       help='Grid size for data generation (e.g., 10x10, 7x7, 3x3)')
    parser.add_argument('--scenario', choices=['LOS', 'NLOS'], default='NLOS',
                       help='Channel scenario')
    parser.add_argument('--n-samples', type=int, default=40000,
                       help='Number of samples to generate')
    
    # Localization options
    parser.add_argument('--results-dir', type=str,
                       help='Use existing results directory (skip localization)')
    parser.add_argument('--skip-pipeline', action='store_true',
                       help='Skip localization pipeline (only plot existing results)')
    parser.add_argument('--model', choices=['gaussian', 'random_forest'], default='gaussian',
                       help='Model type to use')
    parser.add_argument('--metrics', nargs='+', default=['rss', 'sinr', 'cqi'],
                       help='Metrics to evaluate. Use comma-separated for combinations (e.g., "RSS,SINR")')
    parser.add_argument('--max-history', type=int, default=3,
                       help='Maximum history length')
    
    # Plotting options
    parser.add_argument('--skip-plots', action='store_true',
                       help='Skip plot generation')
    
    args = parser.parse_args()
    
    start_time = datetime.now()
    print(f"\n{'='*70}")
    print(f"FULL GRID LOCALIZATION PIPELINE")
    print(f"{'='*70}")
    print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Data Generation (or use existing)
    if args.data_dir:
        print(f"\n📁 Using existing data: {args.data_dir}")
        data_dir = args.data_dir
    else:
        data_dir = run_matlab_data_generation(
            args.grid_size, 
            args.scenario, 
            args.n_samples
        )
    
    # Step 2: Localization (or use existing results)
    if args.results_dir:
        print(f"\n📁 Using existing results: {args.results_dir}")
        results_dir = args.results_dir
    elif args.skip_pipeline:
        print(f"\n⏭️  Skipping localization pipeline")
        if not args.results_dir:
            print(f"❌ Must provide --results-dir when using --skip-pipeline")
            sys.exit(1)
        results_dir = args.results_dir
    else:
        results_dir = run_localization_pipeline(
            data_dir,
            args.model,
            args.metrics,
            args.max_history
        )
    
    # Step 3: Plotting
    if args.skip_plots:
        print(f"\n⏭️  Skipping plot generation")
    else:
        run_plotting(results_dir)
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n{'='*70}")
    print(f"PIPELINE COMPLETE!")
    print(f"{'='*70}")
    print(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print(f"\nFinal Results: {results_dir}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
