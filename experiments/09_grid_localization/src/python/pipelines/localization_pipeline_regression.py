"""
3D Regression Pipeline for UE Localization

Instead of classifying grid points, this pipeline predicts continuous 3D position:
- Distance to BS (meters)
- AoA Azimuth (degrees)
- AoA Elevation (degrees)

Usage:
    python localization_pipeline_regression.py --data-dir <sim_data_dir> --model random_forest
"""

import argparse
import json
import numpy as np
from pathlib import Path
from scipy.io import loadmat
from datetime import datetime

# Project root: 4 levels up from src/python/ -> experiments/09_grid_localization/ -> experiments/ -> CSI-Location/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor
import time
from utils.read_jsonc import read_jsonc


class RegressionData:
    """Container for regression simulation data"""
    
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.load_data()
    
    def load_data(self):
        """Load simulation data and compute ground truth targets"""
        sim_file = self.data_dir / 'simulation_data.mat'
        if not sim_file.exists():
            raise FileNotFoundError(f"Simulation data not found: {sim_file}")
        
        print(f"Loading simulation data from: {sim_file}")
        data = loadmat(str(sim_file), squeeze_me=True, struct_as_record=False)
        
        # Load configuration from data directory (preserves generation parameters)
        # Handle both old (config.json) and new (data_generation_config.jsonc) filenames
        config_file = self.data_dir / 'data_generation_config.jsonc'
        if not config_file.exists():
            config_file = self.data_dir / 'config.jsonc'
        if not config_file.exists():
            config_file = self.data_dir / 'config.json'
        self.config = read_jsonc(config_file) if config_file.suffix == '.jsonc' else json.load(open(config_file))
        
        # Load ML config for realistic_aoa settings
        ml_config_file = Path(__file__).parent.parent.parent / 'configs' / 'ml_config.jsonc'
        if ml_config_file.exists():
            self.ml_config = read_jsonc(ml_config_file)
        else:
            self.ml_config = {}
        
        # Extract input features
        self.metrics = {
            'rss': data['metrics'].rss_wb,
            'sinr': data['metrics'].sinr_wb,
            'cqi': data['metrics'].cqi_wb
        }
        
        # Add AoA and TA if available
        # Apply realistic impairments to AoA if configured in ml_config
        if hasattr(data['metrics'], 'aoa_azimuth'):
            aoa_az = data['metrics'].aoa_azimuth
            if self.ml_config.get('realistic_aoa', {}).get('enabled', False):
                noise_std = self.ml_config['realistic_aoa']['noise_std_deg']
                quant_step = self.ml_config['realistic_aoa']['quantization_deg']
                np.random.seed(42)  # Reproducible noise
                aoa_az = aoa_az + noise_std * np.random.randn(len(aoa_az))
                aoa_az = np.round(aoa_az / quant_step) * quant_step
            self.metrics['aoa_azimuth'] = aoa_az
            
        if hasattr(data['metrics'], 'aoa_elevation'):
            aoa_el = data['metrics'].aoa_elevation
            if self.ml_config.get('realistic_aoa', {}).get('enabled', False):
                noise_std = self.ml_config['realistic_aoa']['noise_std_deg']
                quant_step = self.ml_config['realistic_aoa']['quantization_deg']
                np.random.seed(43)  # Reproducible noise (different seed)
                aoa_el = aoa_el + noise_std * np.random.randn(len(aoa_el))
                aoa_el = np.round(aoa_el / quant_step) * quant_step
            self.metrics['aoa_elevation'] = aoa_el
            
        if hasattr(data['metrics'], 'timing_advance'):
            self.metrics['timing_advance'] = data['metrics'].timing_advance
        
        # Add path-loss and multi-path metrics if available
        if hasattr(data['metrics'], 'path_loss'):
            self.metrics['path_loss'] = data['metrics'].path_loss
        
        if hasattr(data['metrics'], 'n_multipath'):
            self.metrics['n_multipath'] = data['metrics'].n_multipath
        
        if hasattr(data['metrics'], 'rms_delay_spread'):
            self.metrics['rms_delay_spread'] = data['metrics'].rms_delay_spread
        
        if hasattr(data['metrics'], 'k_factor'):
            self.metrics['k_factor'] = data['metrics'].k_factor

        # Per-interferer RSS fields (rss_ibs_1, rss_ibs_2, ...) for multi-BS experiments
        for field in dir(data['metrics']):
            if field.startswith('rss_ibs_'):
                self.metrics[field] = getattr(data['metrics'], field)

        # Compute ground truth targets from UE positions
        ue_positions = data['walk_path'].positions_jittered  # [N x 3] array
        bs_position = self.config['base_station']['position']
        
        self.n_samples = len(ue_positions)
        
        # Compute targets (distance, azimuth, elevation)
        self.targets = self._compute_targets(ue_positions, bs_position)
        
        available_metrics = ', '.join(self.metrics.keys())
        print(f"[OK] Loaded {self.n_samples} samples")
        print(f"     Available features: {available_metrics}")
        print(f"     Target shape: {self.targets.shape} (distance, azimuth, elevation)")
    
    def _compute_targets(self, ue_positions, bs_position):
        """Compute ground truth distance, azimuth, elevation from UE positions"""
        bs_pos = np.array(bs_position)
        
        # Store UE positions for later error calculation
        self.ue_positions = ue_positions
        self.bs_position = bs_pos
        
        # Compute relative position
        delta = ue_positions - bs_pos  # [dx, dy, dz]
        
        # Distance (3D Euclidean)
        distance = np.linalg.norm(delta, axis=1)
        
        # Azimuth angle (horizontal plane, 0° = North, clockwise)
        azimuth = np.arctan2(delta[:, 0], delta[:, 1]) * 180 / np.pi
        
        # Elevation angle (vertical, negative = below BS)
        horizontal_dist = np.sqrt(delta[:, 0]**2 + delta[:, 1]**2)
        elevation = -np.arctan2(delta[:, 2], horizontal_dist) * 180 / np.pi
        
        # Stack as [N x 3]
        targets = np.column_stack([distance, azimuth, elevation])
        
        print(f"\nGround truth statistics:")
        print(f"  Distance:  {distance.min():.2f} - {distance.max():.2f} m (mean: {distance.mean():.2f} m)")
        print(f"  Azimuth:   {azimuth.min():.2f} - {azimuth.max():.2f}° (mean: {azimuth.mean():.2f}°)")
        print(f"  Elevation: {elevation.min():.2f} - {elevation.max():.2f}° (mean: {elevation.mean():.2f}°)")
        
        return targets
    
    def spherical_to_cartesian(self, distance, azimuth_deg, elevation_deg, bs_position):
        """Convert spherical coordinates (from BS) to Cartesian 3D position
        
        Args:
            distance: Distance from BS (m)
            azimuth_deg: Azimuth angle (degrees, 0° = North, clockwise)
            elevation_deg: Elevation angle (degrees, negative = below BS)
            bs_position: BS position [x, y, z]
            
        Returns:
            UE position [x, y, z]
        """
        # Convert to radians
        azimuth_rad = azimuth_deg * np.pi / 180
        elevation_rad = elevation_deg * np.pi / 180
        
        # Compute horizontal distance
        horizontal_dist = distance * np.cos(elevation_rad)
        
        # Compute relative position from BS
        dx = horizontal_dist * np.sin(azimuth_rad)
        dy = horizontal_dist * np.cos(azimuth_rad)
        dz = -distance * np.sin(elevation_rad)
        
        # Add BS position
        if distance.ndim == 0:  # scalar
            ue_pos = bs_position + np.array([dx, dy, dz])
        else:  # array
            ue_pos = bs_position + np.column_stack([dx, dy, dz])
        
        return ue_pos


