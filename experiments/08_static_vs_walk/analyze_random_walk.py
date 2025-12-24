#!/usr/bin/env python3
"""
Analyze Random Walk Results
Compare temporal correlation in track-based vs step-by-step generation
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.io import loadmat
from pathlib import Path
import seaborn as sns

def analyze_random_walk(results_path):
    """Analyze random walk experiment results"""
    
    print("="*60)
    print("RANDOM WALK ANALYSIS")
    print("="*60)
    
    # Load results
    data = loadmat(results_path)
    
    config = data['config'][0,0]
    metrics = data['metrics'][0,0]
    transitions = data['transitions'][0,0]
    use_track = bool(data['use_track'][0,0])
    
    # Extract metrics
    rss = metrics['RSS_wb'].flatten()
    sinr = metrics['SINR_wb'].flatten()
    path_loss = metrics['path_loss'].flatten()
    
    rss_diff = transitions['RSS_wb_diff'].flatten()
    sinr_diff = transitions['SINR_wb_diff'].flatten()
    path_loss_diff = transitions['path_loss_diff'].flatten()
    
    walk_path = data['walk_path'].flatten()
    
    print(f"\nGeneration Method: {'Track-based (temporal correlation)' if use_track else 'Step-by-step (independent)'}")
    print(f"Total steps: {len(walk_path) - 1}")
    
    # Overall variance analysis
    print("\n" + "="*60)
    print("VARIANCE ANALYSIS")
    print("="*60)
    
    rss_std = np.std(rss)
    path_loss_std = np.std(path_loss)
    
    print(f"\nOverall Statistics:")
    print(f"  RSS std: {rss_std:.3f} dB")
    print(f"  Path loss std: {path_loss_std:.3f} dB")
    
    # Expected values
    if use_track:
        expected_std = 1.5  # Walking with temporal correlation
        print(f"  Expected (track-based): ~1.5-2.5 dB")
    else:
        expected_std = 3.5  # Independent samples
        print(f"  Expected (independent): ~3.5-4.5 dB")
    
    # Check if results match expectations
    tolerance = 1.0  # dB
    if abs(rss_std - expected_std) < tolerance:
        print(f"  ✓ Results match expected variance!")
    else:
        print(f"  ⚠ Unexpected variance (diff: {abs(rss_std - expected_std):.2f} dB)")
    
    # Transition analysis
    print("\n" + "="*60)
    print("TRANSITION ANALYSIS")
    print("="*60)
    
    rss_diff_std = np.std(rss_diff)
    
    print(f"\nStep-to-step changes:")
    print(f"  RSS diff mean: {np.mean(rss_diff):.3f} dB (should be ~0)")
    print(f"  RSS diff std: {rss_diff_std:.3f} dB")
    
    if use_track:
        print(f"  Expected (temporal): ~0.5-1.5 dB")
        if rss_diff_std < 2.0:
            print(f"  ✓ Good temporal correlation!")
        else:
            print(f"  ⚠ High step changes - may not have temporal correlation")
    else:
        print(f"  Expected (independent): ~5.0-6.0 dB")
        if rss_diff_std > 4.0:
            print(f"  ✓ Confirmed independent samples")
    
    # Per-point variance
    print("\n" + "="*60)
    print("PER-POINT VARIANCE")
    print("="*60)
    
    n_points = 9
    per_point_std = []
    
    print(f"\n{'Point':<8} {'Visits':<10} {'RSS std (dB)':<15} {'Expected':<15}")
    print("-"*60)
    
    for pt in range(1, n_points + 1):
        mask = (walk_path == pt)
        rss_pt = rss[mask]
        
        if len(rss_pt) > 1:
            std_pt = np.std(rss_pt)
            per_point_std.append(std_pt)
            
            # Expected variance within point
            if use_track:
                expected_pt = 0.3  # Temporal fading only
            else:
                expected_pt = 3.5  # Independent samples
            
            status = "✓" if abs(std_pt - expected_pt) < 1.5 else "⚠"
            print(f"{pt:<8} {len(rss_pt):<10} {std_pt:<15.3f} {expected_pt:<15.1f} {status}")
    
    avg_per_point_std = np.mean(per_point_std)
    print(f"\nAverage per-point std: {avg_per_point_std:.3f} dB")
    
    if use_track:
        print(f"Expected (temporal): ~0.3-0.8 dB")
        if avg_per_point_std < 1.5:
            print("✓ Good! Low variance within points (temporal correlation working)")
        else:
            print("⚠ High variance within points - temporal correlation may be weak")
    else:
        print(f"Expected (independent): ~3.5-4.5 dB")
        if avg_per_point_std > 2.5:
            print("✓ High variance confirms independent samples")
    
    # Create visualizations
    create_visualizations(rss, rss_diff, walk_path, use_track, results_path.parent)
    
    return {
        'use_track': use_track,
        'rss_std': rss_std,
        'rss_diff_std': rss_diff_std,
        'per_point_avg_std': avg_per_point_std,
        'expected_rss_std': expected_std,
    }

def create_visualizations(rss, rss_diff, walk_path, use_track, output_dir):
    """Create analysis visualizations"""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. RSS over time
    ax = axes[0, 0]
    ax.plot(rss, 'b-', linewidth=0.5, alpha=0.7)
    ax.set_xlabel('Step')
    ax.set_ylabel('RSS (dBm)')
    ax.set_title(f'RSS Evolution ({"Temporal" if use_track else "Independent"})')
    ax.grid(True, alpha=0.3)
    
    # 2. RSS distribution
    ax = axes[0, 1]
    ax.hist(rss, bins=50, alpha=0.7, edgecolor='black')
    ax.axvline(np.mean(rss), color='r', linestyle='--', label=f'Mean: {np.mean(rss):.2f}')
    ax.axvline(np.mean(rss) + np.std(rss), color='orange', linestyle='--', 
               label=f'σ: {np.std(rss):.2f}')
    ax.axvline(np.mean(rss) - np.std(rss), color='orange', linestyle='--')
    ax.set_xlabel('RSS (dBm)')
    ax.set_ylabel('Count')
    ax.set_title('RSS Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Step-to-step RSS changes
    ax = axes[1, 0]
    ax.hist(rss_diff, bins=50, alpha=0.7, edgecolor='black')
    ax.axvline(0, color='r', linestyle='--', label='Zero change')
    ax.axvline(np.std(rss_diff), color='orange', linestyle='--', 
               label=f'σ: {np.std(rss_diff):.2f}')
    ax.axvline(-np.std(rss_diff), color='orange', linestyle='--')
    ax.set_xlabel('RSS Difference (dB)')
    ax.set_ylabel('Count')
    ax.set_title(f'Step-to-Step Changes ({"Small for temporal" if use_track else "Large for independent"})')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 4. Per-point variance
    ax = axes[1, 1]
    per_point_std = []
    for pt in range(1, 10):
        mask = (walk_path == pt)
        rss_pt = rss[mask]
        if len(rss_pt) > 1:
            per_point_std.append(np.std(rss_pt))
        else:
            per_point_std.append(0)
    
    ax.bar(range(1, 10), per_point_std, alpha=0.7, edgecolor='black')
    expected = 0.5 if use_track else 3.5
    ax.axhline(expected, color='r', linestyle='--', 
               label=f'Expected: {expected:.1f} dB')
    ax.set_xlabel('Grid Point')
    ax.set_ylabel('RSS std (dB)')
    ax.set_title(f'Variance Within Each Point ({"Should be low" if use_track else "Should be high"})')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'random_walk_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved visualization: {output_dir / 'random_walk_analysis.png'}")
    plt.close()

def main():
    # Find most recent exp13b results
    results_dir = Path(__file__).parent.parent / 'results'
    exp13b_dirs = sorted(results_dir.glob('exp13b_*'))
    
    if not exp13b_dirs:
        print("No exp13b results found!")
        print(f"Run exp13b_random_walk.m first")
        return
    
    latest_dir = exp13b_dirs[-1]
    results_file = latest_dir / 'random_walk_results.mat'
    
    print(f"Analyzing: {latest_dir.name}\n")
    
    results = analyze_random_walk(results_file)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if results['use_track']:
        print("\n✓ Track-based generation was used")
        print(f"  RSS std: {results['rss_std']:.2f} dB (expected: ~1.5-2.5 dB)")
        print(f"  Per-point avg std: {results['per_point_avg_std']:.2f} dB (expected: ~0.3-0.8 dB)")
        
        if results['rss_std'] < 3.0 and results['per_point_avg_std'] < 1.5:
            print("\n✓✓ EXCELLENT! Temporal correlation is working!")
        else:
            print("\n⚠ Results don't show strong temporal correlation")
            print("  Track generation may have fallen back to independent samples")
    else:
        print("\n⚠ Step-by-step (independent) generation was used")
        print(f"  RSS std: {results['rss_std']:.2f} dB (expected: ~3.5-4.5 dB)")
        print(f"  Per-point avg std: {results['per_point_avg_std']:.2f} dB (expected: ~3.5-4.5 dB)")
        print("\n→ Try running exp13b_random_walk_FIXED.m for proper temporal correlation")

if __name__ == '__main__':
    main()
