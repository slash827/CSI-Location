"""
Model Investigation Tool

This script performs comprehensive diagnostics on Random Forest models to detect:
- Data leakage
- Overfitting
- Feature importance
- Cross-validation performance

Usage:
    python investigate_model.py <data_directory>
"""

import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.io import loadmat
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, learning_curve
from sklearn.inspection import permutation_importance
from sklearn.metrics import confusion_matrix, accuracy_score
import pandas as pd

sns.set_style('whitegrid')


def load_data(data_dir):
    """Load simulation data"""
    data_dir = Path(data_dir)
    
    sim_file = data_dir / 'simulation_data.mat'
    if not sim_file.exists():
        raise FileNotFoundError(f"Simulation data not found: {sim_file}")
    
    print(f"Loading data from: {sim_file}")
    data = loadmat(str(sim_file), squeeze_me=True, struct_as_record=False)
    
    config_file = data_dir / 'config.json'
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    return data, config


def prepare_features(data, feature_names):
    """Prepare feature matrix from available metrics"""
    metrics_data = data['metrics']
    features = []
    actual_names = []
    
    for name in feature_names:
        name_lower = name.lower().replace('+', '_').replace('-', '_')
        
        if hasattr(metrics_data, 'rss_wb') and 'rss' in name_lower:
            features.append(metrics_data.rss_wb)
            actual_names.append('RSS')
        elif hasattr(metrics_data, 'sinr_wb') and 'sinr' in name_lower:
            features.append(metrics_data.sinr_wb)
            actual_names.append('SINR')
        elif hasattr(metrics_data, 'cqi_wb') and 'cqi' in name_lower:
            features.append(metrics_data.cqi_wb)
            actual_names.append('CQI')
        elif hasattr(metrics_data, 'aoa_azimuth') and 'aoa_azimuth' in name_lower:
            features.append(metrics_data.aoa_azimuth)
            actual_names.append('AoA_Azimuth')
        elif hasattr(metrics_data, 'aoa_elevation') and 'aoa_elevation' in name_lower:
            features.append(metrics_data.aoa_elevation)
            actual_names.append('AoA_Elevation')
        elif hasattr(metrics_data, 'timing_advance') and 'timing_advance' in name_lower:
            features.append(metrics_data.timing_advance)
            actual_names.append('Timing_Advance')
    
    X = np.column_stack(features)
    return X, actual_names


def check_feature_uniqueness(X, y, feature_names):
    """Check if each feature combination is unique per location (data leakage indicator)"""
    print("\n" + "="*70)
    print("FEATURE UNIQUENESS CHECK (Data Leakage Detection)")
    print("="*70)
    
    n_locations = len(np.unique(y))
    
    # Check if feature combinations are unique per location
    unique_combinations = set()
    location_feature_map = {}
    
    for i, (features, location) in enumerate(zip(X, y)):
        feature_tuple = tuple(features)
        
        if feature_tuple not in unique_combinations:
            unique_combinations.add(feature_tuple)
            if feature_tuple not in location_feature_map:
                location_feature_map[feature_tuple] = set()
            location_feature_map[feature_tuple].add(location)
    
    # Count how many feature combinations map to single location
    single_location_features = sum(1 for locs in location_feature_map.values() if len(locs) == 1)
    multi_location_features = len(location_feature_map) - single_location_features
    
    print(f"Total unique feature combinations: {len(unique_combinations)}")
    print(f"Combinations mapping to SINGLE location: {single_location_features} ({single_location_features/len(unique_combinations)*100:.1f}%)")
    print(f"Combinations mapping to MULTIPLE locations: {multi_location_features} ({multi_location_features/len(unique_combinations)*100:.1f}%)")
    
    if single_location_features / len(unique_combinations) > 0.9:
        print("\n⚠️  WARNING: >90% of feature combinations are unique to single locations!")
        print("   This indicates potential DATA LEAKAGE or perfect separability.")
        print("   The model might be memorizing feature->location mappings.")
    
    # Check per-feature uniqueness
    print("\nPer-feature analysis:")
    for idx, name in enumerate(feature_names):
        unique_vals = len(np.unique(X[:, idx]))
        unique_per_location = unique_vals / n_locations
        print(f"  {name:20s}: {unique_vals:6d} unique values ({unique_per_location:.2f} per location)")
        
        if unique_vals >= 0.9 * len(X):
            print(f"    ⚠️  Nearly all values are unique! Possible fingerprinting.")


