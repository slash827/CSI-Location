"""
Analyze Base Station Geometry from Existing Dataset
This script helps you figure out the BS positions retroactively
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import KMeans

def load_your_data():
    """
    Replace this with your actual data loading
    """
    # Example - adjust to your actual loading method:
    # data = np.load('experiment_11_data.npz')
    # csi = data['csi']  # Shape: [40000, 4, 64, 64, 2]
    # positions = data['positions']  # Shape: [40000, 2]
    
    # For demonstration:
    print("⚠ Replace this function with your actual data loading!")
    return None, None

def estimate_bs_positions_from_csi(csi_data, ue_positions, num_bs=4):
    """
    Try to estimate BS positions from CSI patterns
    
    Method: Look for strong signal regions (likely near BS)
    """
    print("\n=== Estimating BS Positions from Data ===\n")
    
    # Calculate average CSI magnitude for each BS
    # Shape: [num_samples, num_bs]
    csi_magnitude = np.abs(csi_data[:, :, :, :, 0] + 1j * csi_data[:, :, :, :, 1])
    avg_csi_per_bs = np.mean(csi_magnitude, axis=(2, 3))  # [num_samples, num_bs]
    
    # For each BS, find positions with strongest signal
    estimated_bs_positions = []
    
    for bs_idx in range(num_bs):
        # Get signal strength for this BS at all UE positions
        signal_strength = avg_csi_per_bs[:, bs_idx]
        
        # Find top 10% strongest signals (likely near BS)
        threshold = np.percentile(signal_strength, 90)
        strong_signal_mask = signal_strength > threshold
        
        # Get UE positions with strong signal
        strong_positions = ue_positions[strong_signal_mask]
        
        # Estimate BS position as centroid of strong signal region
        bs_estimate = np.mean(strong_positions, axis=0)
        estimated_bs_positions.append(bs_estimate)
        
        print(f"BS {bs_idx+1} estimated at: [{bs_estimate[0]:.2f}, {bs_estimate[1]:.2f}] m")
    
    return np.array(estimated_bs_positions)

def analyze_bs_geometry(bs_positions):
    """
    Analyze the geometric configuration of base stations
    """
    print("\n=== BS Geometry Analysis ===\n")
    
    num_bs = len(bs_positions)
    print(f"Number of Base Stations: {num_bs}")
    
    # Calculate all pairwise distances
    print("\nInter-BS Distances:")
    distances = squareform(pdist(bs_positions))
    
    for i in range(num_bs):
        for j in range(i+1, num_bs):
            print(f"  BS{i+1} ↔ BS{j+1}: {distances[i,j]:.2f} m")
    
    # Determine geometry type
    print("\n--- Geometry Classification ---")
    
    if num_bs == 4:
        # Get unique distances
        unique_dists = []
        for i in range(num_bs):
            for j in range(i+1, num_bs):
                unique_dists.append(distances[i,j])
        
        unique_dists = np.array(unique_dists)
        dist_std = np.std(unique_dists)
        dist_mean = np.mean(unique_dists)
        
        if dist_std < dist_mean * 0.1:
            geometry = "Square (all equal distances)"
        else:
            # Check for rectangular
            sorted_dists = np.sort(unique_dists)
            side_dists = sorted_dists[:4]
            diag_dists = sorted_dists[4:]
            
            if len(diag_dists) == 2 and np.abs(diag_dists[0] - diag_dists[1]) < 1:
                geometry = "Rectangle (4 sides + 2 diagonals)"
            else:
                geometry = "Custom arrangement"
        
        print(f"Geometry Type: {geometry}")
        
        # Calculate coverage
        min_x, max_x = bs_positions[:, 0].min(), bs_positions[:, 0].max()
        min_y, max_y = bs_positions[:, 1].min(), bs_positions[:, 1].max()
        
        print(f"\nBS Coverage Area:")
        print(f"  X: {min_x:.2f} to {max_x:.2f} m (span: {max_x-min_x:.2f} m)")
        print(f"  Y: {min_y:.2f} to {max_y:.2f} m (span: {max_y-min_y:.2f} m)")
        
        # Calculate centroid
        centroid = np.mean(bs_positions, axis=0)
        print(f"\nCentroid: [{centroid[0]:.2f}, {centroid[1]:.2f}] m")
        
        return {
            'geometry': geometry,
            'distances': distances,
            'centroid': centroid,
            'coverage': (min_x, max_x, min_y, max_y)
        }

def visualize_bs_layout(bs_positions, ue_area=(0, 80, 0, 80), save_path='bs_geometry_analysis.png'):
    """
    Visualize the BS layout
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Plot UE area
    ue_x_min, ue_x_max, ue_y_min, ue_y_max = ue_area
    ax.add_patch(plt.Rectangle((ue_x_min, ue_y_min), 
                                ue_x_max - ue_x_min, 
                                ue_y_max - ue_y_min,
                                fill=False, edgecolor='gray', 
                                linestyle='--', linewidth=2, 
                                label='UE Coverage Area (80×80m)'))
    
    # Plot BS positions
    for i, pos in enumerate(bs_positions):
        ax.plot(pos[0], pos[1], 'r^', markersize=20, 
                markeredgecolor='black', markeredgewidth=2,
                label=f'BS{i+1}' if i == 0 else '')
        ax.text(pos[0]+2, pos[1]+2, f'BS{i+1}', 
                fontsize=14, fontweight='bold')
        
        # Draw coverage circle (approximate)
        circle = plt.Circle(pos, 60, fill=False, 
                          edgecolor='red', alpha=0.3, linestyle=':')
        ax.add_patch(circle)
    
    # Draw lines between BSs
    num_bs = len(bs_positions)
    for i in range(num_bs):
        for j in range(i+1, num_bs):
            ax.plot([bs_positions[i, 0], bs_positions[j, 0]],
                   [bs_positions[i, 1], bs_positions[j, 1]],
                   'b--', alpha=0.3, linewidth=1)
            
            # Add distance label
            mid_x = (bs_positions[i, 0] + bs_positions[j, 0]) / 2
            mid_y = (bs_positions[i, 1] + bs_positions[j, 1]) / 2
            dist = np.linalg.norm(bs_positions[i] - bs_positions[j])
            ax.text(mid_x, mid_y, f'{dist:.1f}m', 
                   fontsize=9, color='blue', 
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    # Draw centroid
    centroid = np.mean(bs_positions, axis=0)
    ax.plot(centroid[0], centroid[1], 'g*', markersize=15, 
            markeredgecolor='black', markeredgewidth=1.5,
            label='Network Centroid')
    
    ax.set_xlabel('X Position (m)', fontsize=12)
    ax.set_ylabel('Y Position (m)', fontsize=12)
    ax.set_title('Base Station Geometric Configuration', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axis('equal')
    ax.legend(fontsize=10)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualization saved to: {save_path}")
    plt.show()

def common_4bs_configurations():
    """
    Show common 4-BS configurations for 80×80m area
    """
    print("\n=== Common 4-BS Configurations ===\n")
    
    configs = {
        'Square (corners)': np.array([
            [0, 0],
            [80, 0],
            [80, 80],
            [0, 80]
        ]),
        
        'Square (centered)': np.array([
            [20, 20],
            [60, 20],
            [60, 60],
            [20, 60]
        ]),
        
        'Rectangle (2×2)': np.array([
            [10, 20],
            [70, 20],
            [70, 60],
            [10, 60]
        ]),
        
        'Triangular + Center': np.array([
            [40, 10],   # Bottom
            [10, 70],   # Top left
            [70, 70],   # Top right
            [40, 40]    # Center
        ])
    }
    
    # Calculate inter-BS distances for each configuration
    for name, positions in configs.items():
        print(f"\n{name}:")
        distances = pdist(positions)
        print(f"  Distance range: {distances.min():.1f}m - {distances.max():.1f}m")
        print(f"  Average distance: {distances.mean():.1f}m")
        print(f"  Positions:\n{positions}")

# ==========================
# Main Analysis Function
# ==========================

def main():
    """
    Main function to run the analysis
    """
    print("=" * 60)
    print("  Base Station Geometry Analysis Tool")
    print("=" * 60)
    
    # Option 1: If you have estimated BS positions
    print("\nOption 1: Manual BS Position Input")
    print("If you know or can estimate BS positions, enter them here.")
    print("Otherwise, we'll try to estimate from data.\n")
    
    # Example: You might know from your QuaDRiGa setup
    # Replace these with actual values if known:
    bs_positions_example = np.array([
        [10, 10],    # BS1
        [70, 10],    # BS2
        [70, 70],    # BS3
        [10, 70]     # BS4
    ])
    
    print("Example BS positions (replace with actual):")
    print(bs_positions_example)
    
    # Analyze geometry
    geometry_info = analyze_bs_geometry(bs_positions_example)
    
    # Visualize
    visualize_bs_layout(bs_positions_example)
    
    # Show common configurations for comparison
    common_4bs_configurations()
    
    print("\n" + "="*60)
    print("To use with your actual data:")
    print("1. Replace 'load_your_data()' with your data loading code")
    print("2. Run 'estimate_bs_positions_from_csi()' to estimate from CSI")
    print("3. Or manually input known BS positions")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
