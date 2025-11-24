"""
Data Generation and Feature Filtering Pipeline

This script provides a complete workflow for:
1. Loading raw CSI data from QuaDRiGa experiments
2. Analyzing feature importance
3. Filtering features based on importance threshold
4. Generating augmented datasets with feature selection
5. Saving processed datasets ready for ML training

Similar to exp09 in MATLAB but with intelligent feature selection.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Tuple, Dict, List, Optional
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression, f_regression
from sklearn.preprocessing import StandardScaler
import pickle
import warnings

from data_loader import CSIDataLoader
from config import DEFAULT_DATASET_PATH, OUTPUT_DIR, RANDOM_SEED, FEATURE_GROUPS


class DataGenerator:
    """Generate and filter CSI datasets with intelligent feature selection."""
    
    def __init__(self, source_dataset_path: Optional[Path] = None):
        """
        Initialize data generator.
        
        Args:
            source_dataset_path: Path to source exp09 dataset
        """
        self.source_path = source_dataset_path or DEFAULT_DATASET_PATH
        self.loader = CSIDataLoader(self.source_path)
        self.output_dir = OUTPUT_DIR / "generated_data"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.X_train = None
        self.y_train = None
        self.X_val = None
        self.y_val = None
        self.feature_names = []
        self.feature_importance = None
        self.selected_features = None
        
        print(f"Data Generator initialized")
        print(f"Source: {self.source_path}")
        print(f"Output: {self.output_dir}")
    
    def load_data(self, feature_groups: List[str] = None):
        """
        Load data from source dataset.
        
        Args:
            feature_groups: List of feature groups to load (default: all)
        """
        print("\n" + "=" * 70)
        print("STEP 1: LOADING SOURCE DATA")
        print("=" * 70)
        
        self.X_train, self.y_train, self.X_val, self.y_val = self.loader.load_all(feature_groups)
        
        # Generate feature names
        self._generate_feature_names(feature_groups)
        
        print(f"\n✓ Loaded {self.X_train.shape[0]} training samples")
        print(f"✓ Loaded {self.X_val.shape[0]} validation samples")
        print(f"✓ Total features: {self.X_train.shape[1]}")
        print(f"✓ Feature groups: {feature_groups or 'all'}")
    
    def _generate_feature_names(self, feature_groups: List[str] = None):
        """Generate human-readable feature names."""
        if feature_groups is None:
            feature_groups = list(FEATURE_GROUPS.keys())
        
        self.feature_names = []
        
        for group in feature_groups:
            if group == 'wideband':
                self.feature_names.extend(FEATURE_GROUPS['wideband'])
            elif group == 'rss_per_sc':
                self.feature_names.extend([f'RSS_SC_{i}' for i in range(256)])
            elif group == 'sinr_per_sc':
                self.feature_names.extend([f'SINR_SC_{i}' for i in range(256)])
            elif group == 'h_mag_per_sc':
                self.feature_names.extend([f'H_MAG_SC_{i}' for i in range(256)])
    
    def analyze_feature_importance(self, method: str = 'mutual_info', n_jobs: int = -1):
        """
        Analyze feature importance using multiple methods.
        
        Args:
            method: 'mutual_info', 'f_test', or 'random_forest'
            n_jobs: Number of parallel jobs
        
        Returns:
            Feature importance scores
        """
        print("\n" + "=" * 70)
        print(f"STEP 2: ANALYZING FEATURE IMPORTANCE ({method.upper()})")
        print("=" * 70)
        
        n_features = self.X_train.shape[1]
        
        if method == 'mutual_info':
            print("\nCalculating mutual information for X position...")
            mi_x = mutual_info_regression(self.X_train, self.y_train[:, 0], 
                                          random_state=RANDOM_SEED, n_jobs=n_jobs)
            
            print("Calculating mutual information for Y position...")
            mi_y = mutual_info_regression(self.X_train, self.y_train[:, 1], 
                                          random_state=RANDOM_SEED, n_jobs=n_jobs)
            
            # Average importance for both coordinates
            importance = (mi_x + mi_y) / 2
            print("✓ Mutual information calculated")
        
        elif method == 'f_test':
            print("\nCalculating F-statistics for X position...")
            f_x, _ = f_regression(self.X_train, self.y_train[:, 0])
            
            print("Calculating F-statistics for Y position...")
            f_y, _ = f_regression(self.X_train, self.y_train[:, 1])
            
            # Average F-statistic
            importance = (f_x + f_y) / 2
            # Normalize to [0, 1]
            importance = importance / importance.max()
            print("✓ F-statistics calculated")
        
        elif method == 'random_forest':
            print("\nTraining Random Forest for feature importance...")
            print("This may take a few minutes...")
            
            from sklearn.multioutput import MultiOutputRegressor
            rf = RandomForestRegressor(n_estimators=100, max_depth=10, 
                                      random_state=RANDOM_SEED, n_jobs=n_jobs)
            multi_rf = MultiOutputRegressor(rf)
            multi_rf.fit(self.X_train, self.y_train)
            
            # Average importance across both outputs
            importance = np.mean([est.feature_importances_ for est in multi_rf.estimators_], axis=0)
            print("✓ Random Forest trained")
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        self.feature_importance = importance
        
        # Print statistics
        print(f"\nFeature Importance Statistics:")
        print(f"  Mean:   {importance.mean():.6f}")
        print(f"  Median: {np.median(importance):.6f}")
        print(f"  Std:    {importance.std():.6f}")
        print(f"  Min:    {importance.min():.6f}")
        print(f"  Max:    {importance.max():.6f}")
        
        # Show top features
        top_indices = np.argsort(importance)[-10:][::-1]
        print(f"\n📊 Top 10 Most Important Features:")
        for rank, idx in enumerate(top_indices, 1):
            print(f"  {rank:2d}. {self.feature_names[idx]:20s} - {importance[idx]:.6f}")
        
        return importance
    
    def select_features(self, n_features: int = None, threshold: float = None, 
                       min_features: int = 10):
        """
        Select features based on importance.
        
        Args:
            n_features: Keep top N features (mutually exclusive with threshold)
            threshold: Keep features above this importance (0-1)
            min_features: Minimum number of features to keep
        
        Returns:
            Indices of selected features
        """
        print("\n" + "=" * 70)
        print("STEP 3: SELECTING FEATURES")
        print("=" * 70)
        
        if self.feature_importance is None:
            raise ValueError("Must run analyze_feature_importance() first")
        
        if n_features is not None and threshold is not None:
            raise ValueError("Specify either n_features or threshold, not both")
        
        if n_features is not None:
            # Select top N features
            selected_indices = np.argsort(self.feature_importance)[-n_features:]
            print(f"\n✓ Selected top {n_features} features")
        
        elif threshold is not None:
            # Select features above threshold
            selected_indices = np.where(self.feature_importance >= threshold)[0]
            
            # Ensure minimum features
            if len(selected_indices) < min_features:
                print(f"⚠️  Only {len(selected_indices)} features above threshold {threshold}")
                print(f"   Selecting top {min_features} features instead")
                selected_indices = np.argsort(self.feature_importance)[-min_features:]
            
            print(f"\n✓ Selected {len(selected_indices)} features above threshold {threshold}")
        
        else:
            # Default: select features with above-median importance
            median_importance = np.median(self.feature_importance)
            selected_indices = np.where(self.feature_importance >= median_importance)[0]
            print(f"\n✓ Selected {len(selected_indices)} features (median threshold)")
        
        # Sort indices for consistency
        self.selected_features = np.sort(selected_indices)
        
        # Print selection summary
        print(f"\nFeature Selection Summary:")
        print(f"  Original features: {len(self.feature_importance)}")
        print(f"  Selected features: {len(self.selected_features)}")
        print(f"  Reduction: {100 * (1 - len(self.selected_features)/len(self.feature_importance)):.1f}%")
        
        # Show importance range of selected features
        selected_importance = self.feature_importance[self.selected_features]
        print(f"\n  Selected importance range:")
        print(f"    Min: {selected_importance.min():.6f}")
        print(f"    Max: {selected_importance.max():.6f}")
        print(f"    Mean: {selected_importance.mean():.6f}")
        
        return self.selected_features
    
    def apply_feature_selection(self):
        """Apply feature selection to training and validation data."""
        if self.selected_features is None:
            raise ValueError("Must run select_features() first")
        
        print("\n" + "=" * 70)
        print("STEP 4: APPLYING FEATURE SELECTION")
        print("=" * 70)
        
        X_train_filtered = self.X_train[:, self.selected_features]
        X_val_filtered = self.X_val[:, self.selected_features]
        
        print(f"\n✓ Training data: {self.X_train.shape} → {X_train_filtered.shape}")
        print(f"✓ Validation data: {self.X_val.shape} → {X_val_filtered.shape}")
        
        return X_train_filtered, self.y_train, X_val_filtered, self.y_val
    
    def visualize_feature_importance(self, top_n: int = 30):
        """
        Visualize feature importance.
        
        Args:
            top_n: Number of top features to show
        """
        if self.feature_importance is None:
            print("⚠️  No feature importance available. Run analyze_feature_importance() first.")
            return
        
        print("\n" + "=" * 70)
        print("STEP 5: VISUALIZING FEATURE IMPORTANCE")
        print("=" * 70)
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Top N features bar plot
        ax = axes[0, 0]
        top_indices = np.argsort(self.feature_importance)[-top_n:]
        top_importance = self.feature_importance[top_indices]
        top_names = [self.feature_names[i] for i in top_indices]
        
        colors = ['red' if i in self.selected_features else 'steelblue' 
                 for i in top_indices] if self.selected_features is not None else 'steelblue'
        
        ax.barh(range(top_n), top_importance, color=colors)
        ax.set_yticks(range(top_n))
        ax.set_yticklabels(top_names, fontsize=8)
        ax.set_xlabel('Importance', fontweight='bold')
        ax.set_title(f'Top {top_n} Most Important Features', fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3, axis='x')
        
        if self.selected_features is not None:
            ax.plot([], [], 's', color='red', label='Selected')
            ax.plot([], [], 's', color='steelblue', label='Not Selected')
            ax.legend()
        
        # 2. Importance distribution
        ax = axes[0, 1]
        ax.hist(self.feature_importance, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
        ax.axvline(np.median(self.feature_importance), color='red', linestyle='--', 
                  linewidth=2, label=f'Median: {np.median(self.feature_importance):.6f}')
        ax.axvline(np.mean(self.feature_importance), color='orange', linestyle='--', 
                  linewidth=2, label=f'Mean: {np.mean(self.feature_importance):.6f}')
        ax.set_xlabel('Importance', fontweight='bold')
        ax.set_ylabel('Frequency', fontweight='bold')
        ax.set_title('Feature Importance Distribution', fontweight='bold', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 3. Cumulative importance
        ax = axes[1, 0]
        sorted_importance = np.sort(self.feature_importance)[::-1]
        cumsum = np.cumsum(sorted_importance) / sorted_importance.sum()
        ax.plot(range(len(cumsum)), cumsum * 100, linewidth=2, color='steelblue')
        ax.axhline(80, color='red', linestyle='--', linewidth=1.5, label='80% threshold')
        ax.axhline(90, color='orange', linestyle='--', linewidth=1.5, label='90% threshold')
        ax.axhline(95, color='green', linestyle='--', linewidth=1.5, label='95% threshold')
        ax.set_xlabel('Number of Features', fontweight='bold')
        ax.set_ylabel('Cumulative Importance (%)', fontweight='bold')
        ax.set_title('Cumulative Feature Importance', fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Find features needed for thresholds
        for pct in [80, 90, 95]:
            n_feat = np.where(cumsum >= pct/100)[0][0] + 1
            ax.text(n_feat, pct, f'  {n_feat} features', fontsize=9, va='center')
        
        # 4. Feature importance by group
        ax = axes[1, 1]
        feature_groups_idx = {}
        current_idx = 0
        
        for group in ['wideband', 'rss_per_sc', 'sinr_per_sc', 'h_mag_per_sc']:
            if group == 'wideband':
                size = 3
            else:
                size = 256
            
            if current_idx + size <= len(self.feature_importance):
                feature_groups_idx[group] = range(current_idx, current_idx + size)
                current_idx += size
        
        group_importance = {}
        for group, indices in feature_groups_idx.items():
            group_importance[group] = self.feature_importance[list(indices)].mean()
        
        groups = list(group_importance.keys())
        importances = list(group_importance.values())
        
        ax.bar(groups, importances, color=['coral', 'steelblue', 'seagreen', 'mediumpurple'])
        ax.set_ylabel('Mean Importance', fontweight='bold')
        ax.set_title('Average Importance by Feature Group', fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save plot
        plot_path = self.output_dir / 'feature_importance_analysis.png'
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"\n✓ Saved visualization: {plot_path}")
        plt.close()
    
    def save_filtered_dataset(self, name: str = "filtered_dataset"):
        """
        Save filtered dataset for ML training.
        
        Args:
            name: Name for the dataset files
        """
        print("\n" + "=" * 70)
        print("STEP 6: SAVING FILTERED DATASET")
        print("=" * 70)
        
        if self.selected_features is None:
            print("⚠️  No feature selection applied. Saving original dataset.")
            X_train_save = self.X_train
            X_val_save = self.X_val
        else:
            X_train_save = self.X_train[:, self.selected_features]
            X_val_save = self.X_val[:, self.selected_features]
        
        # Save training data
        train_file = self.output_dir / f"{name}_train.npz"
        np.savez(train_file, X=X_train_save, y=self.y_train)
        print(f"✓ Saved training data: {train_file}")
        print(f"  Shape: X={X_train_save.shape}, y={self.y_train.shape}")
        
        # Save validation data
        val_file = self.output_dir / f"{name}_val.npz"
        np.savez(val_file, X=X_val_save, y=self.y_val)
        print(f"✓ Saved validation data: {val_file}")
        print(f"  Shape: X={X_val_save.shape}, y={self.y_val.shape}")
        
        # Save metadata
        metadata = {
            'n_train_samples': len(self.y_train),
            'n_val_samples': len(self.y_val),
            'n_features_original': self.X_train.shape[1],
            'n_features_selected': X_train_save.shape[1],
            'selected_feature_indices': self.selected_features,
            'selected_feature_names': [self.feature_names[i] for i in self.selected_features] 
                                      if self.selected_features is not None else self.feature_names,
            'feature_importance': self.feature_importance,
            'source_dataset': str(self.source_path),
        }
        
        metadata_file = self.output_dir / f"{name}_metadata.pkl"
        with open(metadata_file, 'wb') as f:
            pickle.dump(metadata, f)
        print(f"✓ Saved metadata: {metadata_file}")
        
        print(f"\n📁 Dataset '{name}' saved successfully!")
        
        return train_file, val_file, metadata_file
    
    def generate_summary_report(self):
        """Generate comprehensive summary report."""
        print("\n" + "=" * 70)
        print("GENERATING SUMMARY REPORT")
        print("=" * 70)
        
        lines = []
        lines.append("=" * 80)
        lines.append("DATA GENERATION AND FEATURE FILTERING REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Source info
        lines.append("--- SOURCE DATA ---")
        lines.append(f"Source path: {self.source_path}")
        lines.append(f"Training samples: {self.X_train.shape[0]}")
        lines.append(f"Validation samples: {self.X_val.shape[0]}")
        lines.append(f"Original features: {self.X_train.shape[1]}")
        lines.append("")
        
        # Feature importance
        if self.feature_importance is not None:
            lines.append("--- FEATURE IMPORTANCE ANALYSIS ---")
            lines.append(f"Mean importance: {self.feature_importance.mean():.6f}")
            lines.append(f"Median importance: {np.median(self.feature_importance):.6f}")
            lines.append(f"Std importance: {self.feature_importance.std():.6f}")
            lines.append("")
            
            # Top 20 features
            lines.append("Top 20 Most Important Features:")
            top_indices = np.argsort(self.feature_importance)[-20:][::-1]
            for rank, idx in enumerate(top_indices, 1):
                lines.append(f"  {rank:2d}. {self.feature_names[idx]:25s} - {self.feature_importance[idx]:.6f}")
            lines.append("")
        
        # Feature selection
        if self.selected_features is not None:
            lines.append("--- FEATURE SELECTION ---")
            lines.append(f"Selected features: {len(self.selected_features)}")
            lines.append(f"Reduction: {100 * (1 - len(self.selected_features)/len(self.feature_importance)):.1f}%")
            
            selected_imp = self.feature_importance[self.selected_features]
            lines.append(f"Selected importance range:")
            lines.append(f"  Min:  {selected_imp.min():.6f}")
            lines.append(f"  Max:  {selected_imp.max():.6f}")
            lines.append(f"  Mean: {selected_imp.mean():.6f}")
            lines.append("")
            
            # Cumulative importance
            sorted_imp = np.sort(self.feature_importance)[::-1]
            cumsum = np.cumsum(sorted_imp) / sorted_imp.sum()
            for pct in [80, 90, 95, 99]:
                n_feat = np.where(cumsum >= pct/100)[0][0] + 1
                lines.append(f"Features for {pct}% importance: {n_feat}")
            lines.append("")
        
        # Position statistics
        lines.append("--- POSITION STATISTICS ---")
        lines.append(f"Training set:")
        lines.append(f"  X: {self.y_train[:, 0].min():.2f} to {self.y_train[:, 0].max():.2f} m")
        lines.append(f"     Mean: {self.y_train[:, 0].mean():.2f} ± {self.y_train[:, 0].std():.2f} m")
        lines.append(f"  Y: {self.y_train[:, 1].min():.2f} to {self.y_train[:, 1].max():.2f} m")
        lines.append(f"     Mean: {self.y_train[:, 1].mean():.2f} ± {self.y_train[:, 1].std():.2f} m")
        lines.append("")
        
        lines.append("=" * 80)
        
        # Save report
        report_file = self.output_dir / "generation_report.txt"
        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"\n✓ Report saved: {report_file}")
        
        # Print to console
        print("\n" + '\n'.join(lines))


def main():
    """Main execution function with CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate and filter CSI dataset with intelligent feature selection'
    )
    parser.add_argument('--source', type=str, default=None,
                       help='Path to source dataset (default: from config)')
    parser.add_argument('--method', type=str, default='mutual_info',
                       choices=['mutual_info', 'f_test', 'random_forest'],
                       help='Feature importance method')
    parser.add_argument('--n_features', type=int, default=None,
                       help='Number of top features to select')
    parser.add_argument('--threshold', type=float, default=None,
                       help='Importance threshold (0-1) for feature selection')
    parser.add_argument('--feature_groups', nargs='+',
                       choices=['wideband', 'rss_per_sc', 'sinr_per_sc', 'h_mag_per_sc'],
                       help='Feature groups to load (default: all)')
    parser.add_argument('--output_name', type=str, default='filtered_dataset',
                       help='Name for output dataset files')
    parser.add_argument('--no_viz', action='store_true',
                       help='Skip visualization')
    
    args = parser.parse_args()
    
    # Create generator
    generator = DataGenerator(args.source)
    
    # Load data
    generator.load_data(feature_groups=args.feature_groups)
    
    # Analyze feature importance
    generator.analyze_feature_importance(method=args.method)
    
    # Visualize (unless disabled)
    if not args.no_viz:
        generator.visualize_feature_importance()
    
    # Select features
    if args.n_features or args.threshold:
        generator.select_features(n_features=args.n_features, threshold=args.threshold)
        generator.apply_feature_selection()
    else:
        # Default: use median threshold
        median_threshold = np.median(generator.feature_importance)
        print(f"\n💡 No selection criteria specified. Using median threshold: {median_threshold:.6f}")
        generator.select_features(threshold=median_threshold)
        generator.apply_feature_selection()
    
    # Save filtered dataset
    generator.save_filtered_dataset(name=args.output_name)
    
    # Generate report
    generator.generate_summary_report()
    
    print("\n" + "=" * 70)
    print("✅ DATA GENERATION AND FILTERING COMPLETE!")
    print("=" * 70)
    print(f"\nOutput directory: {generator.output_dir}")
    print("\nGenerated files:")
    print(f"  - {args.output_name}_train.npz")
    print(f"  - {args.output_name}_val.npz")
    print(f"  - {args.output_name}_metadata.pkl")
    print(f"  - feature_importance_analysis.png")
    print(f"  - generation_report.txt")
    print("\n🎯 Next step: Train models with filtered dataset!")
    print(f"   Use: python models/baseline_models.py --use_processed")


if __name__ == "__main__":
    main()
