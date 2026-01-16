"""
Multi-Metric Fusion Experiments

This script loads saved experiment results and tests different approaches
to combine RSS and SINR for improved localization accuracy.

Usage:
    python fusion_experiments.py <results_directory>
"""

import sys
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.io import loadmat
from scipy.stats import norm


def load_experiment_data(results_dir):
    """Load saved experiment data from MATLAB .mat file"""
    results_dir = Path(results_dir)
    mat_file = results_dir / 'corrected_comparison_results.mat'
    
    if not mat_file.exists():
        raise FileNotFoundError(f"Results file not found: {mat_file}")
    
    print(f"Loading data from: {mat_file}")
    data = loadmat(str(mat_file), squeeze_me=True, struct_as_record=False)
    
    # Load config
    config_file = results_dir / 'experiment_config.json'
    with open(config_file, 'r') as f:
        config_json = json.load(f)
    
    print(f"[OK] Loaded experiment data")
    print(f"  Grid size: {config_json['grid']['size']}x{config_json['grid']['size']}")
    print(f"  Scenario: {config_json['channel']['scenario']}")
    print(f"  Metrics available: RSS, SINR, CQI")
    
    return data, config_json, results_dir


def extract_data_structures(data):
    """Extract key data structures from loaded .mat file"""
    config = data['config']
    metrics = data['metrics']
    walk_path = data['walk_path']
    static_data = data['static_data']
    transition_data = data['transition_data']
    
    # Extract metric values
    rss_wb = metrics.rss_wb
    sinr_wb = metrics.sinr_wb
    cqi_wb = metrics.cqi_wb
    
    # Extract train/test splits
    train_samples_static = static_data.train_samples
    test_samples_static = static_data.test_samples
    train_samples_transition = transition_data.train_samples
    test_samples_transition = transition_data.test_samples
    
    # Extract true locations
    true_locations = walk_path.grid_point_indices
    
    info = {
        'config': config,
        'metrics': {
            'rss': rss_wb,
            'sinr': sinr_wb,
            'cqi': cqi_wb
        },
        'true_locations': true_locations,
        'train_samples_static': train_samples_static,
        'test_samples_static': test_samples_static,
        'train_samples_transition': train_samples_transition,
        'test_samples_transition': test_samples_transition,
        'n_points': config.n_points
    }
    
    print(f"\n[Data Summary]")
    print(f"  Total samples: {len(true_locations)}")
    print(f"  Static train/test: {len(train_samples_static)}/{len(test_samples_static)}")
    print(f"  Transition train/test: {len(train_samples_transition)}/{len(test_samples_transition)}")
    print(f"  Grid points: {info['n_points']}")
    
    return info


def train_gaussian_models(metric_values, true_locations, train_samples, n_points):
    """Train Gaussian models for each grid point"""
    models = []
    
    for point_idx in range(n_points):
        # Find samples at this location
        samples_at_point = []
        for sample_idx in train_samples:
            if true_locations[sample_idx - 1] == point_idx + 1:  # MATLAB 1-indexed
                samples_at_point.append(metric_values[sample_idx - 1])
        
        if len(samples_at_point) > 0:
            mean = np.mean(samples_at_point)
            std = np.std(samples_at_point)
            if std == 0 or not np.isfinite(std):
                std = 1e-6
        else:
            mean = 0
            std = 1e-6
        
        models.append({'mean': mean, 'std': std, 'n_samples': len(samples_at_point)})
    
    return models


def compute_posterior(metric_value, models):
    """Compute posterior probabilities for all locations given a metric value"""
    n_points = len(models)
    posterior = np.zeros(n_points)
    
    for i, model in enumerate(models):
        posterior[i] = norm.pdf(metric_value, model['mean'], model['std'])
    
    # Normalize
    if posterior.sum() > 0:
        posterior = posterior / posterior.sum()
    
    return posterior


def fusion_method_1_multiply(posterior_rss, posterior_sinr, alpha=0.5):
    """Method 1: Weighted posterior multiplication"""
    # P_combined = P(RSS)^alpha * P(SINR)^(1-alpha)
    posterior_combined = (posterior_rss ** alpha) * (posterior_sinr ** (1 - alpha))
    
    # Normalize
    if posterior_combined.sum() > 0:
        posterior_combined = posterior_combined / posterior_combined.sum()
    
    return posterior_combined


