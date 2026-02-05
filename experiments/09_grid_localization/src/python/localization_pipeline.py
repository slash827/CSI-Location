"""
Modular Localization Pipeline

This script handles the complete localization analysis pipeline:
- Load simulation data (from MATLAB or existing results)
- Train/test split
- Model training (statistical or ML)
- Evaluation and metrics
- Report generation

Design Philosophy:
- Modular: Easy to swap between statistical models and ML models
- Reusable: Can load pre-existing simulation data
- Extensible: Easy to add new models or metrics

Usage:
    # Run full pipeline on new simulation data:
    python localization_pipeline.py --data-dir results/sim_data/run_001
    
    # Re-analyze existing results with different model:
    python localization_pipeline.py --data-dir results/sim_data/run_001 --model ml
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.io import loadmat, savemat
from scipy.stats import norm
from datetime import datetime
from abc import ABC, abstractmethod
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
import time
from read_jsonc import read_jsonc


class SimulationData:
    """Container for simulation data loaded from MATLAB"""
    
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.load_data()
    
    def load_data(self):
        """Load simulation data from directory"""
        # Load raw simulation data
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
        
        # Extract data
        self.metrics = {
            'rss': data['metrics'].rss_wb,
            'sinr': data['metrics'].sinr_wb,
            'cqi': data['metrics'].cqi_wb
        }
        
        # Add AoA and Timing Advance if available (backward compatibility)
        if hasattr(data['metrics'], 'aoa_azimuth'):
            aoa_az = data['metrics'].aoa_azimuth
            # Apply realistic impairments if configured in ml_config
            if self.ml_config.get('realistic_aoa', {}).get('enabled', False):
                noise_std = self.ml_config['realistic_aoa']['noise_std_deg']
                quant_step = self.ml_config['realistic_aoa']['quantization_deg']
                np.random.seed(42)  # Reproducible noise
                aoa_az = aoa_az + noise_std * np.random.randn(len(aoa_az))
                aoa_az = np.round(aoa_az / quant_step) * quant_step
            self.metrics['aoa_azimuth'] = aoa_az
            
        if hasattr(data['metrics'], 'aoa_elevation'):
            aoa_el = data['metrics'].aoa_elevation
            # Apply realistic impairments if configured in ml_config
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
        
        self.true_locations = data['walk_path'].grid_point_indices
        self.grid_positions = data['config'].grid_positions
        self.neighbors = self._convert_neighbors(data['config'].neighbors)
        self.n_points = int(data['config'].n_points)
        self.n_samples = len(self.true_locations)
        
        available_metrics = ', '.join(self.metrics.keys())
        print(f"[OK] Loaded {self.n_samples} samples across {self.n_points} grid points")
        print(f"     Available metrics: {available_metrics}")
    
    def _convert_neighbors(self, neighbors_cell):
        """Convert MATLAB cell array to Python dict"""
        neighbors_dict = {}
        for i in range(len(neighbors_cell)):
            neighs = neighbors_cell[i]
            if np.isscalar(neighs):
                neighbors_dict[i] = [int(neighs)]
            else:
                neighbors_dict[i] = [int(n) for n in neighs]
        return neighbors_dict


class DataSplitter:
    """Handle train/test splitting with support for static and transition modes"""
    
    def __init__(self, test_ratio=0.2, random_seed=42, split_method='random'):
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.split_method = split_method
    
    def split_static(self, n_samples):
        """Random or Temporal train/test split for static classification"""
        
        if self.split_method == 'temporal':
            # Sequential split - train on early trajectory, test on later
            train_cutoff = int(n_samples * (1 - self.test_ratio))
            train_indices = np.arange(0, train_cutoff)
            test_indices = np.arange(train_cutoff, n_samples)
        else:
            # Random split (default)
            np.random.seed(self.random_seed)
            all_indices = np.arange(n_samples)
            np.random.shuffle(all_indices)
            
            n_test = int(n_samples * self.test_ratio)
            test_indices = all_indices[:n_test]
            train_indices = all_indices[n_test:]
        
        return train_indices, test_indices
    
    def split_transition(self, n_samples, max_history=3):
        """Split for transition-based approach (exclude early samples without history)"""
        
        if self.split_method == 'temporal':
            # Can't use samples without enough history even in temporal split
            # Start after max_history
            valid_start = max_history
            n_valid = n_samples - valid_start
            
            train_cutoff = valid_start + int(n_valid * (1 - self.test_ratio))
            
            train_indices = np.arange(valid_start, train_cutoff)
            test_indices = np.arange(train_cutoff, n_samples)
        else:
            # Random split
            np.random.seed(self.random_seed)
            
            # Can't use samples without enough history
            valid_indices = np.arange(max_history, n_samples)
            np.random.shuffle(valid_indices)
            
            n_test = int(len(valid_indices) * self.test_ratio)
            test_indices = valid_indices[:n_test]
            train_indices = valid_indices[n_test:]
        
        return train_indices, test_indices


class LocalizationModel(ABC):
    """Abstract base class for localization models"""
    
    @abstractmethod
    def train(self, metric_values, true_locations, train_indices, n_points):
        """Train the model"""
        pass
    
    @abstractmethod
    def predict(self, metric_value):
        """Predict location given metric value, returns probabilities"""
        pass
    
    @abstractmethod
    def get_name(self):
        """Return model name"""
        pass


class GaussianStaticModel(LocalizationModel):
    """Gaussian statistical model for static localization"""
    
    def __init__(self):
        self.models = []
        self.name = "Gaussian (Static)"
    
    def train(self, metric_values, true_locations, train_indices, n_points):
        """Train Gaussian model for each grid point"""
        self.models = []
        
        for point_idx in range(n_points):
            # Find samples at this location (convert to 0-indexed)
            samples_at_point = []
            for idx in train_indices:
                if true_locations[idx] == point_idx + 1:  # MATLAB uses 1-indexed
                    samples_at_point.append(metric_values[idx])
            
            if len(samples_at_point) > 0:
                mean = np.mean(samples_at_point)
                std = np.std(samples_at_point)
                if std == 0 or not np.isfinite(std):
                    std = 1e-6
            else:
                mean = 0
                std = 1e-6
            
            self.models.append({
                'mean': mean,
                'std': std,
                'n_samples': len(samples_at_point)
            })
    
    def predict(self, metric_value):
        """Compute posterior probability for each location"""
        n_points = len(self.models)
        posterior = np.zeros(n_points)
        
        for i, model in enumerate(self.models):
            posterior[i] = norm.pdf(metric_value, model['mean'], model['std'])
        
        # Normalize
        if posterior.sum() > 0:
            posterior = posterior / posterior.sum()
        
        return posterior
    
    def get_name(self):
        return self.name


class GaussianTransitionModel(LocalizationModel):
    """Gaussian model with transition delta information"""
    
    def __init__(self, neighbors, history_length=1):
        self.neighbors = neighbors
        self.history_length = history_length
        self.static_models = []
        self.transition_models = {}
        self.name = f"Gaussian (Transition h={history_length})"
        
        # Build reverse neighbor lookup for efficiency
        # reverse_neighbors[loc] = list of locations that have `loc` as a neighbor
        self.reverse_neighbors = {}
        for loc_idx, neighs in neighbors.items():
            for neigh_id in neighs:
                if neigh_id not in self.reverse_neighbors:
                    self.reverse_neighbors[neigh_id] = []
                self.reverse_neighbors[neigh_id].append(loc_idx)
    
    def train(self, metric_values, true_locations, train_indices, n_points):
        """Train both static and transition models"""
        # Train static models
        self.static_models = []
        for point_idx in range(n_points):
            samples_at_point = []
            for idx in train_indices:
                if true_locations[idx] == point_idx + 1:
                    samples_at_point.append(metric_values[idx])
            
            if len(samples_at_point) > 0:
                mean = np.mean(samples_at_point)
                std = np.std(samples_at_point)
                if std == 0 or not np.isfinite(std):
                    std = 1e-6
            else:
                mean = 0
                std = 1e-6
            
            self.static_models.append({'mean': mean, 'std': std})
        
        # Train transition models (delta distributions)
        self.transition_models = {}
        n_valid_transitions = 0
        
        for idx in train_indices[1:]:  # Need previous sample
            prev_loc = true_locations[idx - 1]  # 1-indexed
            curr_loc = true_locations[idx]  # 1-indexed
            
            # Check if this is a valid transition (neighbors)
            # neighbors has 0-indexed keys but 1-indexed values
            if curr_loc in self.neighbors.get(prev_loc - 1, []):
                key = f"{prev_loc}_{curr_loc}"
                # Convert to float to avoid overflow with uint8 data types
                delta = float(metric_values[idx]) - float(metric_values[idx - 1])
                
                if key not in self.transition_models:
                    self.transition_models[key] = []
                self.transition_models[key].append(delta)
                n_valid_transitions += 1
        
        print(f"  [DEBUG] Collected {n_valid_transitions} valid transitions, {len(self.transition_models)} unique paths")
        
        # Compute statistics for each transition
        for key in self.transition_models:
            deltas = self.transition_models[key]
            mean_delta = np.mean(deltas)
            std_delta = np.std(deltas)
            if std_delta == 0 or not np.isfinite(std_delta):
                std_delta = 1e-6
            self.transition_models[key] = {
                'mean_delta': mean_delta,
                'std_delta': std_delta,
                'n_samples': len(deltas)
            }
    
    def predict(self, metric_value, previous_values=None, previous_location=None):
        """Predict using both current value and transition info
        
        Args:
            metric_value: Current metric observation
            previous_values: List of previous metric values [t-h, t-h+1, ..., t-1]
                           For h=1: [value at t-1]
                           For h=2: [value at t-2, value at t-1]
                           For h=3: [value at t-3, value at t-2, value at t-1]
            previous_location: Previous known location (1-indexed) - if known (not used in evaluation)
        """
        n_points = len(self.static_models)
        posterior = np.zeros(n_points)
        
        if previous_values is None or len(previous_values) == 0:
            # Fall back to static only
            for i, model in enumerate(self.static_models):
                posterior[i] = norm.pdf(metric_value, model['mean'], model['std'])
        else:
            # Use transition information with log probabilities to avoid underflow
            # Compute all deltas in the sequence
            history_len = min(len(previous_values), self.history_length)
            
            # Build list of metric values: [t-h, t-h+1, ..., t-1, t]
            # Convert to float to avoid overflow with uint8 data types (e.g., CQI)
            metric_sequence = [float(v) for v in previous_values[-history_len:]] + [float(metric_value)]
            
            # Compute deltas: delta[i] = metric_sequence[i+1] - metric_sequence[i]
            deltas_observed = np.diff(metric_sequence)
            
            # OPTIMIZATION: Pre-compute PDF values for all transition models with observed deltas
            # This avoids recomputing norm.logpdf millions of times in nested loops
            delta_logpdfs = {}  # key -> list of log probabilities for each delta
            for key, model in self.transition_models.items():
                delta_logpdfs[key] = [
                    norm.logpdf(delta, model['mean_delta'], model['std_delta'])
                    for delta in deltas_observed
                ]
            
            log_posterior = np.full(n_points, -np.inf)  # Initialize with -inf (log(0))
            
            for curr_loc in range(n_points):
                # Static log-likelihood for current position
                log_prob_static = norm.logpdf(metric_value, 
                                             self.static_models[curr_loc]['mean'],
                                             self.static_models[curr_loc]['std'])
                
                # Find best path through history using dynamic exploration
                max_log_path_prob = -np.inf
                
                if history_len == 1:
                    # Single transition: only check locations that can reach curr_loc
                    # Use reverse neighbor lookup for efficiency
                    prev_locs = self.reverse_neighbors.get(curr_loc + 1, [])
                    for prev_loc_idx in prev_locs:
                        key = f"{prev_loc_idx + 1}_{curr_loc + 1}"
                        if key not in delta_logpdfs:
                            continue
                        
                        log_prob_delta = delta_logpdfs[key][0]
                        if log_prob_delta > max_log_path_prob:
                            max_log_path_prob = log_prob_delta
                
                elif history_len == 2:
                    # Two transitions: explore paths (prev2 → prev1 → curr)
                    # Use reverse neighbors for efficiency
                    prev_locs = self.reverse_neighbors.get(curr_loc + 1, [])
                    for prev_loc_idx in prev_locs:
                        key1 = f"{prev_loc_idx + 1}_{curr_loc + 1}"
                        if key1 not in delta_logpdfs:
                            continue
                        
                        log_prob1 = delta_logpdfs[key1][1]  # Most recent delta
                        
                        # Check second transition: find locations that can reach prev_loc_idx
                        prev2_locs = self.reverse_neighbors.get(prev_loc_idx + 1, [])
                        for prev_loc2_idx in prev2_locs:
                            key2 = f"{prev_loc2_idx + 1}_{prev_loc_idx + 1}"
                            if key2 not in delta_logpdfs:
                                continue
                            
                            log_prob2 = delta_logpdfs[key2][0]  # Older delta
                            
                            # Path probability = product of transition probabilities
                            log_path_prob = log_prob1 + log_prob2
                            if log_path_prob > max_log_path_prob:
                                max_log_path_prob = log_path_prob
                
                elif history_len >= 3:
                    # Three+ transitions: explore paths (prev3 → prev2 → prev1 → curr)
                    prev_locs = self.reverse_neighbors.get(curr_loc + 1, [])
                    for prev_loc_idx in prev_locs:
                        key1 = f"{prev_loc_idx + 1}_{curr_loc + 1}"
                        if key1 not in delta_logpdfs:
                            continue
                        
                        log_prob1 = delta_logpdfs[key1][2 if len(deltas_observed) > 2 else -1]
                        
                        prev2_locs = self.reverse_neighbors.get(prev_loc_idx + 1, [])
                        for prev_loc2_idx in prev2_locs:
                            key2 = f"{prev_loc2_idx + 1}_{prev_loc_idx + 1}"
                            if key2 not in delta_logpdfs:
                                continue
                            
                            log_prob2 = delta_logpdfs[key2][1 if len(deltas_observed) > 1 else 0]
                            
                            prev3_locs = self.reverse_neighbors.get(prev_loc2_idx + 1, [])
                            for prev_loc3_idx in prev3_locs:
                                key3 = f"{prev_loc3_idx + 1}_{prev_loc2_idx + 1}"
                                if key3 not in delta_logpdfs:
                                    continue
                                
                                log_prob3 = delta_logpdfs[key3][0]
                                
                                # Path probability = product of all transitions
                                log_path_prob = log_prob1 + log_prob2 + log_prob3
                                if log_path_prob > max_log_path_prob:
                                    max_log_path_prob = log_path_prob
                
                # Combine in log space: log(a*b) = log(a) + log(b)
                if max_log_path_prob > -np.inf:
                    log_posterior[curr_loc] = log_prob_static + max_log_path_prob
            
            # Convert back from log space
            # Use log-sum-exp trick for numerical stability
            if np.all(np.isinf(log_posterior)):
                # All probabilities are zero, fall back to static only
                for i, model in enumerate(self.static_models):
                    posterior[i] = norm.pdf(metric_value, model['mean'], model['std'])
            else:
                max_log = np.max(log_posterior[np.isfinite(log_posterior)])
                posterior = np.exp(log_posterior - max_log)
        
        # Normalize
        if posterior.sum() > 0:
            posterior = posterior / posterior.sum()
        else:
            # Ultimate fallback: uniform distribution
            posterior = np.ones(n_points) / n_points
        
        return posterior
    
    def get_name(self):
        return self.name


class RandomForestModel(LocalizationModel):
    """Random Forest classifier for localization
    
    Advantages:
    - Handles multiple features naturally (can combine RSS + SINR)
    - Learns non-linear relationships
    - Captures feature interactions automatically
    - No Gaussian assumption needed
    - Good with high-dimensional data
    """
    
    def __init__(self, use_transition=False, history_length=1, n_estimators=100, max_depth=30, n_jobs=4):
        """
        Args:
            use_transition: If True, include history as features
            history_length: Number of previous timesteps to include
            n_estimators: Number of trees in the forest
            max_depth: Maximum depth of trees (limits memory usage)
            n_jobs: Number of parallel jobs (reduce for memory constraints)
        """
        self.use_transition = use_transition
        self.history_length = history_length
        self.n_estimators = n_estimators
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,  # Limit tree depth to prevent memory explosion
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=n_jobs  # Reduce parallelism to limit memory usage
        )
        mode = "Transition" if use_transition else "Static"
        self.name = f"RandomForest ({mode}, h={history_length})"
    
    def train(self, metric_values, true_locations, train_indices, n_points):
        """Train random forest classifier
        
        Args:
            metric_values: Can be 1D array (single metric) or 2D array (multiple metrics)
                          Shape: (n_samples,) or (n_samples, n_features)
            true_locations: Array of location labels (1-indexed from MATLAB)
            train_indices: Indices to use for training
            n_points: Number of grid points
        """
        # Ensure metric_values is 2D
        if metric_values.ndim == 1:
            metric_values = metric_values.reshape(-1, 1)
        
        n_samples, n_base_features = metric_values.shape
        
        # Build feature matrix
        if self.use_transition and self.history_length > 0:
            # Include history as features
            features_list = []
            labels_list = []
            
            for idx in train_indices:
                if idx < self.history_length:
                    continue  # Skip if not enough history
                
                # Current + history features
                feature_vec = []
                for h in range(self.history_length + 1):
                    feature_vec.extend(metric_values[idx - h])
                
                features_list.append(feature_vec)
                labels_list.append(true_locations[idx])
            
            X_train = np.array(features_list)
            y_train = np.array(labels_list)
        else:
            # Static: just current features
            X_train = metric_values[train_indices]
            y_train = true_locations[train_indices]
        
        # Train model
        self.model.fit(X_train, y_train)
        self.n_base_features = n_base_features
    
    def predict(self, metric_value, previous_values=None):
        """Predict location probabilities
        
        Args:
            metric_value: Current observation(s), can be scalar or array
            previous_values: List of previous observations (if use_transition=True)
                           Each element can be scalar or array
        
        Returns:
            Array of probabilities for each location
        """
        # Ensure metric_value is array
        if np.isscalar(metric_value):
            metric_value = np.array([metric_value])
        elif metric_value.ndim == 0:
            metric_value = metric_value.reshape(1)
        
        # Build feature vector
        if self.use_transition and previous_values is not None:
            feature_vec = []
            
            # Must match training order: current, then history (t-1, t-2, ..., t-h)
            # Add current value first
            feature_vec.extend(metric_value if hasattr(metric_value, '__iter__') else [metric_value])
            
            # Add history: from most recent (t-1) to oldest (t-history_length)
            # Training uses: for h in range(history_length+1): extend(metric_values[idx-h])
            # This gives: [idx-0 (current), idx-1, idx-2, ..., idx-history_length]
            # previous_values comes as [idx-history_length, ..., idx-2, idx-1] (oldest to newest)
            # So we need to REVERSE it to get [idx-1, idx-2, ..., idx-history_length]
            n_history_needed = self.history_length
            if len(previous_values) < n_history_needed:
                # Pad with zeros if not enough history (shouldn't happen in evaluation)
                previous_values = [0] * (n_history_needed - len(previous_values)) + list(previous_values)
            
            # Take the last history_length values and reverse to match training order
            history_to_use = previous_values[-n_history_needed:] if len(previous_values) >= n_history_needed else previous_values
            history_to_use = list(reversed(history_to_use))  # Reverse to get [t-1, t-2, ..., t-h]
            
            for prev_val in history_to_use:
                if np.isscalar(prev_val):
                    feature_vec.append(prev_val)
                else:
                    feature_vec.extend(prev_val if hasattr(prev_val, '__iter__') else [prev_val])
            
            X = np.array(feature_vec).reshape(1, -1)
        else:
            # Static mode
            X = metric_value.reshape(1, -1)
        
        # Get probability predictions
        proba = self.model.predict_proba(X)[0]
        
        # Return probabilities in the order of classes
        # Note: sklearn classes are sorted, need to map back to grid points
        n_classes = len(self.model.classes_)
        posterior = np.zeros(n_classes)
        for i, class_label in enumerate(self.model.classes_):
            # class_label is 1-indexed from MATLAB, convert to 0-indexed
            posterior[int(class_label) - 1] = proba[i]
        
        return posterior
    
    def get_name(self):
        return self.name


class Evaluator:
    """Evaluate model performance"""
    
    @staticmethod
    def compute_spatial_mae(predictions, true_labels, grid_positions):
        """Compute MAE in meters using actual grid positions
        
        Args:
            predictions: Predicted location labels (1-indexed)
            true_labels: True location labels (1-indexed)
            grid_positions: (N, 2) array of (x, y) coordinates for each grid point
        
        Returns:
            mae_meters: Mean absolute error in meters
        """
        # Convert labels to 0-indexed
        pred_idx = predictions.astype(int) - 1
        true_idx = true_labels.astype(int) - 1
        
        # Get coordinates
        pred_coords = grid_positions[pred_idx]
        true_coords = grid_positions[true_idx]
        
        # Compute Euclidean distance
        distances = np.sqrt(np.sum((pred_coords - true_coords)**2, axis=1))
        mae_meters = np.mean(distances)
        
        return mae_meters
    
    @staticmethod
    def evaluate_static(model, metric_values, true_locations, test_indices, grid_positions=None):
        """Evaluate static classification"""
        predictions = []
        
        for idx in test_indices:
            posterior = model.predict(metric_values[idx])
            pred_location = np.argmax(posterior) + 1  # Convert to 1-indexed
            predictions.append(pred_location)
        
        # Compute metrics
        predictions = np.array(predictions)
        true_labels = np.array([true_locations[idx] for idx in test_indices])
        
        accuracy = np.mean(predictions == true_labels) * 100
        
        # Compute MAE in meters if grid_positions provided
        if grid_positions is not None:
            mae = Evaluator.compute_spatial_mae(predictions, true_labels, grid_positions)
        else:
            # Fallback to label difference (for backward compatibility)
            mae = np.mean(np.abs(predictions - true_labels))
        
        # Confusion matrix
        n_points = len(np.unique(true_locations))
        cm = np.zeros((n_points, n_points))
        for true_loc, pred_loc in zip(true_labels, predictions):
            cm[int(true_loc) - 1, int(pred_loc) - 1] += 1
        
        return {
            'accuracy': accuracy,
            'mae': mae,
            'predictions': predictions,
            'true_labels': true_labels,
            'confusion_matrix': cm
        }
    
    @staticmethod
    def evaluate_transition(model, metric_values, true_locations, test_indices, grid_positions=None):
        """Evaluate transition-based classification
        
        NOTE: This follows the MATLAB approach - we do NOT use ground truth previous location.
        Instead, we marginalize over all possible previous locations (neighbors).
        We also pass ALL previous values in the history window to compute multiple deltas.
        """
        predictions = []
        valid_test_indices = []
        
        # Get history length from model
        history_length = getattr(model, 'history_length', 1)
        
        # Check model type to use appropriate interface
        is_gaussian = isinstance(model, GaussianTransitionModel)
        
        for idx in test_indices:
            if idx >= history_length:  # Need enough history
                if is_gaussian:
                    # GaussianTransitionModel: Pass ALL previous values for history window
                    # Collect [t-h, t-h+1, ..., t-1]
                    previous_values = [metric_values[idx - h] for h in range(history_length, 0, -1)]
                    posterior = model.predict(metric_values[idx], 
                                            previous_values=previous_values,
                                            previous_location=None)  # Don't use ground truth!
                else:
                    # RandomForestModel: Pass list of previous values
                    previous_values = [metric_values[idx - h] for h in range(history_length, 0, -1)]
                    posterior = model.predict(metric_values[idx], previous_values=previous_values)
                
                pred_location = np.argmax(posterior) + 1
                predictions.append(pred_location)
                valid_test_indices.append(idx)
        
        # Compute metrics
        predictions = np.array(predictions)
        true_labels = np.array([true_locations[idx] for idx in valid_test_indices])
        
        accuracy = np.mean(predictions == true_labels) * 100
        
        # Compute MAE in meters if grid_positions provided
        if grid_positions is not None:
            mae = Evaluator.compute_spatial_mae(predictions, true_labels, grid_positions)
        else:
            # Fallback to label difference (for backward compatibility)
            mae = np.mean(np.abs(predictions - true_labels))
        
        # Confusion matrix
        n_points = len(np.unique(true_locations))
        cm = np.zeros((n_points, n_points))
        for true_loc, pred_loc in zip(true_labels, predictions):
            cm[int(true_loc) - 1, int(pred_loc) - 1] += 1
        
        return {
            'accuracy': accuracy,
            'mae': mae,
            'predictions': predictions,
            'true_labels': true_labels,
            'confusion_matrix': cm
        }


class Pipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, data_dir, output_dir=None, test_ratio=0.2, max_history=3, split_method='random'):
        t_start = time.time()
        self.data = SimulationData(data_dir)
        t_load = time.time() - t_start
        
        self.output_dir = Path(output_dir) if output_dir else self._create_output_dir()
        self.splitter = DataSplitter(test_ratio=test_ratio, split_method=split_method)
        self.max_history = max_history
        self.results = {}
        self.timing = {'data_loading': t_load}
    
    def _create_output_dir(self):
        """Create timestamped output directory"""
        scenario = self.data.config['channel']['scenario']
        los_nlos = 'LOS' if 'LOS' in scenario and 'NLOS' not in scenario else 'NLOS'
        grid_size = self.data.config['grid']['size']
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = Path(f"results/grid_localization/grid_{grid_size}x{grid_size}/exp13e_{los_nlos}_{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def _prepare_metric_data(self, metric_spec):
        """Prepare metric data based on specification
        
        Args:
            metric_spec: Either a string ('RSS') or list of strings (['RSS', 'SINR'])
        
        Returns:
            tuple: (metric_name, metric_values_array)
                  - metric_name: String identifier (e.g., 'RSS' or 'RSS+SINR')
                  - metric_values_array: 1D or 2D numpy array
        """
        if isinstance(metric_spec, str):
            # Single metric
            return metric_spec, self.data.metrics[metric_spec.lower()]
        elif isinstance(metric_spec, list):
            # Combined metrics
            metric_name = '+'.join(metric_spec)
            # Stack metrics as columns
            metric_arrays = [self.data.metrics[m.lower()] for m in metric_spec]
            metric_values = np.column_stack(metric_arrays)
            return metric_name, metric_values
        else:
            raise ValueError(f"Invalid metric specification: {metric_spec}")
    
    def run(self, metrics_to_test=['rss', 'sinr', 'cqi'], model_type='gaussian'):
        """Run complete pipeline
        
        Args:
            metrics_to_test: List of metric specifications. Each can be:
                           - String: 'rss', 'sinr', 'cqi'
                           - List: ['RSS', 'SINR'] for combined metrics
            model_type: 'gaussian' or 'random_forest'
        """
        t_pipeline_start = time.time()
        
        print(f"\n{'='*70}")
        print(f"LOCALIZATION PIPELINE")
        print(f"{'='*70}")
        print(f"Output directory: {self.output_dir}")
        print(f"Model type: {model_type}")
        print(f"Data loading time: {self.timing['data_loading']:.2f}s")
        
        # Display metrics in readable format
        metric_names = []
        for m_spec in metrics_to_test:
            if isinstance(m_spec, list):
                metric_names.append('+'.join(m_spec))
            else:
                metric_names.append(str(m_spec).upper())
        print(f"Metrics to test: {', '.join(metric_names)}")
        print(f"Max history length: {self.max_history}")
        
        # Split data
        train_static, test_static = self.splitter.split_static(self.data.n_samples)
        train_transition, test_transition = self.splitter.split_transition(
            self.data.n_samples, self.max_history
        )
        
        print(f"\nData splits:")
        print(f"  Static: {len(train_static)} train, {len(test_static)} test")
        print(f"  Transition: {len(train_transition)} train, {len(test_transition)} test")
        
        # Track timing for each metric
        self.timing['metrics'] = {}
        
        # Evaluate each metric (or metric combination)
        for metric_spec in metrics_to_test:
            t_metric_start = time.time()
            metric_name, metric_values = self._prepare_metric_data(metric_spec)
            
            print(f"\n{'-'*70}")
            print(f"Evaluating {metric_name}")
            if metric_values.ndim > 1:
                print(f"  Feature dimension: {metric_values.shape[1]}")
            print(f"{'-'*70}")
            
            metric_timing = {}
            
            # Choose model based on type
            if model_type == 'random_forest':
                # Static model
                print(f"\nTraining Random Forest (static)...")
                t_train = time.time()
                static_model = RandomForestModel(use_transition=False, history_length=0, n_estimators=100)
                static_model.train(metric_values, self.data.true_locations, 
                                 train_static, self.data.n_points)
                metric_timing['static_train'] = time.time() - t_train
                
                print(f"Evaluating static model...")
                t_eval = time.time()
                static_results = Evaluator.evaluate_static(
                    static_model, metric_values, self.data.true_locations, test_static,
                    grid_positions=self.data.grid_positions
                )
                metric_timing['static_eval'] = time.time() - t_eval
                
                print(f"  Accuracy: {static_results['accuracy']:.2f}%")
                print(f"  MAE: {static_results['mae']:.3f} meters")
                print(f"  Time: train={metric_timing['static_train']:.2f}s, eval={metric_timing['static_eval']:.2f}s")
                
                # Transition models with different history lengths
                transition_results = []
                metric_timing['transition_train'] = []
                metric_timing['transition_eval'] = []
                
                for h in range(1, self.max_history + 1):
                    print(f"\nTraining Random Forest (transition, h={h})...")
                    t_train = time.time()
                    trans_model = RandomForestModel(use_transition=True, history_length=h, n_estimators=100)
                    trans_model.train(metric_values, self.data.true_locations,
                                    train_transition, self.data.n_points)
                    metric_timing['transition_train'].append(time.time() - t_train)
                    
                    print(f"Evaluating transition model (h={h})...")
                    t_eval = time.time()
                    trans_result = Evaluator.evaluate_transition(
                        trans_model, metric_values, self.data.true_locations, test_transition,
                        grid_positions=self.data.grid_positions
                    )
                    metric_timing['transition_eval'].append(time.time() - t_eval)
                    
                    print(f"  Accuracy: {trans_result['accuracy']:.2f}%")
                    print(f"  MAE: {trans_result['mae']:.3f} meters")
                    print(f"  Time: train={metric_timing['transition_train'][-1]:.2f}s, eval={metric_timing['transition_eval'][-1]:.2f}s")
                    
                    transition_results.append(trans_result)
            
            else:  # gaussian (default)
                # Note: Gaussian models only work with 1D features (single metric)
                if metric_values.ndim > 1:
                    print(f"\n  WARNING: Gaussian models only support single metrics.")
                    print(f"           Skipping {metric_name}. Use --model random_forest instead.")
                    continue
                
                # Static model
                print(f"\nTraining Gaussian (static)...")
                t_train = time.time()
                static_model = GaussianStaticModel()
                static_model.train(metric_values, self.data.true_locations, 
                                 train_static, self.data.n_points)
                metric_timing['static_train'] = time.time() - t_train
                
                print(f"Evaluating static model...")
                t_eval = time.time()
                static_results = Evaluator.evaluate_static(
                    static_model, metric_values, self.data.true_locations, test_static,
                    grid_positions=self.data.grid_positions
                )
                metric_timing['static_eval'] = time.time() - t_eval
                
                print(f"  Accuracy: {static_results['accuracy']:.2f}%")
                print(f"  MAE: {static_results['mae']:.3f} meters")
                print(f"  Time: train={metric_timing['static_train']:.2f}s, eval={metric_timing['static_eval']:.2f}s")
                
                # Transition models with different history lengths
                transition_results = []
                metric_timing['transition_train'] = []
                metric_timing['transition_eval'] = []
                
                for h in range(1, self.max_history + 1):
                    print(f"\nTraining Gaussian (transition, h={h})...")
                    print(f"  [DEBUG] Creating model with history_length={h}")
                    t_train = time.time()
                    trans_model = GaussianTransitionModel(self.data.neighbors, history_length=h)
                    print(f"  [DEBUG] Model.history_length = {trans_model.history_length}")
                    trans_model.train(metric_values, self.data.true_locations,
                                    train_transition, self.data.n_points)
                    metric_timing['transition_train'].append(time.time() - t_train)
                    
                    print(f"Evaluating transition model (h={h})...")
                    print(f"  [DEBUG] Will skip samples with idx < {h}")
                    t_eval = time.time()
                    trans_result = Evaluator.evaluate_transition(
                        trans_model, metric_values, self.data.true_locations, test_transition,
                        grid_positions=self.data.grid_positions
                    )
                    metric_timing['transition_eval'].append(time.time() - t_eval)
                    
                    print(f"  Accuracy: {trans_result['accuracy']:.2f}%")
                    print(f"  MAE: {trans_result['mae']:.3f} meters")
                    print(f"  [DEBUG] Evaluated {len(trans_result['predictions'])} samples")
                    print(f"  Time: train={metric_timing['transition_train'][-1]:.2f}s, eval={metric_timing['transition_eval'][-1]:.2f}s")
                    
                    transition_results.append(trans_result)
            
            # Store results
            metric_timing['total'] = time.time() - t_metric_start
            self.timing['metrics'][metric_name] = metric_timing
            
            self.results[metric_name] = {
                'static': static_results,
                'transition': transition_results
            }
        
        # Save results and generate report
        t_save_start = time.time()
        self.save_results()
        self.timing['save_results'] = time.time() - t_save_start
        
        t_report_start = time.time()
        self.generate_report()
        self.timing['generate_report'] = time.time() - t_report_start
        
        self.timing['total_pipeline'] = time.time() - t_pipeline_start
        
        print(f"\n{'='*70}")
        print(f"TIMING SUMMARY")
        print(f"{'='*70}")
        print(f"Data loading:     {self.timing['data_loading']:8.2f}s")
        for metric_name, metric_timing in self.timing['metrics'].items():
            print(f"\n{metric_name}:")
            print(f"  Static train:   {metric_timing['static_train']:8.2f}s")
            print(f"  Static eval:    {metric_timing['static_eval']:8.2f}s")
            for i, (t_train, t_eval) in enumerate(zip(metric_timing['transition_train'], metric_timing['transition_eval'])):
                print(f"  Trans(h={i+1}) train: {t_train:8.2f}s")
                print(f"  Trans(h={i+1}) eval:  {t_eval:8.2f}s")
            print(f"  Total:          {metric_timing['total']:8.2f}s")
        print(f"\nSave results:     {self.timing['save_results']:8.2f}s")
        print(f"Generate report:  {self.timing['generate_report']:8.2f}s")
        print(f"{'='*70}")
        print(f"TOTAL PIPELINE:   {self.timing['total_pipeline']:8.2f}s")
        print(f"{'='*70}")
        
        print(f"\nPipeline complete! Results saved to:")
        print(f"  {self.output_dir}")
        print(f"{'='*70}\n")
    
    def save_results(self):
        """Save results to file"""
        output_file = self.output_dir / 'pipeline_results.npz'
        
        # Prepare data for saving
        save_dict = {
            'config': json.dumps(self.data.config),
            'n_samples': self.data.n_samples,
            'n_points': self.data.n_points
        }
        
        for metric, results in self.results.items():
            save_dict[f'{metric}_static_acc'] = results['static']['accuracy']
            save_dict[f'{metric}_static_mae'] = results['static']['mae']
            save_dict[f'{metric}_static_cm'] = results['static']['confusion_matrix']
            
            # Save transition results for each history length
            for h_idx, trans_result in enumerate(results['transition']):
                save_dict[f'{metric}_trans_h{h_idx+1}_acc'] = trans_result['accuracy']
                save_dict[f'{metric}_trans_h{h_idx+1}_mae'] = trans_result['mae']
                save_dict[f'{metric}_trans_h{h_idx+1}_cm'] = trans_result['confusion_matrix']
        
        np.savez(output_file, **save_dict)
        print(f"\n[OK] Results saved to: {output_file}")
    
    def generate_report(self):
        """Generate summary report"""
        report_file = self.output_dir / 'SUMMARY_REPORT.md'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('# Localization Pipeline Results\n\n')
            f.write(f'**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            f.write('## Configuration\n\n')
            f.write(f'- Scenario: {self.data.config["channel"]["scenario"]}\n')
            f.write(f'- Grid Size: {self.data.config["grid"]["size"]}x{self.data.config["grid"]["size"]}\n')
            f.write(f'- Total Samples: {self.data.n_samples}\n')
    def generate_report(self):
        """Generate summary report (MATLAB-compatible format)"""
        report_file = self.output_dir / 'SUMMARY_REPORT.md'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('# Localization Pipeline Results\n\n')
            f.write(f'**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            # Configuration section
            f.write('## Configuration\n\n')
            f.write('```\n')
            f.write(f'Scenario:        {self.data.config["channel"]["scenario"]}\n')
            f.write(f'Grid Size:       {self.data.config["grid"]["size"]}x{self.data.config["grid"]["size"]}\n')
            f.write(f'Spacing:         {self.data.config["grid"]["spacing"]} meters\n')
            f.write(f'Total Samples:   {self.data.n_samples}\n')
            f.write(f'Max History:     {self.max_history}\n')
            f.write(f'Classification:  {self.data.n_points}-class (grid points)\n')
            f.write('```\n\n')
            
            f.write('## Fair Comparison Results\n\n')
            
            # Accuracy table with multiple history lengths
            f.write('### Accuracy (Multiple History Lengths)\n\n')
            f.write('| Metric | Static | Trans(h=1) | Trans(h=2) | Trans(h=3) | Best Improvement |\n')
            f.write('|:-------|:-------|:-----------|:-----------|:-----------|:------------------|\n')
            for metric in self.results:
                static_acc = self.results[metric]['static']['accuracy']
                trans_results = self.results[metric]['transition']
                accs = [r['accuracy'] for r in trans_results]
                best_acc = max(accs)
                improvement = best_acc - static_acc
                
                f.write(f'| {metric.upper()} | {static_acc:.2f}% ')
                for acc in accs:
                    f.write(f'| {acc:.2f}% ')
                f.write(f'| **{improvement:+.2f}%** |\n')
            
            # MAE table
            f.write('\n### Mean Absolute Error (meters)\n\n')
            f.write('| Metric | Static | Trans(h=1) | Trans(h=2) | Trans(h=3) | Best Improvement (%) |\n')
            f.write('|:-------|:-------|:-----------|:-----------|:-----------|:---------------------|\n')
            for metric in self.results:
                static_mae = self.results[metric]['static']['mae']
                trans_results = self.results[metric]['transition']
                maes = [r['mae'] for r in trans_results]
                best_mae = min(maes)  # Lower is better
                improvement_pct = ((static_mae - best_mae) / static_mae) * 100 if static_mae > 0 else 0
                
                f.write(f'| {metric.upper()} | {static_mae:.3f} ')
                for mae in maes:
                    f.write(f'| {mae:.3f} ')
                f.write(f'| **{improvement_pct:+.2f}%** |\n')
            
            f.write('\n*Note: h=1 uses last transition, h=2 uses last 2 transitions, h=3 uses last 3 transitions. Lower MAE is better.*\n\n')
            
            # Interpretation
            f.write('## Interpretation\n\n')
            best_metric = max(self.results.items(), 
                            key=lambda x: max(r['accuracy'] for r in x[1]['transition']) - x[1]['static']['accuracy'])
            best_improvement = max(r['accuracy'] for r in best_metric[1]['transition']) - best_metric[1]['static']['accuracy']
            
            if best_improvement > 1:
                f.write('### ✅ Transition-Based Approach WINS!\n\n')
                f.write(f'Adding delta information **improved** localization accuracy by {best_improvement:.2f}%.\n\n')
                f.write('**Why it helps:**\n')
                f.write('- Delta provides geometric movement cues\n')
                f.write('- Helps disambiguate overlapping RSS regions\n')
                f.write('- Variance amplification is compensated by additional information\n')
            elif best_improvement < -1:
                f.write('### ✗ Static Approach Better\n\n')
                f.write(f'Transition approach **decreased** accuracy by {abs(best_improvement):.2f}%.\n\n')
                f.write('**Possible reasons:**\n')
                f.write('- Measurement noise amplification\n')
                f.write('- Grid size may be too large for transition model\n')
                f.write('- Insufficient training data for transition statistics\n')
            else:
                f.write('### ≈ No Clear Winner\n\n')
                f.write('Static and transition approaches perform similarly.\n')
            
            # History length analysis for best metric
            f.write('\n## History Length Analysis')  
            best_acc_metric = max(self.results.items(),
                                key=lambda x: x[1]['static']['accuracy'])
            metric_name = best_acc_metric[0].upper()
            
            f.write(f' ({metric_name})\n\n')
            f.write('Performance as history length increases:\n\n')
            f.write('| History | Accuracy | MAE | Improvement vs Static |\n')
            f.write('|:--------|:---------|:----|:---------------------|\n')
            
            static_acc = best_acc_metric[1]['static']['accuracy']
            static_mae = best_acc_metric[1]['static']['mae']
            
            for h_idx, trans_result in enumerate(best_acc_metric[1]['transition'], 1):
                acc = trans_result['accuracy']
                mae = trans_result['mae']
                improvement = acc - static_acc
                f.write(f'| h={h_idx} | {acc:.2f}% | {mae:.3f} | {improvement:+.2f}% |\n')
            
            # Trend analysis
            accs = [r['accuracy'] for r in best_acc_metric[1]['transition']]
            if len(accs) >= 3:
                if accs[2] > accs[1] > accs[0]:
                    f.write('\n➡️ **INCREASING:** Longer history consistently helps\n')
                elif accs[2] < accs[1] < accs[0]:
                    f.write('\n➡️ **DECREASING:** Overfitting with longer history\n')
                else:
                    f.write('\n➡️ **MIXED:** No clear trend with history length\n')
            
            f.write('\nThe optimal history length may depend on specific conditions.\n')
            
            # Add timing information
            f.write('\n## Performance Metrics\n\n')
            f.write('### Execution Timing\n\n')
            f.write('```\n')
            f.write(f"Data Loading:     {self.timing['data_loading']:8.2f}s\n")
            for metric_name, metric_timing in self.timing['metrics'].items():
                f.write(f"\n{metric_name}:\n")
                f.write(f"  Static Train:   {metric_timing['static_train']:8.2f}s\n")
                f.write(f"  Static Eval:    {metric_timing['static_eval']:8.2f}s\n")
                for i, (t_train, t_eval) in enumerate(zip(metric_timing['transition_train'], metric_timing['transition_eval'])):
                    f.write(f"  Trans(h={i+1}) Train: {t_train:8.2f}s\n")
                    f.write(f"  Trans(h={i+1}) Eval:  {t_eval:8.2f}s\n")
                f.write(f"  Metric Total:   {metric_timing['total']:8.2f}s\n")
            f.write(f"\nSave Results:     {self.timing['save_results']:8.2f}s\n")
            # Note: generate_report timing not available yet (this is called during report generation)
            f.write('```\n')
            
            f.write('\n---\n\n')
            f.write('*Generated by localization_pipeline.py*\n')
        
        print(f"[OK] Report saved to: {report_file}")



def main():
    parser = argparse.ArgumentParser(
        description='Localization Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default Gaussian models on RSS, SINR, CQI separately:
  python localization_pipeline.py --data-dir results/sim_data_xxx
  
  # Run Random Forest on combined RSS+SINR:
  python localization_pipeline.py --data-dir results/sim_data_xxx --model random_forest --metrics "RSS,SINR"
  
  # Test multiple configurations:
  python localization_pipeline.py --data-dir results/sim_data_xxx --model random_forest --metrics RSS SINR "RSS,SINR"
        """
    )
    parser.add_argument('--data-dir', required=True, help='Directory with simulation data')
    parser.add_argument('--output-dir', help='Output directory (auto-generated if not specified)')
    parser.add_argument('--test-ratio', type=float, default=0.2, help='Test set ratio')
    parser.add_argument('--max-history', type=int, default=3, help='Maximum history length')
    parser.add_argument('--split-method', choices=['random', 'temporal'], default='random',
                       help='Train/test split strategy: random (default) or temporal')
    parser.add_argument('--model', choices=['gaussian', 'random_forest'], default='gaussian',
                       help='Model type to use')
    parser.add_argument('--metrics', nargs='+', default=['rss', 'sinr', 'cqi'],
                       help='Metrics to evaluate. Use comma-separated for combinations (e.g., "RSS,SINR")')
    
    args = parser.parse_args()
    
    # Parse metrics - handle comma-separated combinations
    parsed_metrics = []
    for m_spec in args.metrics:
        if ',' in m_spec:
            # Combined metrics like "RSS,SINR"
            parsed_metrics.append([m.strip() for m in m_spec.split(',')])
        else:
            # Single metric
            parsed_metrics.append(m_spec.lower())
    
    # Run pipeline
    pipeline = Pipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        test_ratio=args.test_ratio,
        max_history=args.max_history,
        split_method=args.split_method
    )
    
    pipeline.run(metrics_to_test=parsed_metrics, model_type=args.model)


if __name__ == '__main__':
    main()