def compute_feature_importance(X_train, y_train, X_test, y_test, feature_names):
    """Compute and visualize feature importance"""
    print("\n" + "="*70)
    print("FEATURE IMPORTANCE ANALYSIS")
    print("="*70)
    
    # Train model
    print("Training Random Forest for feature importance...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    
    train_acc = accuracy_score(y_train, rf.predict(X_train))
    test_acc = accuracy_score(y_test, rf.predict(X_test))
    
    print(f"Train Accuracy: {train_acc*100:.2f}%")
    print(f"Test Accuracy:  {test_acc*100:.2f}%")
    
    if train_acc > 0.99 and test_acc > 0.99:
        print("\n⚠️  WARNING: Near-perfect accuracy on both train and test!")
        print("   This suggests the problem is TOO EASY or there's data leakage.")
    
    # Gini importance (built-in)
    gini_importance = rf.feature_importances_
    
    # Permutation importance (more reliable)
    print("\nComputing permutation importance (this may take a minute)...")
    perm_importance = permutation_importance(rf, X_test, y_test, n_repeats=10, 
                                            random_state=42, n_jobs=-1)
    
    # Create DataFrame
    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Gini_Importance': gini_importance,
        'Perm_Importance': perm_importance.importances_mean,
        'Perm_Std': perm_importance.importances_std
    })
    importance_df = importance_df.sort_values('Perm_Importance', ascending=False)
    
    print("\nFeature Importance Results:")
    print(importance_df.to_string(index=False))
    
    return importance_df, rf