def fusion_method_2_average(posterior_rss, posterior_sinr, weight_rss=0.5):
    """Method 2: Weighted average of posteriors"""
    weight_sinr = 1 - weight_rss
    posterior_combined = weight_rss * posterior_rss + weight_sinr * posterior_sinr
    
    # Normalize
    if posterior_combined.sum() > 0:
        posterior_combined = posterior_combined / posterior_combined.sum()
    
    return posterior_combined


def fusion_method_3_bivariate(rss_value, sinr_value, models_bivariate):
    """Method 3: Bivariate Gaussian (RSS, SINR) jointly"""
    n_points = len(models_bivariate)
    posterior = np.zeros(n_points)
    
    for i, model in enumerate(models_bivariate):
        mean = model['mean']
        cov = model['cov']
        
        # Compute bivariate Gaussian PDF
        x = np.array([rss_value, sinr_value])
        diff = x - mean
        
        # Avoid singular covariance
        if np.linalg.det(cov) > 1e-10:
            cov_inv = np.linalg.inv(cov)
            exponent = -0.5 * diff.T @ cov_inv @ diff
            normalization = 1 / (2 * np.pi * np.sqrt(np.linalg.det(cov)))
            posterior[i] = normalization * np.exp(exponent)
        else:
            posterior[i] = 0
    
    # Normalize
    if posterior.sum() > 0:
        posterior = posterior / posterior.sum()
    
    return posterior


def train_bivariate_models(rss_values, sinr_values, true_locations, train_samples, n_points):
    """Train bivariate Gaussian models (RSS, SINR) for each location"""
    models = []
    
    for point_idx in range(n_points):
        # Find samples at this location
        rss_samples = []
        sinr_samples = []
        
        for sample_idx in train_samples:
            if true_locations[sample_idx - 1] == point_idx + 1:
                rss_samples.append(rss_values[sample_idx - 1])
                sinr_samples.append(sinr_values[sample_idx - 1])
        
        if len(rss_samples) > 1:
            # Compute mean vector
            mean = np.array([np.mean(rss_samples), np.mean(sinr_samples)])
            
            # Compute covariance matrix
            data = np.column_stack([rss_samples, sinr_samples])
            cov = np.cov(data.T)
            
            # Regularize covariance to avoid singularity
            cov = cov + np.eye(2) * 1e-6
        else:
            mean = np.array([0, 0])
            cov = np.eye(2) * 1e-6
        
        models.append({'mean': mean, 'cov': cov, 'n_samples': len(rss_samples)})
    
    return models


def evaluate_fusion_method(info, method_name, fusion_func, **kwargs):
    """Evaluate a fusion method on test data"""
    print(f"\n{'='*60}")
    print(f"Evaluating: {method_name}")
    print(f"{'='*60}")
    
    # Train models
    rss_models = train_gaussian_models(
        info['metrics']['rss'], 
        info['true_locations'], 
        info['train_samples_static'], 
        info['n_points']
    )
    
    sinr_models = train_gaussian_models(
        info['metrics']['sinr'], 
        info['true_locations'], 
        info['train_samples_static'], 
        info['n_points']
    )
    
    # Test
    test_samples = info['test_samples_static']
    predictions = []
    
    for sample_idx in test_samples:
        rss_val = info['metrics']['rss'][sample_idx - 1]
        sinr_val = info['metrics']['sinr'][sample_idx - 1]
        
        # Get individual posteriors
        posterior_rss = compute_posterior(rss_val, rss_models)
        posterior_sinr = compute_posterior(sinr_val, sinr_models)
        
        # Combine using specified method
        posterior_combined = fusion_func(posterior_rss, posterior_sinr, **kwargs)
        
        # Predict
        pred_location = np.argmax(posterior_combined) + 1  # 1-indexed
        predictions.append(pred_location)
    
    # Compute accuracy
    true_labels = [info['true_locations'][idx - 1] for idx in test_samples]
    predictions = np.array(predictions)
    true_labels = np.array(true_labels)
    
    accuracy = np.mean(predictions == true_labels) * 100
    mae = np.mean(np.abs(predictions - true_labels))
    
    print(f"  Accuracy: {accuracy:.2f}%")
    print(f"  MAE: {mae:.3f} grid points")
    
    return accuracy, mae, predictions