class DataSplitter:
    """Handle train/test splitting"""
    
    def __init__(self, test_ratio=0.2, random_seed=42, split_method='random'):
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.split_method = split_method
    
    def split(self, n_samples):
        """Split data indices"""
        if self.split_method == 'temporal':
            train_cutoff = int(n_samples * (1 - self.test_ratio))
            train_indices = np.arange(0, train_cutoff)
            test_indices = np.arange(train_cutoff, n_samples)
        else:
            np.random.seed(self.random_seed)
            all_indices = np.arange(n_samples)
            np.random.shuffle(all_indices)
            
            n_test = int(n_samples * self.test_ratio)
            test_indices = all_indices[:n_test]
            train_indices = all_indices[n_test:]
        
        return train_indices, test_indices


class RegressionPipeline:
    """Main regression pipeline"""
    
    def __init__(self, data_dir, output_dir=None, test_ratio=0.2, split_method='random', max_history=0, 
                 n_estimators=100, max_depth=None, min_samples_split=2, min_samples_leaf=1):
        t_start = time.time()
        self.data = RegressionData(data_dir)
        t_load = time.time() - t_start
        
        self.output_dir = Path(output_dir) if output_dir else self._create_output_dir()
        self.splitter = DataSplitter(test_ratio=test_ratio, split_method=split_method)
        self.max_history = max_history
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.results = {}
        self.timing = {'data_loading': t_load}
    
    def _create_output_dir(self):
        """Create timestamped output directory"""
        scenario = self.data.config['channel']['scenario']
        los_nlos = 'LOS' if 'LOS' in scenario and 'NLOS' not in scenario else 'NLOS'
        grid_size = self.data.config['grid']['size']
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = PROJECT_ROOT / f"results/grid_localization/grid_{grid_size}x{grid_size}/exp_regression_{los_nlos}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def _stack_history_features(self, X, h):
        """Stack h previous samples with current sample
        
        Args:
            X: Feature matrix [N x D]
            h: History length
            
        Returns:
            X_stacked: [N x (h+1)*D] with first h samples dropped
            valid_indices: Indices after dropping initial h samples
        """
        if h == 0:
            return X, np.arange(len(X))
        
        N, D = X.shape if X.ndim > 1 else (len(X), 1)
        X_reshaped = X.reshape(N, D) if X.ndim == 1 else X
        
        # Create stacked features: [X[i-h], ..., X[i-1], X[i]]
        X_stacked_list = []
        for offset in range(h, -1, -1):
            if offset == 0:
                X_stacked_list.append(X_reshaped[h:])
            else:
                X_stacked_list.append(X_reshaped[h-offset:-offset])
        
        X_stacked = np.hstack(X_stacked_list)
        valid_indices = np.arange(h, N)
        
        return X_stacked, valid_indices
    
    def _prepare_features(self, feature_spec):
        """Prepare feature matrix (always returns 2D)"""
        if isinstance(feature_spec, str):
            vals = self.data.metrics[feature_spec.lower()]
            return feature_spec, vals.reshape(-1, 1) if vals.ndim == 1 else vals
        elif isinstance(feature_spec, list):
            feature_name = '+'.join(feature_spec)
            feature_arrays = [self.data.metrics[f.lower()] for f in feature_spec]
            feature_values = np.column_stack(feature_arrays)
            return feature_name, feature_values
        else:
            raise ValueError(f"Invalid feature specification: {feature_spec}")
    
    def run(self, features_to_test=None, model_type='random_forest'):
        """Run regression pipeline"""
        t_start = time.time()
        
        # Use all available features if not specified
        if features_to_test is None:
            features_to_test = [list(self.data.metrics.keys())]
        
        print(f"\n{'='*70}")
        print(f"3D REGRESSION PIPELINE")
        print(f"{'='*70}")
        print(f"Output directory: {self.output_dir}")
        print(f"Model type: {model_type}")
        print(f"Split method: {self.splitter.split_method}")
        print(f"Max history: {self.max_history}")
        
        # Split data (will be adjusted for valid indices after stacking)
        train_idx_full, test_idx_full = self.splitter.split(self.data.n_samples)
        
        # Evaluate each feature set with history values
        for h in range(self.max_history + 1):
            for feature_spec in features_to_test:
                feature_name, X = self._prepare_features(feature_spec)
                
                # Stack history features
                X_stacked, valid_idx = self._stack_history_features(X, h)
                
                # Adjust split indices for valid samples
                train_idx = train_idx_full[train_idx_full >= h]
                test_idx = test_idx_full[test_idx_full >= h]
                
                # Map to stacked indices (subtract h)
                train_idx_mapped = train_idx - h
                test_idx_mapped = test_idx - h
                
                history_suffix = f" (h={h})" if h > 0 else ""
                
                print(f"\n{'-'*70}")
                print(f"Features: {feature_name}{history_suffix}")
                if X_stacked.ndim > 1:
                    print(f"Feature dimension: {X_stacked.shape[1]} (base: {X.shape[1] if X.ndim > 1 else 1}, history: {h})")
                print(f"Data split: {len(train_idx_mapped)} train, {len(test_idx_mapped)} test")
                print(f"{'-'*70}")
                
                # Train model
                t_train = time.time()

                if model_type == 'random_forest':
                    model = RandomForestRegressor(
                        n_estimators=self.n_estimators,
                        max_depth=self.max_depth,
                        min_samples_split=self.min_samples_split,
                        min_samples_leaf=self.min_samples_leaf,
                        random_state=42,
                        n_jobs=-1
                    )
                    print(f"Training RandomForest(n_estimators={self.n_estimators}, max_depth={self.max_depth})...")
                elif model_type == 'xgboost':
                    model = MultiOutputRegressor(XGBRegressor(
                        n_estimators=self.n_estimators,
                        max_depth=6,
                        learning_rate=0.1,
                        random_state=42,
                        n_jobs=4
                    ))
                    print(f"Training XGBoost(n_estimators={self.n_estimators}, max_depth=6, lr=0.1)...")
                else:
                    raise ValueError(f"Unknown model type: {model_type}")
                
                X_train = X_stacked[train_idx_mapped]
                y_train = self.data.targets[valid_idx][train_idx_mapped]
            
                model.fit(X_train, y_train)
                train_time = time.time() - t_train
                
                # Evaluate
                print("Evaluating model...")
                t_eval = time.time()
                
                X_test = X_stacked[test_idx_mapped]
                y_test = self.data.targets[valid_idx][test_idx_mapped]
                y_pred = model.predict(X_test)
            
                eval_time = time.time() - t_eval
                
                # Compute 3D position error (comparable to classification MAE)
                ue_positions_true = self.data.ue_positions[valid_idx][test_idx_mapped]
                ue_positions_pred = self.data.spherical_to_cartesian(
                    y_pred[:, 0], y_pred[:, 1], y_pred[:, 2], self.data.bs_position
                )
                position_errors_3d = np.linalg.norm(ue_positions_true - ue_positions_pred, axis=1)
                position_mae_3d = np.mean(position_errors_3d)
                
                # Compute metrics for each target
                target_names = ['Distance (m)', 'Azimuth (°)', 'Elevation (°)']
                results = {}
                
                print("\nResults:")
                print(f"{'Target':15s} {'MAE':>10s} {'RMSE':>10s} {'R²':>10s}")
                print('-' * 50)
                
                for i, name in enumerate(target_names):
                    mae = mean_absolute_error(y_test[:, i], y_pred[:, i])
                    rmse = np.sqrt(mean_squared_error(y_test[:, i], y_pred[:, i]))
                    r2 = r2_score(y_test[:, i], y_pred[:, i])
                    
                    results[name] = {'MAE': mae, 'RMSE': rmse, 'R2': r2}
                    
                    print(f"{name:15s} {mae:10.3f} {rmse:10.3f} {r2:10.3f}")
                
                # Add 3D position error
                results['3D Position Error'] = {'MAE': position_mae_3d}
                print('-' * 50)
                print(f"{'3D Position (m)':15s} {position_mae_3d:10.3f}    (comparable to classification)")
                
                # Save results
                result_key = f"{feature_name}{history_suffix}"
                self.results[result_key] = {
                    'results': results,
                    'history': h,
                    'train_time': train_time,
                    'eval_time': eval_time,
                    'predictions': y_pred,
                    'ground_truth': y_test,
                    'position_mae_3d': position_mae_3d,
                    'position_errors_3d': position_errors_3d
                }
                
                # Save results to disk for per-cell analysis
                if h == 0:  # Save baseline h=0 for per-cell analysis
                    results_file = self.output_dir / f'results_h{h}.npz'
                    np.savez(results_file,
                            y_test=y_test,
                            y_pred=y_pred,
                            test_indices=test_idx)
        
        # Generate report
        self.generate_report()
        
        total_time = time.time() - t_start
        print(f"\n{'='*70}")
        print(f"TOTAL TIME: {total_time:.2f}s")
        print(f"{'='*70}\n")
    
    def generate_report(self):
        """Generate markdown report"""
        report_file = self.output_dir / 'REGRESSION_REPORT.md'
        
        with open(report_file, 'w') as f:
            f.write('# 3D Regression Localization Results\n\n')
            f.write(f'**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            # Configuration
            scenario = self.data.config['channel']['scenario']
            grid_size = self.data.config['grid']['size']
            
            f.write('## Configuration\n\n')
            f.write('```\n')
            f.write(f'Scenario:        {scenario}\n')
            f.write(f'Grid Size:       {grid_size}x{grid_size}\n')
            f.write(f'Total Samples:   {self.data.n_samples}\n')
            f.write(f'Split Method:    {self.splitter.split_method}\n')
            f.write(f'Task:            3D Regression (Distance + Azimuth + Elevation)\n')
            f.write('```\n\n')
            
            # Results table
            f.write('## Results Summary\n\n')
            
            for feature_name, result in self.results.items():
                f.write(f'### Features: {feature_name}\n\n')
                f.write('| Target | MAE | RMSE | R² |\n')
                f.write('|:-------|:----|:-----|:---|\n')
                
                for target, metrics in result['results'].items():
                    if target == '3D Position Error':
                        f.write(f"| **{target}** | **{metrics['MAE']:.3f} m** | - | - |\n")
                    else:
                        f.write(f"| {target} | {metrics['MAE']:.3f} | {metrics['RMSE']:.3f} | {metrics['R2']:.3f} |\n")
                
                f.write(f"\n**3D Position MAE:** {result['position_mae_3d']:.3f} m (comparable to classification)\n")
                f.write(f"**Training time:** {result['train_time']:.2f}s\n")
                f.write(f"**Evaluation time:** {result['eval_time']:.2f}s\n\n")
            
            f.write('---\n\n')
            f.write('*Generated by localization_pipeline_regression.py*\n')
        
        print(f"\n[OK] Report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description='3D Regression Localization Pipeline')
    parser.add_argument('--data-dir', required=True, help='Directory with simulation data')
    parser.add_argument('--output-dir', help='Output directory (auto-generated if not specified)')
    parser.add_argument('--test-ratio', type=float, default=0.2, help='Test set ratio')
    parser.add_argument('--split-method', choices=['random', 'temporal'], default='temporal',
                       help='Train/test split strategy')
    parser.add_argument('--model', choices=['random_forest', 'xgboost'], default='random_forest',
                       help='Model type to use')
    parser.add_argument('--max-history', type=int, default=3,
                       help='Maximum history length to test (0 to max_history)')
    parser.add_argument('--metrics', nargs='+', default=None,
                       help='Metric combinations to test (comma-separated per combo). '
                            'E.g.: rss sinr "rss,sinr" "rss,sinr,aoa_azimuth"')
    
    # Random Forest hyperparameters
    parser.add_argument('--n-estimators', type=int, default=100,
                       help='Number of trees in Random Forest (default: 100)')
    parser.add_argument('--max-depth', type=int, default=None,
                       help='Maximum depth of trees (default: None = unlimited)')
    parser.add_argument('--min-samples-split', type=int, default=2,
                       help='Minimum samples required to split a node (default: 2)')
    parser.add_argument('--min-samples-leaf', type=int, default=1,
                       help='Minimum samples required at leaf node (default: 1)')
    
    args = parser.parse_args()
    
    # Run pipeline (uses all available features)
    pipeline = RegressionPipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        test_ratio=args.test_ratio,
        split_method=args.split_method,
        max_history=args.max_history,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_split=args.min_samples_split,
        min_samples_leaf=args.min_samples_leaf
    )
    
    # Parse metric combinations
    features_to_test = None
    if args.metrics:
        features_to_test = []
        for spec in args.metrics:
            parts = [m.strip() for m in spec.split(',')]
            features_to_test.append(parts if len(parts) > 1 else parts[0])

    pipeline.run(features_to_test=features_to_test, model_type=args.model)


if __name__ == '__main__':
    main()
