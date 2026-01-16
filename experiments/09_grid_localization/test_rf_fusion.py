"""
Quick test script for Random Forest with metric fusion

This demonstrates the new capabilities:
1. Combined metrics (RSS + SINR)
2. Random Forest classifier
3. Feature concatenation
"""

import sys
from pathlib import Path

# Find most recent simulation data
results_dir = Path("../../results")
sim_dirs = list(results_dir.glob("sim_data_*"))

if not sim_dirs:
    print("ERROR: No simulation data found!")
    print("Please run: matlab -batch \"cd experiments/09_grid_localization; generate_simulation_data\"")
    sys.exit(1)

# Use most recent
sim_dir = max(sim_dirs, key=lambda p: p.stat().st_mtime)
print(f"Using simulation data: {sim_dir}")

# Test configurations
test_cases = [
    {
        'name': 'Gaussian - RSS only',
        'model': 'gaussian',
        'metrics': ['rss']
    },
    {
        'name': 'Gaussian - SINR only',
        'model': 'gaussian',
        'metrics': ['sinr']
    },
    {
        'name': 'Random Forest - RSS only',
        'model': 'random_forest',
        'metrics': ['rss']
    },
    {
        'name': 'Random Forest - SINR only',
        'model': 'random_forest',
        'metrics': ['sinr']
    },
    {
        'name': 'Random Forest - RSS+SINR FUSION',
        'model': 'random_forest',
        'metrics': [['RSS', 'SINR']]  # Combined!
    },
    {
        'name': 'Random Forest - All metrics combined',
        'model': 'random_forest',
        'metrics': [['RSS', 'SINR', 'CQI']]
    }
]

print("\nTesting metric fusion with Random Forest...")
print("="*70)

# Run first test case to verify everything works
test = test_cases[4]  # RSS+SINR fusion
print(f"\nTest: {test['name']}")
print(f"  Model: {test['model']}")
print(f"  Metrics: {test['metrics']}")

# Import and run
from localization_pipeline import Pipeline

pipeline = Pipeline(
    data_dir=str(sim_dir),
    output_dir=None,
    test_ratio=0.2,
    max_history=3
)

try:
    pipeline.run(metrics_to_test=test['metrics'], model_type=test['model'])
    print("\n✓ SUCCESS! Random Forest with RSS+SINR fusion works!")
    print("\nTo test all configurations, run:")
    for i, tc in enumerate(test_cases):
        metrics_str = str(tc['metrics']).replace("['", '"').replace("']", '"')
        print(f"  # {tc['name']}")
        print(f"  python localization_pipeline.py --data-dir {sim_dir} --model {tc['model']} --metrics {metrics_str}")
        print()
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