def plot_feature_importance(importance_df, output_dir):
    """Plot feature importance comparison"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Gini importance
    ax = axes[0]
    sorted_gini = importance_df.sort_values('Gini_Importance', ascending=True)
    ax.barh(sorted_gini['Feature'], sorted_gini['Gini_Importance'], color='skyblue', edgecolor='navy')
    ax.set_xlabel('Gini Importance', fontsize=12, fontweight='bold')
    ax.set_title('Gini Importance (Built-in)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    # Permutation importance
    ax = axes[1]
    sorted_perm = importance_df.sort_values('Perm_Importance', ascending=True)
    ax.barh(sorted_perm['Feature'], sorted_perm['Perm_Importance'], 
            xerr=sorted_perm['Perm_Std'], color='lightcoral', edgecolor='darkred')
    ax.set_xlabel('Permutation Importance', fontsize=12, fontweight='bold')
    ax.set_title('Permutation Importance (Test Set)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    output_file = output_dir / 'feature_importance.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n[SAVED] {output_file}")
    plt.close()


def analyze_correlations(X, feature_names, output_dir):
    """Analyze feature correlations"""
    print("\n" + "="*70)
    print("FEATURE CORRELATION ANALYSIS")
    print("="*70)
    
    # Compute correlation matrix
    corr_matrix = np.corrcoef(X.T)
    
    # Create DataFrame
    corr_df = pd.DataFrame(corr_matrix, index=feature_names, columns=feature_names)
    
    print("\nCorrelation Matrix:")
    print(corr_df.to_string())
    
    # Plot heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr_df, annot=True, fmt='.3f', cmap='coolwarm', center=0,
                square=True, linewidths=1, cbar_kws={"shrink": 0.8})
    ax.set_title('Feature Correlation Matrix', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_file = output_dir / 'feature_correlations.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n[SAVED] {output_file}")
    plt.close()
    
    # Flag high correlations
    high_corr_pairs = []
    for i in range(len(feature_names)):
        for j in range(i+1, len(feature_names)):
            if abs(corr_matrix[i, j]) > 0.8:
                high_corr_pairs.append((feature_names[i], feature_names[j], corr_matrix[i, j]))
    
    if high_corr_pairs:
        print("\n⚠️  High correlations detected (|r| > 0.8):")
        for f1, f2, corr in high_corr_pairs:
            print(f"  {f1} ↔ {f2}: r={corr:.3f}")
        print("  Highly correlated features provide redundant information.")


def cross_validation_analysis(X, y, feature_names):
    """Perform cross-validation to detect overfitting"""
    print("\n" + "="*70)
    print("CROSS-VALIDATION ANALYSIS")
    print("="*70)
    
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    
    print("Running 5-fold cross-validation...")
    cv_scores = cross_val_score(rf, X, y, cv=5, scoring='accuracy', n_jobs=-1)
    
    print(f"\nCross-validation scores: {cv_scores}")
    print(f"Mean CV accuracy: {cv_scores.mean()*100:.2f}% (±{cv_scores.std()*100:.2f}%)")
    
    if cv_scores.mean() > 0.99:
        print("\n⚠️  WARNING: Cross-validation accuracy >99%!")
        print("   The problem might be too easy or features are too discriminative.")


def plot_learning_curves(X, y, output_dir):
    """Plot learning curves to detect overfitting"""
    print("\n" + "="*70)
    print("LEARNING CURVE ANALYSIS")
    print("="*70)
    
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    
    train_sizes = np.linspace(0.1, 1.0, 10)
    
    print("Computing learning curves (this may take a few minutes)...")
    train_sizes_abs, train_scores, test_scores = learning_curve(
        rf, X, y, train_sizes=train_sizes, cv=5, scoring='accuracy',
        n_jobs=-1, shuffle=True, random_state=42
    )
    
    train_mean = train_scores.mean(axis=1)
    train_std = train_scores.std(axis=1)
    test_mean = test_scores.mean(axis=1)
    test_std = test_scores.std(axis=1)
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 7))
    
    ax.plot(train_sizes_abs, train_mean, 'o-', color='blue', linewidth=2, 
            markersize=8, label='Training score')
    ax.fill_between(train_sizes_abs, train_mean - train_std, train_mean + train_std,
                     alpha=0.2, color='blue')
    
    ax.plot(train_sizes_abs, test_mean, 'o-', color='red', linewidth=2,
            markersize=8, label='Cross-validation score')
    ax.fill_between(train_sizes_abs, test_mean - test_std, test_mean + test_std,
                     alpha=0.2, color='red')
    
    ax.set_xlabel('Training Set Size', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
    ax.set_title('Learning Curves (Random Forest)', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 1.05])
    
    plt.tight_layout()
    output_file = output_dir / 'learning_curves.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n[SAVED] {output_file}")
    plt.close()
    
    # Analyze gap
    final_gap = train_mean[-1] - test_mean[-1]
    print(f"\nFinal train-test gap: {final_gap*100:.2f}%")
    
    if final_gap < 0.02 and test_mean[-1] > 0.98:
        print("⚠️  Very small gap + high test accuracy = Problem too easy or data leakage")
    elif final_gap > 0.1:
        print("⚠️  Large gap = Overfitting detected")
    else:
        print("✓  Healthy train-test gap")


def ablation_study(X, y, feature_names, output_dir):
    """Test performance with individual features removed"""
    print("\n" + "="*70)
    print("ABLATION STUDY (Remove One Feature at a Time)")
    print("="*70)
    
    from sklearn.model_selection import train_test_split
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Baseline (all features)
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    baseline_acc = accuracy_score(y_test, rf.predict(X_test))
    
    print(f"\nBaseline (all features): {baseline_acc*100:.2f}%")
    
    results = []
    
    # Remove each feature one at a time
    for idx, feature_name in enumerate(feature_names):
        # Create feature set without this feature
        feature_mask = np.ones(X.shape[1], dtype=bool)
        feature_mask[idx] = False
        
        X_train_ablated = X_train[:, feature_mask]
        X_test_ablated = X_test[:, feature_mask]
        
        rf_ablated = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_ablated.fit(X_train_ablated, y_train)
        acc_ablated = accuracy_score(y_test, rf_ablated.predict(X_test_ablated))
        
        drop = (baseline_acc - acc_ablated) * 100
        results.append({
            'Removed_Feature': feature_name,
            'Accuracy': acc_ablated * 100,
            'Drop_from_Baseline': drop
        })
        
        print(f"Without {feature_name:20s}: {acc_ablated*100:6.2f}% (drop: {drop:+6.2f}%)")
    
    # Plot
    results_df = pd.DataFrame(results).sort_values('Drop_from_Baseline', ascending=False)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ['red' if x > 5 else 'orange' if x > 1 else 'green' for x in results_df['Drop_from_Baseline']]
    ax.barh(results_df['Removed_Feature'], results_df['Drop_from_Baseline'], color=colors, edgecolor='black')
    ax.axvline(0, color='black', linewidth=1)
    ax.set_xlabel('Accuracy Drop when Feature Removed (%)', fontsize=12, fontweight='bold')
    ax.set_title('Feature Ablation Study', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    output_file = output_dir / 'ablation_study.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n[SAVED] {output_file}")
    plt.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python investigate_model.py <sim_data_directory>")
        sys.exit(1)
    
    data_dir = Path(sys.argv[1])
    
    print("\n" + "="*70)
    print("RANDOM FOREST MODEL INVESTIGATION")
    print("="*70)
    print(f"Data directory: {data_dir}\n")
    
    # Load data
    data, config = load_data(data_dir)
    
    # Prepare features (use all available)
    feature_list = ['rss', 'sinr', 'aoa_azimuth', 'aoa_elevation', 'timing_advance']
    X, feature_names = prepare_features(data, feature_list)
    y = data['walk_path'].grid_point_indices
    
    print(f"Features loaded: {feature_names}")
    print(f"Data shape: {X.shape}")
    print(f"Number of locations: {len(np.unique(y))}")
    
    # Create output directory
    output_dir = data_dir / 'model_diagnostics'
    output_dir.mkdir(exist_ok=True)
    
    # Run diagnostics
    check_feature_uniqueness(X, y, feature_names)
    
    # Split data
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    importance_df, rf = compute_feature_importance(X_train, y_train, X_test, y_test, feature_names)
    plot_feature_importance(importance_df, output_dir)
    
    analyze_correlations(X, feature_names, output_dir)
    
    cross_validation_analysis(X, y, feature_names)
    
    plot_learning_curves(X, y, output_dir)
    
    ablation_study(X, y, feature_names, output_dir)
    
    print("\n" + "="*70)
    print(f"All diagnostics saved to: {output_dir}")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
