"""
Exploratory Data Analysis (EDA) for CSI dataset.

Generates comprehensive visualizations and statistical analysis.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

from data_loader import CSIDataLoader
from config import DEFAULT_DATASET_PATH, PLOTS_DIR, FEATURE_GROUPS


class CSIExplorer:
    """EDA for CSI localization dataset."""
    
    def __init__(self, dataset_path=None, output_dir=None):
        """
        Initialize explorer.
        
        Args:
            dataset_path: Path to dataset folder
            output_dir: Directory to save plots
        """
        self.loader = CSIDataLoader(dataset_path)
        self.output_dir = Path(output_dir) if output_dir else PLOTS_DIR / "eda"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set plotting style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
        
        print(f"EDA output directory: {self.output_dir}")
    
    def load_data(self):
        """Load and prepare data."""
        print("\nLoading data...")
        self.X_train, self.y_train, self.X_val, self.y_val = self.loader.load_all()
        
        # Load metadata
        train_data = self.loader.load_train_data()
        self.train_metadata = self.loader.get_metadata_info(train_data)
        
        if self.X_val is not None:
            val_data = self.loader.load_val_data()
            self.val_metadata = self.loader.get_metadata_info(val_data)
        
        print("Data loaded successfully!")
    
    def plot_spatial_distribution(self):
        """Plot spatial distribution of samples."""
        print("\n1. Plotting spatial distribution...")
        
        fig, axes = plt.subplots(1, 2, figsize=(16, 7))
        
        # Training data
        ax = axes[0]
        scatter = ax.scatter(self.y_train[:, 0], self.y_train[:, 1], 
                           c=self.train_metadata.get('distances', np.zeros(len(self.y_train))),
                           cmap='viridis', alpha=0.6, s=30, edgecolors='k', linewidth=0.5)
        ax.set_xlabel('X Position (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Y Position (m)', fontsize=12, fontweight='bold')
        ax.set_title(f'Training Set Spatial Distribution (N={len(self.y_train)})', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        # Mark base station (assumed at center)
        bs_x, bs_y = 50, 50  # From exp09 config
        ax.plot(bs_x, bs_y, 'r^', markersize=15, label='Base Station', 
               markeredgecolor='k', markeredgewidth=1.5)
        ax.legend(fontsize=10)
        
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Distance to BS (m)', fontsize=11)
        
        # Validation data
        if self.X_val is not None:
            ax = axes[1]
            scatter = ax.scatter(self.y_val[:, 0], self.y_val[:, 1],
                               c=self.val_metadata.get('distances', np.zeros(len(self.y_val))),
                               cmap='viridis', alpha=0.6, s=30, edgecolors='k', linewidth=0.5)
            ax.set_xlabel('X Position (m)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Y Position (m)', fontsize=12, fontweight='bold')
            ax.set_title(f'Validation Set Spatial Distribution (N={len(self.y_val)})', 
                        fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            
            ax.plot(bs_x, bs_y, 'r^', markersize=15, label='Base Station',
                   markeredgecolor='k', markeredgewidth=1.5)
            ax.legend(fontsize=10)
            
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Distance to BS (m)', fontsize=11)
        else:
            axes[1].text(0.5, 0.5, 'No Validation Data', 
                        ha='center', va='center', fontsize=16)
            axes[1].axis('off')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '01_spatial_distribution.png', dpi=150, bbox_inches='tight')
        print(f"   Saved: {self.output_dir / '01_spatial_distribution.png'}")
        plt.close()
    
    def plot_position_histograms(self):
        """Plot position distributions."""
        print("\n2. Plotting position histograms...")
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # X position - training
        axes[0, 0].hist(self.y_train[:, 0], bins=30, alpha=0.7, color='steelblue', edgecolor='black')
        axes[0, 0].set_xlabel('X Position (m)', fontsize=11, fontweight='bold')
        axes[0, 0].set_ylabel('Frequency', fontsize=11, fontweight='bold')
        axes[0, 0].set_title('Training: X Position Distribution', fontsize=12, fontweight='bold')
        axes[0, 0].axvline(self.y_train[:, 0].mean(), color='red', linestyle='--', 
                          linewidth=2, label=f'Mean: {self.y_train[:, 0].mean():.1f}m')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Y position - training
        axes[0, 1].hist(self.y_train[:, 1], bins=30, alpha=0.7, color='coral', edgecolor='black')
        axes[0, 1].set_xlabel('Y Position (m)', fontsize=11, fontweight='bold')
        axes[0, 1].set_ylabel('Frequency', fontsize=11, fontweight='bold')
        axes[0, 1].set_title('Training: Y Position Distribution', fontsize=12, fontweight='bold')
        axes[0, 1].axvline(self.y_train[:, 1].mean(), color='red', linestyle='--', 
                          linewidth=2, label=f'Mean: {self.y_train[:, 1].mean():.1f}m')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # X position - validation
        if self.X_val is not None:
            axes[1, 0].hist(self.y_val[:, 0], bins=20, alpha=0.7, color='steelblue', edgecolor='black')
            axes[1, 0].set_xlabel('X Position (m)', fontsize=11, fontweight='bold')
            axes[1, 0].set_ylabel('Frequency', fontsize=11, fontweight='bold')
            axes[1, 0].set_title('Validation: X Position Distribution', fontsize=12, fontweight='bold')
            axes[1, 0].axvline(self.y_val[:, 0].mean(), color='red', linestyle='--', 
                              linewidth=2, label=f'Mean: {self.y_val[:, 0].mean():.1f}m')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
            
            # Y position - validation
            axes[1, 1].hist(self.y_val[:, 1], bins=20, alpha=0.7, color='coral', edgecolor='black')
            axes[1, 1].set_xlabel('Y Position (m)', fontsize=11, fontweight='bold')
            axes[1, 1].set_ylabel('Frequency', fontsize=11, fontweight='bold')
            axes[1, 1].set_title('Validation: Y Position Distribution', fontsize=12, fontweight='bold')
            axes[1, 1].axvline(self.y_val[:, 1].mean(), color='red', linestyle='--', 
                              linewidth=2, label=f'Mean: {self.y_val[:, 1].mean():.1f}m')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
        else:
            for ax in axes[1, :]:
                ax.text(0.5, 0.5, 'No Validation Data', ha='center', va='center', fontsize=14)
                ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '02_position_histograms.png', dpi=150, bbox_inches='tight')
        print(f"   Saved: {self.output_dir / '02_position_histograms.png'}")
        plt.close()
    
    def plot_wideband_features(self):
        """Plot wideband feature distributions."""
        print("\n3. Plotting wideband features...")
        
        # Get wideband feature indices
        train_data = self.loader.load_train_data()
        wideband_features = {}
        for feat in FEATURE_GROUPS['wideband']:
            wideband_features[feat] = self.loader._get_field(train_data, feat)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        axes = axes.ravel()
        
        # Plot each wideband feature
        for idx, (feat_name, feat_data) in enumerate(wideband_features.items()):
            ax = axes[idx]
            
            # Histogram
            ax.hist(feat_data, bins=40, alpha=0.7, color='seagreen', edgecolor='black')
            ax.set_xlabel(f'{feat_name}', fontsize=11, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
            ax.set_title(f'{feat_name} Distribution (Training)', fontsize=12, fontweight='bold')
            
            # Add statistics
            mean_val = feat_data.mean()
            std_val = feat_data.std()
            ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, 
                      label=f'Mean: {mean_val:.2f}')
            ax.axvline(mean_val + std_val, color='orange', linestyle=':', linewidth=1.5, 
                      label=f'±1σ: {std_val:.2f}')
            ax.axvline(mean_val - std_val, color='orange', linestyle=':', linewidth=1.5)
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
        
        # Distance histogram (from metadata)
        if 'distances' in self.train_metadata:
            ax = axes[3]
            distances = self.train_metadata['distances']
            ax.hist(distances, bins=40, alpha=0.7, color='mediumpurple', edgecolor='black')
            ax.set_xlabel('Distance to BS (m)', fontsize=11, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
            ax.set_title('Distance Distribution (Training)', fontsize=12, fontweight='bold')
            ax.axvline(distances.mean(), color='red', linestyle='--', linewidth=2, 
                      label=f'Mean: {distances.mean():.2f}m')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '03_wideband_features.png', dpi=150, bbox_inches='tight')
        print(f"   Saved: {self.output_dir / '03_wideband_features.png'}")
        plt.close()
    
    def plot_feature_vs_distance(self):
        """Plot features vs distance to BS."""
        print("\n4. Plotting features vs distance...")
        
        if 'distances' not in self.train_metadata:
            print("   Skipped: Distance information not available")
            return
        
        distances = self.train_metadata['distances']
        train_data = self.loader.load_train_data()
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        axes = axes.ravel()
        
        # Plot RSS, SINR, CQI vs distance
        features_to_plot = ['RSS_wb', 'SINR_wb', 'CQI_wb']
        colors = ['steelblue', 'coral', 'seagreen']
        
        for idx, (feat_name, color) in enumerate(zip(features_to_plot, colors)):
            ax = axes[idx]
            feat_data = self.loader._get_field(train_data, feat_name)
            
            # Scatter plot with transparency
            ax.scatter(distances, feat_data, alpha=0.3, s=20, c=color, edgecolors='none')
            
            # Add trend line (binned mean)
            dist_bins = np.linspace(distances.min(), distances.max(), 20)
            bin_means = []
            bin_centers = []
            for i in range(len(dist_bins) - 1):
                mask = (distances >= dist_bins[i]) & (distances < dist_bins[i+1])
                if mask.sum() > 0:
                    bin_means.append(feat_data[mask].mean())
                    bin_centers.append((dist_bins[i] + dist_bins[i+1]) / 2)
            
            ax.plot(bin_centers, bin_means, 'r-', linewidth=2.5, label='Binned Mean')
            
            ax.set_xlabel('Distance to BS (m)', fontsize=11, fontweight='bold')
            ax.set_ylabel(feat_name, fontsize=11, fontweight='bold')
            ax.set_title(f'{feat_name} vs Distance', fontsize=12, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
        
        # 4th plot: All features normalized on same plot
        ax = axes[3]
        for feat_name, color in zip(features_to_plot, colors):
            feat_data = self.loader._get_field(train_data, feat_name)
            # Normalize to [0, 1]
            feat_norm = (feat_data - feat_data.min()) / (feat_data.max() - feat_data.min())
            
            # Binned mean
            bin_means = []
            bin_centers = []
            for i in range(len(dist_bins) - 1):
                mask = (distances >= dist_bins[i]) & (distances < dist_bins[i+1])
                if mask.sum() > 0:
                    bin_means.append(feat_norm[mask].mean())
                    bin_centers.append((dist_bins[i] + dist_bins[i+1]) / 2)
            
            ax.plot(bin_centers, bin_means, '-o', linewidth=2, label=feat_name, color=color)
        
        ax.set_xlabel('Distance to BS (m)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Normalized Feature Value', fontsize=11, fontweight='bold')
        ax.set_title('All Features vs Distance (Normalized)', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '04_features_vs_distance.png', dpi=150, bbox_inches='tight')
        print(f"   Saved: {self.output_dir / '04_features_vs_distance.png'}")
        plt.close()
    
    def plot_per_subcarrier_patterns(self):
        """Plot per-subcarrier feature patterns."""
        print("\n5. Plotting per-subcarrier patterns...")
        
        train_data = self.loader.load_train_data()
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # H_mag_per_sc: Mean and std across samples
        H_mag = self.loader._get_field(train_data, 'H_mag_per_sc')
        axes[0, 0].plot(np.mean(H_mag, axis=0), 'b-', linewidth=1.5, label='Mean')
        axes[0, 0].fill_between(range(H_mag.shape[1]), 
                               np.mean(H_mag, axis=0) - np.std(H_mag, axis=0),
                               np.mean(H_mag, axis=0) + np.std(H_mag, axis=0),
                               alpha=0.3, label='±1σ')
        axes[0, 0].set_xlabel('Subcarrier Index', fontsize=11, fontweight='bold')
        axes[0, 0].set_ylabel('Channel Magnitude (dB)', fontsize=11, fontweight='bold')
        axes[0, 0].set_title('Channel Magnitude per Subcarrier', fontsize=12, fontweight='bold')
        axes[0, 0].legend(fontsize=9)
        axes[0, 0].grid(True, alpha=0.3)
        
        # RSS_per_sc
        RSS_per_sc = self.loader._get_field(train_data, 'RSS_per_sc')
        axes[0, 1].plot(np.mean(RSS_per_sc, axis=0), 'r-', linewidth=1.5, label='Mean')
        axes[0, 1].fill_between(range(RSS_per_sc.shape[1]),
                               np.mean(RSS_per_sc, axis=0) - np.std(RSS_per_sc, axis=0),
                               np.mean(RSS_per_sc, axis=0) + np.std(RSS_per_sc, axis=0),
                               alpha=0.3, label='±1σ')
        axes[0, 1].set_xlabel('Subcarrier Index', fontsize=11, fontweight='bold')
        axes[0, 1].set_ylabel('RSS (dBm)', fontsize=11, fontweight='bold')
        axes[0, 1].set_title('RSS per Subcarrier', fontsize=12, fontweight='bold')
        axes[0, 1].legend(fontsize=9)
        axes[0, 1].grid(True, alpha=0.3)
        
        # Heatmap: H_mag for random 50 samples
        sample_indices = np.random.choice(H_mag.shape[0], size=min(50, H_mag.shape[0]), replace=False)
        im = axes[1, 0].imshow(H_mag[sample_indices, :], aspect='auto', cmap='viridis', 
                              interpolation='nearest')
        axes[1, 0].set_xlabel('Subcarrier Index', fontsize=11, fontweight='bold')
        axes[1, 0].set_ylabel('Sample Index', fontsize=11, fontweight='bold')
        axes[1, 0].set_title('Channel Magnitude Heatmap (50 samples)', fontsize=12, fontweight='bold')
        plt.colorbar(im, ax=axes[1, 0], label='Magnitude (dB)')
        
        # Variance across subcarriers
        H_var = np.var(H_mag, axis=0)
        RSS_var = np.var(RSS_per_sc, axis=0)
        axes[1, 1].plot(H_var, 'b-', linewidth=1.5, label='H_mag variance')
        axes[1, 1].plot(RSS_var, 'r-', linewidth=1.5, label='RSS variance', alpha=0.7)
        axes[1, 1].set_xlabel('Subcarrier Index', fontsize=11, fontweight='bold')
        axes[1, 1].set_ylabel('Variance', fontsize=11, fontweight='bold')
        axes[1, 1].set_title('Feature Variance per Subcarrier', fontsize=12, fontweight='bold')
        axes[1, 1].legend(fontsize=9)
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '05_subcarrier_patterns.png', dpi=150, bbox_inches='tight')
        print(f"   Saved: {self.output_dir / '05_subcarrier_patterns.png'}")
        plt.close()
    
    def plot_correlation_analysis(self):
        """Plot correlation between wideband features."""
        print("\n6. Plotting correlation analysis...")
        
        train_data = self.loader.load_train_data()
        
        # Get wideband features + distance
        features_dict = {}
        for feat in FEATURE_GROUPS['wideband']:
            features_dict[feat] = self.loader._get_field(train_data, feat)
        
        if 'distances' in self.train_metadata:
            features_dict['Distance'] = self.train_metadata['distances']
        
        # Create DataFrame for easy correlation
        import pandas as pd
        df = pd.DataFrame(features_dict)
        
        # Correlation matrix
        corr = df.corr()
        
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr, annot=True, fmt='.3f', cmap='coolwarm', center=0,
                   square=True, linewidths=1, cbar_kws={"shrink": 0.8},
                   ax=ax, vmin=-1, vmax=1)
        ax.set_title('Feature Correlation Matrix', fontsize=14, fontweight='bold', pad=15)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '06_correlation_matrix.png', dpi=150, bbox_inches='tight')
        print(f"   Saved: {self.output_dir / '06_correlation_matrix.png'}")
        plt.close()
    
    def generate_summary_statistics(self):
        """Generate and save summary statistics."""
        print("\n7. Generating summary statistics...")
        
        train_data = self.loader.load_train_data()
        
        summary = []
        summary.append("=" * 80)
        summary.append("CSI DATASET - EXPLORATORY DATA ANALYSIS SUMMARY")
        summary.append("=" * 80)
        summary.append("")
        
        # Dataset info
        summary.append("--- DATASET INFO ---")
        summary.append(f"Training samples: {len(self.y_train)}")
        if self.X_val is not None:
            summary.append(f"Validation samples: {len(self.y_val)}")
        summary.append(f"Total features: {self.X_train.shape[1]}")
        summary.append("")
        
        # Position statistics
        summary.append("--- POSITION STATISTICS (Training) ---")
        summary.append(f"X position: {self.y_train[:, 0].min():.2f} to {self.y_train[:, 0].max():.2f} m")
        summary.append(f"            Mean: {self.y_train[:, 0].mean():.2f} ± {self.y_train[:, 0].std():.2f} m")
        summary.append(f"Y position: {self.y_train[:, 1].min():.2f} to {self.y_train[:, 1].max():.2f} m")
        summary.append(f"            Mean: {self.y_train[:, 1].mean():.2f} ± {self.y_train[:, 1].std():.2f} m")
        
        if 'distances' in self.train_metadata:
            dist = self.train_metadata['distances']
            summary.append(f"Distance:   {dist.min():.2f} to {dist.max():.2f} m")
            summary.append(f"            Mean: {dist.mean():.2f} ± {dist.std():.2f} m")
        summary.append("")
        
        # Feature statistics
        summary.append("--- WIDEBAND FEATURE STATISTICS (Training) ---")
        for feat in FEATURE_GROUPS['wideband']:
            feat_data = self.loader._get_field(train_data, feat)
            summary.append(f"{feat:12s}: {feat_data.min():8.2f} to {feat_data.max():8.2f}")
            summary.append(f"              Mean: {feat_data.mean():8.2f} ± {feat_data.std():7.2f}")
        summary.append("")
        
        # Per-subcarrier statistics
        summary.append("--- PER-SUBCARRIER FEATURE STATISTICS (Training) ---")
        for feat_name in ['H_mag_per_sc', 'RSS_per_sc', 'SINR_per_sc']:
            feat_data = self.loader._get_field(train_data, feat_name)
            summary.append(f"{feat_name}:")
            summary.append(f"  Shape: {feat_data.shape}")
            summary.append(f"  Mean across subcarriers: {feat_data.mean():.2f} ± {feat_data.std():.2f}")
            summary.append(f"  Min/Max: {feat_data.min():.2f} / {feat_data.max():.2f}")
        summary.append("")
        
        # Trajectory info
        if 'trajectory_id' in self.train_metadata:
            traj_ids = self.train_metadata['trajectory_id']
            unique_traj = np.unique(traj_ids)
            summary.append("--- TRAJECTORY INFO ---")
            summary.append(f"Number of trajectories: {len(unique_traj)}")
            samples_per_traj = [np.sum(traj_ids == tid) for tid in unique_traj]
            summary.append(f"Samples per trajectory: {np.mean(samples_per_traj):.1f} ± "
                          f"{np.std(samples_per_traj):.1f}")
            summary.append(f"Min/Max samples: {np.min(samples_per_traj)} / {np.max(samples_per_traj)}")
        
        summary.append("")
        summary.append("=" * 80)
        
        # Save to file
        summary_text = "\n".join(summary)
        summary_file = self.output_dir / "eda_summary.txt"
        with open(summary_file, 'w') as f:
            f.write(summary_text)
        
        print(summary_text)
        print(f"\n   Saved: {summary_file}")
    
    def run_full_eda(self):
        """Run complete EDA pipeline."""
        print("\n" + "=" * 70)
        print("STARTING EXPLORATORY DATA ANALYSIS")
        print("=" * 70)
        
        self.load_data()
        self.plot_spatial_distribution()
        self.plot_position_histograms()
        self.plot_wideband_features()
        self.plot_feature_vs_distance()
        self.plot_per_subcarrier_patterns()
        self.plot_correlation_analysis()
        self.generate_summary_statistics()
        
        print("\n" + "=" * 70)
        print("EDA COMPLETE!")
        print(f"All plots saved to: {self.output_dir}")
        print("=" * 70 + "\n")


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Exploratory Data Analysis for CSI dataset')
    parser.add_argument('--dataset_path', type=str, default=None,
                       help='Path to dataset folder (default: from config)')
    parser.add_argument('--output_dir', type=str, default=None,
                       help='Output directory for plots (default: config.PLOTS_DIR/eda)')
    
    args = parser.parse_args()
    
    # Run EDA
    explorer = CSIExplorer(args.dataset_path, args.output_dir)
    explorer.run_full_eda()


if __name__ == "__main__":
    main()