def evaluate_bivariate_fusion(info):
    """Evaluate bivariate Gaussian fusion"""
    print(f"\n{'='*60}")
    print(f"Evaluating: Bivariate Gaussian (RSS, SINR)")
    print(f"{'='*60}")
    
    # Train bivariate models
    models = train_bivariate_models(
        info['metrics']['rss'],
        info['metrics']['sinr'],
        info['true_locations'],
        info['train_samples_static'],
        info['n_points']
    )
    
    # Test
    test_samples = info['test_samples_static']
    predictions = []
    
    for sample_idx in test_samples:
        rss_val = info['metrics']['rss'][sample_idx - 1]
        sinr_val = info['metrics']['sinr'][sample_idx - 1]
        
        posterior = fusion_method_3_bivariate(rss_val, sinr_val, models)
        pred_location = np.argmax(posterior) + 1
        predictions.append(pred_location)
    
    # Compute accuracy
    true_labels = [info['true_locations'][idx - 1] for idx in test_samples]
    predictions = np.array(predictions)
    true_labels = np.array(true_labels)
    
    accuracy = np.mean(predictions == true_labels) * 100
    mae = np.mean(np.abs(predictions - true_labels))
    
    print(f"  Accuracy: {accuracy:.2f}%")
    print(f"  MAE: {mae:.3f} grid points")
    
    return accuracy, mae, predictions


def main():
    if len(sys.argv) < 2:
        print("Usage: python fusion_experiments.py <results_directory>")
        sys.exit(1)
    
    results_dir = Path(sys.argv[1])
    
    # Load data
    data, config_json, results_dir = load_experiment_data(results_dir)
    info = extract_data_structures(data)
    
    # Store results
    fusion_results = {}
    
    # Baseline: Individual metrics (for comparison)
    print(f"\n{'='*60}")
    print(f"BASELINE: Individual Metrics")
    print(f"{'='*60}")
    print(f"  RSS:  Accuracy = {data['results'].rss.static_acc:.2f}%, MAE = {data['results'].rss.mae_static:.3f}")
    print(f"  SINR: Accuracy = {data['results'].sinr.static_acc:.2f}%, MAE = {data['results'].sinr.mae_static:.3f}")
    print(f"  CQI:  Accuracy = {data['results'].cqi.static_acc:.2f}%, MAE = {data['results'].cqi.mae_static:.3f}")
    
    # Method 1: Posterior multiplication with different alpha values
    for alpha in [0.3, 0.5, 0.7]:
        method_name = f"Posterior Multiply (α={alpha})"
        acc, mae, _ = evaluate_fusion_method(
            info, method_name, fusion_method_1_multiply, alpha=alpha
        )
        fusion_results[f"multiply_alpha_{alpha}"] = {'accuracy': acc, 'mae': mae}
    
    # Method 2: Weighted average with different weights
    for weight_rss in [0.3, 0.5, 0.7]:
        method_name = f"Weighted Average (RSS={weight_rss})"
        acc, mae, _ = evaluate_fusion_method(
            info, method_name, fusion_method_2_average, weight_rss=weight_rss
        )
        fusion_results[f"average_rss_{weight_rss}"] = {'accuracy': acc, 'mae': mae}
    
    # Method 3: Bivariate Gaussian
    acc, mae, _ = evaluate_bivariate_fusion(info)
    fusion_results['bivariate'] = {'accuracy': acc, 'mae': mae}
    
    # Summary
    print(f"\n{'='*60}")
    print(f"FUSION RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"{'Method':<40} {'Accuracy':>10} {'MAE':>10}")
    print(f"{'-'*60}")
    
    for method, result in fusion_results.items():
        print(f"{method:<40} {result['accuracy']:>9.2f}% {result['mae']:>9.3f}")
    
    # Find best
    best_method = max(fusion_results.items(), key=lambda x: x[1]['accuracy'])
    print(f"\n✓ Best Method: {best_method[0]}")
    print(f"  Accuracy: {best_method[1]['accuracy']:.2f}%")
    print(f"  MAE: {best_method[1]['mae']:.3f}")
    
    # Compare to best individual metric
    best_individual_acc = max(
        data['results'].rss.static_acc,
        data['results'].sinr.static_acc,
        data['results'].cqi.static_acc
    )
    improvement = best_method[1]['accuracy'] - best_individual_acc
    print(f"\n  Improvement over best individual metric: {improvement:+.2f}%")


if __name__ == '__main__':
    main()
