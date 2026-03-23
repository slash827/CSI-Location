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
from pathlib import Path
from scipy.io import loadmat
from scipy.stats import norm
from datetime import datetime
from abc import ABC, abstractmethod
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
import time
from read_jsonc import read_jsonc

# Project root: 4 levels up from src/python/ -> experiments/09_grid_localization/ -> experiments/ -> CSI-Location/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


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

        # Per-interferer RSS fields (rss_ibs_1, rss_ibs_2, ...) for multi-BS experiments
        for field in dir(data['metrics']):
            if field.startswith('rss_ibs_'):
                self.metrics[field] = getattr(data['metrics'], field)

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
        
        # Pre-computed path arrays (built during train)
        self._static_means = None
        self._static_stds = None
        self._paths = None  # List of dicts per history depth
    
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
        
        # Store static params as arrays for vectorized evaluation
        self._static_means = np.array([m['mean'] for m in self.static_models])
        self._static_stds = np.array([m['std'] for m in self.static_models])
        
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
        
        # Pre-enumerate all valid paths for batch evaluation
        self._build_path_arrays(n_points)
    
    def _build_path_arrays(self, n_points):
        """Pre-enumerate all valid neighbor paths and store as numpy arrays.
        
        For h=1: paths are (prev -> curr), one transition each
        For h=2: paths are (prev2 -> prev1 -> curr), two transitions each
        For h=3: paths are (prev3 -> prev2 -> prev1 -> curr), three transitions each
        
        Each path stores: the destination grid point (curr_loc) and the
        mean/std of each transition's delta distribution.
        """
        history_len = self.history_length
        
        # Build h=1 edges: all valid (prev, curr) pairs with trained models
        edges = []  # List of (prev_0idx, curr_0idx, mean_delta, std_delta)
        for key, model in self.transition_models.items():
            parts = key.split('_')
            prev_1idx, curr_1idx = int(parts[0]), int(parts[1])
            edges.append((prev_1idx - 1, curr_1idx - 1, model['mean_delta'], model['std_delta']))
        
        if not edges:
            self._paths = None
            return
        
        edges_arr = np.array(edges)  # shape (n_edges, 4)
        edge_prev = edges_arr[:, 0].astype(int)
        edge_curr = edges_arr[:, 1].astype(int)
        edge_means = edges_arr[:, 2]
        edge_stds = edges_arr[:, 3]
        
        # Build edge lookup: for each destination, which edge indices lead there
        edge_by_dest = {}
        for i, c in enumerate(edge_curr):
            edge_by_dest.setdefault(int(c), []).append(i)
        
        if history_len == 1:
            # Paths = edges themselves
            # delta_index 0 = the single observed delta
            self._paths = {
                'curr_locs': edge_curr,          # shape (P,)
                'means': edge_means[:, None],    # shape (P, 1) - one delta per path
                'stds': edge_stds[:, None],      # shape (P, 1)
            }
        
        elif history_len == 2:
            # Paths: (prev2 -> prev1 -> curr)
            # delta_index 0 = older delta (prev2->prev1), 1 = recent delta (prev1->curr)
            path_curr = []
            path_means = []
            path_stds = []
            
            for e1_idx in range(len(edge_prev)):
                # e1: prev1 -> curr (recent transition, delta index 1)
                prev1 = int(edge_prev[e1_idx])
                curr = int(edge_curr[e1_idx])
                
                # Find edges that lead to prev1 (older transition, delta index 0)
                for e0_idx in edge_by_dest.get(prev1, []):
                    path_curr.append(curr)
                    path_means.append([edge_means[e0_idx], edge_means[e1_idx]])
                    path_stds.append([edge_stds[e0_idx], edge_stds[e1_idx]])
            
            if path_curr:
                self._paths = {
                    'curr_locs': np.array(path_curr, dtype=int),
                    'means': np.array(path_means),  # shape (P, 2)
                    'stds': np.array(path_stds),     # shape (P, 2)
                }
            else:
                self._paths = None
        
        elif history_len >= 3:
            # Paths: (prev3 -> prev2 -> prev1 -> curr)
            # delta_index 0 = oldest, 1 = middle, 2 = most recent
            path_curr = []
            path_means = []
            path_stds = []
            
            for e2_idx in range(len(edge_prev)):
                # e2: prev1 -> curr (most recent, delta index 2)
                prev1 = int(edge_prev[e2_idx])
                curr = int(edge_curr[e2_idx])
                
                for e1_idx in edge_by_dest.get(prev1, []):
                    # e1: prev2 -> prev1 (middle, delta index 1)
                    prev2 = int(edge_prev[e1_idx])
                    
                    for e0_idx in edge_by_dest.get(prev2, []):
                        # e0: prev3 -> prev2 (oldest, delta index 0)
                        path_curr.append(curr)
                        path_means.append([edge_means[e0_idx], edge_means[e1_idx], edge_means[e2_idx]])
                        path_stds.append([edge_stds[e0_idx], edge_stds[e1_idx], edge_stds[e2_idx]])
            
            if path_curr:
                self._paths = {
                    'curr_locs': np.array(path_curr, dtype=int),
                    'means': np.array(path_means),  # shape (P, 3)
                    'stds': np.array(path_stds),     # shape (P, 3)
                }
            else:
                self._paths = None
        
        n_paths = len(self._paths['curr_locs']) if self._paths else 0
        print(f"  [DEBUG] Pre-enumerated {n_paths} valid {history_len}-step paths for batch evaluation")
    
    def predict_batch(self, metric_values, test_indices):
        """Batch-predict all test samples at once using vectorized numpy operations.
        
        This is ~100x faster than calling predict() in a loop because it:
        1. Computes all deltas for all samples at once
        2. Evaluates norm.logpdf for all (samples × paths) in one numpy call
        3. Aggregates path scores per grid point using vectorized operations
        
        Args:
            metric_values: Full metric array (all samples)
            test_indices: Array of test sample indices
            
        Returns:
            predictions: Array of predicted locations (1-indexed)
        """
        n_points = len(self.static_models)
        history_len = self.history_length
        
        # Filter to valid indices (need enough history)
        valid_mask = test_indices >= history_len
        valid_indices = test_indices[valid_mask]
        N = len(valid_indices)
        
        if N == 0:
            return np.array([]), valid_mask
        
        # Current metric values for all test samples: shape (N,)
        current_values = metric_values[valid_indices].astype(float)
        
        # Static log-likelihoods: shape (N, n_points)
        static_logpdfs = norm.logpdf(
            current_values[:, None],
            self._static_means[None, :],
            self._static_stds[None, :]
        )
        
        if self._paths is None:
            # No valid paths — fall back to static only
            predictions = np.argmax(static_logpdfs, axis=1) + 1
            return predictions, valid_mask
        
        # Build delta matrix: shape (N, history_len)
        # deltas[:, 0] = oldest delta, deltas[:, -1] = most recent delta
        deltas = np.zeros((N, history_len))
        for d in range(history_len):
            # d=0: delta between t-h and t-h+1 (oldest)
            # d=history_len-1: delta between t-1 and t (most recent)
            t_from = valid_indices - history_len + d
            t_to = valid_indices - history_len + d + 1
            deltas[:, d] = metric_values[t_to].astype(float) - metric_values[t_from].astype(float)
        
        path_curr = self._paths['curr_locs']  # shape (P,)
        path_means = self._paths['means']      # shape (P, history_len)
        path_stds = self._paths['stds']        # shape (P, history_len)
        P = len(path_curr)

        # Chunk over test samples to bound the dense (chunk, P, H) array to ~256 MB.
        # Without chunking, shape (N, P, H) can reach several GB on larger grids
        # (e.g. 10x10 h=3: 8000 × 35952 × 3 × 8 bytes ≈ 6.4 GB → OOM).
        _MEM_BUDGET = 256 * 1024 * 1024  # 256 MB per chunk
        chunk_size = max(1, int(_MEM_BUDGET / (P * history_len * 8))) if P > 0 else N

        predictions = np.empty(N, dtype=int)

        for start in range(0, N, chunk_size):
            end = min(start + chunk_size, N)
            nc = end - start  # number of samples in this chunk

            # Log-pdf for each (sample, path, delta_step): shape (nc, P, H)
            all_logpdfs = norm.logpdf(
                deltas[start:end, None, :],    # (nc, 1, H)
                path_means[None, :, :],         # (1, P, H)
                path_stds[None, :, :]           # (1, P, H)
            )

            # Sum log-probs across delta steps for each path: shape (nc, P)
            path_scores = all_logpdfs.sum(axis=2)

            # Best path score per grid point: shape (nc, n_points)
            transition_scores = np.full((nc, n_points), -np.inf)
            for loc in range(n_points):
                mask = path_curr == loc
                if mask.any():
                    transition_scores[:, loc] = path_scores[:, mask].max(axis=1)

            # Combine static + transition in log space
            log_posterior = static_logpdfs[start:end] + transition_scores

            # Fall back to static where all transition scores are -inf
            all_inf_mask = np.all(np.isinf(transition_scores), axis=1)
            log_posterior[all_inf_mask] = static_logpdfs[start:end][all_inf_mask]

            predictions[start:end] = np.argmax(log_posterior, axis=1) + 1

        return predictions, valid_mask
    
    def predict(self, metric_value, previous_values=None, previous_location=None):
        """Predict using both current value and transition info (single sample).
        
        NOTE: For batch evaluation, use predict_batch() which is ~100x faster.
        This method is kept for backward compatibility and debugging.
        """
        n_points = len(self.static_models)
        posterior = np.zeros(n_points)
        
        if previous_values is None or len(previous_values) == 0:
            # Fall back to static only
            for i, model in enumerate(self.static_models):
                posterior[i] = norm.pdf(metric_value, model['mean'], model['std'])
        else:
            # Use transition information with log probabilities to avoid underflow
            history_len = min(len(previous_values), self.history_length)
            metric_sequence = [float(v) for v in previous_values[-history_len:]] + [float(metric_value)]
            deltas_observed = np.diff(metric_sequence)
            
            # Compute via batch path if available
            if self._paths is not None:
                path_curr = self._paths['curr_locs']
                path_means = self._paths['means']
                path_stds = self._paths['stds']
                
                # logpdf for each (path, delta): shape (P, H)
                all_logpdfs = norm.logpdf(
                    deltas_observed[None, :],
                    path_means,
                    path_stds
                )
                path_scores = all_logpdfs.sum(axis=1)  # shape (P,)
                
                log_posterior = np.full(n_points, -np.inf)
                for loc in range(n_points):
                    mask = path_curr == loc
                    if mask.any():
                        log_posterior[loc] = path_scores[mask].max()
                
                # Add static
                static_logpdfs = norm.logpdf(
                    float(metric_value),
                    self._static_means,
                    self._static_stds
                )
                
                valid = np.isfinite(log_posterior)
                if valid.any():
                    log_posterior[valid] += static_logpdfs[valid]
                    # Fall back to static for locations with no valid paths
                    log_posterior[~valid] = static_logpdfs[~valid]
                else:
                    log_posterior = static_logpdfs
                
                max_log = np.max(log_posterior[np.isfinite(log_posterior)])
                posterior = np.exp(log_posterior - max_log)
            else:
                # No paths available, static only
                for i, model in enumerate(self.static_models):
                    posterior[i] = norm.pdf(metric_value, model['mean'], model['std'])
        
        # Normalize
        if posterior.sum() > 0:
            posterior = posterior / posterior.sum()
        else:
            posterior = np.ones(n_points) / n_points
        
        return posterior
    
    def get_name(self):
        return self.name


class TransitionFeatureExtractor:
    """Extract engineered transition features from metric history.

    Instead of raw stacking (which scales as O(h * n_metrics) and requires
    enumerating possible paths through grid points), this creates a fixed-size
    feature vector that captures transition dynamics:

    - Current values (absolute position signal)
    - Per-step deltas (movement signal)
    - Cumulative change (total displacement signal)
    - Trend slope (acceleration/direction signal)
    - Variance (stability signal)

    Feature vector size = n_metrics * (h + 4) for history length h.
    This is INDEPENDENT of grid size — the key scalability property.
    """

    @staticmethod
    def extract(current_values, previous_values_list):
        """Extract transition features from a history window.

        Args:
            current_values: Current metric values (scalar or 1D array)
            previous_values_list: List of previous values [t-h, ..., t-2, t-1]
                                 Each element is scalar or 1D array

        Returns:
            1D numpy feature vector
        """
        current = np.atleast_1d(np.asarray(current_values, dtype=float))
        n_metrics = len(current)

        if not previous_values_list or len(previous_values_list) == 0:
            return current

        # Build sequence: [t-h, ..., t-1, t]
        sequence = []
        for pv in previous_values_list:
            sequence.append(np.atleast_1d(np.asarray(pv, dtype=float)))
        sequence.append(current)
        sequence = np.array(sequence)  # shape: (h+1, n_metrics)

        features = []

        # 1. Current absolute values
        features.extend(current)

        # 2. Per-step deltas
        deltas = np.diff(sequence, axis=0)  # shape: (h, n_metrics)
        features.extend(deltas.flatten())

        # 3. Cumulative change (current - oldest)
        features.extend(current - sequence[0])

        # 4. Trend (slope of linear fit per metric)
        h_plus_1 = len(sequence)
        if h_plus_1 >= 2:
            x = np.arange(h_plus_1, dtype=float)
            for m in range(n_metrics):
                slope = np.polyfit(x, sequence[:, m], 1)[0]
                features.append(slope)

        # 5. Variance over window
        features.extend(np.var(sequence, axis=0))

        return np.array(features)

    @staticmethod
    def feature_size(n_metrics, history_length):
        """Calculate feature vector size for given parameters."""
        if history_length == 0:
            return n_metrics
        # current(k) + deltas(h*k) + cumulative(k) + trend(k) + variance(k)
        return n_metrics * (history_length + 4)


def _build_sklearn_features(metric_value, previous_values, history_length, feature_mode):
    """Build feature vector for sklearn-style models.

    Shared helper used by RandomForest, XGBoost, and MLP models.

    Args:
        metric_value: Current observation (scalar or array)
        previous_values: List of previous values [t-h, ..., t-1] or None
        history_length: Number of history steps
        feature_mode: 'raw' for stacking, 'smart' for engineered features

    Returns:
        1D numpy feature vector
    """
    current = np.atleast_1d(np.asarray(metric_value, dtype=float))

    if previous_values is None or len(previous_values) == 0:
        return current

    if feature_mode == 'smart':
        return TransitionFeatureExtractor.extract(current, previous_values)
    else:
        # Raw stacking: [current, t-1, t-2, ..., t-h]
        vec = list(current)
        n_history = min(len(previous_values), history_length)
        history_to_use = previous_values[-n_history:]
        # Reverse to get newest-first: [t-1, t-2, ..., t-h]
        for prev_val in reversed(history_to_use):
            vec.extend(np.atleast_1d(np.asarray(prev_val, dtype=float)))
        return np.array(vec)


class BaseSklearnModel(LocalizationModel):
    """Base class for sklearn-based classifiers with smart feature support.

    Handles common logic for feature building, training, and prediction.
    Subclasses only need to provide the sklearn classifier instance.
    """

    def __init__(self, classifier, model_name, use_transition=False,
                 history_length=1, feature_mode='raw'):
        self.classifier = classifier
        self.use_transition = use_transition
        self.history_length = history_length
        self.feature_mode = feature_mode
        self.name = model_name

    def train(self, metric_values, true_locations, train_indices, n_points):
        """Train the classifier."""
        if metric_values.ndim == 1:
            metric_values = metric_values.reshape(-1, 1)

        min_idx = self.history_length if self.use_transition else 0

        if self.use_transition and self.history_length > 0:
            features_list = []
            labels_list = []
            for idx in train_indices:
                if idx < min_idx:
                    continue
                previous = [metric_values[idx - h] for h in range(self.history_length, 0, -1)]
                feat = _build_sklearn_features(metric_values[idx], previous,
                                               self.history_length, self.feature_mode)
                features_list.append(feat)
                labels_list.append(true_locations[idx])
            X_train = np.array(features_list)
            y_train = np.array(labels_list)
        else:
            X_train = metric_values[train_indices]
            y_train = true_locations[train_indices]

        self.classifier.fit(X_train, y_train)

    def predict(self, metric_value, previous_values=None):
        """Predict location probabilities."""
        if np.isscalar(metric_value):
            metric_value = np.array([metric_value])
        elif hasattr(metric_value, 'ndim') and metric_value.ndim == 0:
            metric_value = metric_value.reshape(1)

        if self.use_transition and previous_values is not None:
            feat = _build_sklearn_features(metric_value, previous_values,
                                           self.history_length, self.feature_mode)
            X = feat.reshape(1, -1)
        else:
            X = np.atleast_1d(metric_value).reshape(1, -1)

        proba = self.classifier.predict_proba(X)[0]

        # Map sklearn class probabilities back to grid point indices (1-indexed)
        max_class = int(max(self.classifier.classes_))
        posterior = np.zeros(max_class)
        for i, class_label in enumerate(self.classifier.classes_):
            posterior[int(class_label) - 1] = proba[i]

        return posterior

    def predict_batch(self, metric_values, test_indices):
        """Batch-predict all test samples at once.
        
        Builds all feature vectors first, then calls predict_proba() once.
        This is ~50-100x faster than per-sample prediction.
        
        Returns:
            predictions: Array of predicted locations (1-indexed)
            valid_mask: Boolean mask of which test_indices were valid
        """
        if metric_values.ndim == 1:
            metric_values = metric_values.reshape(-1, 1)
        
        history_length = self.history_length if self.use_transition else 0
        min_idx = history_length
        
        # Filter valid indices
        valid_mask = test_indices >= min_idx
        valid_indices = test_indices[valid_mask]
        
        if len(valid_indices) == 0:
            return np.array([]), valid_mask
        
        # Build all feature vectors
        if self.use_transition and history_length > 0:
            features_list = []
            for idx in valid_indices:
                previous = [metric_values[idx - h] for h in range(history_length, 0, -1)]
                feat = _build_sklearn_features(metric_values[idx], previous,
                                               history_length, self.feature_mode)
                features_list.append(feat)
            X = np.array(features_list)
        else:
            X = metric_values[valid_indices]
        
        # Single batch predict call
        predictions = self.classifier.predict(X)
        
        return predictions.astype(int), valid_mask

    def get_name(self):
        return self.name


class RandomForestModel(BaseSklearnModel):
    """Random Forest classifier for localization."""

    def __init__(self, use_transition=False, history_length=1, n_estimators=100,
                 max_depth=30, n_jobs=4, feature_mode='raw'):
        clf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=n_jobs
        )
        mode = "Transition" if use_transition else "Static"
        fm = f", {feature_mode}" if use_transition else ""
        name = f"RandomForest ({mode}, h={history_length}{fm})"
        super().__init__(clf, name, use_transition, history_length, feature_mode)


class XGBoostModel(BaseSklearnModel):
    """XGBoost classifier for localization."""

    def __init__(self, use_transition=False, history_length=1, n_estimators=100,
                 max_depth=6, learning_rate=0.1, feature_mode='raw', n_jobs=4):
        if not HAS_XGBOOST:
            raise ImportError("xgboost is not installed. Install with: pip install xgboost")
        clf = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
            n_jobs=n_jobs,
            verbosity=0,
            use_label_encoder=False,
            eval_metric='mlogloss'
        )
        mode = "Transition" if use_transition else "Static"
        fm = f", {feature_mode}" if use_transition else ""
        name = f"XGBoost ({mode}, h={history_length}{fm})"
        super().__init__(clf, name, use_transition, history_length, feature_mode)

    def train(self, metric_values, true_locations, train_indices, n_points):
        """Train XGBoost - needs 0-indexed labels."""
        if metric_values.ndim == 1:
            metric_values = metric_values.reshape(-1, 1)

        min_idx = self.history_length if self.use_transition else 0

        if self.use_transition and self.history_length > 0:
            features_list = []
            labels_list = []
            for idx in train_indices:
                if idx < min_idx:
                    continue
                previous = [metric_values[idx - h] for h in range(self.history_length, 0, -1)]
                feat = _build_sklearn_features(metric_values[idx], previous,
                                               self.history_length, self.feature_mode)
                features_list.append(feat)
                labels_list.append(true_locations[idx])
            X_train = np.array(features_list)
            y_train = np.array(labels_list)
        else:
            X_train = metric_values[train_indices]
            y_train = true_locations[train_indices]

        # XGBoost needs 0-indexed labels for multi-class
        self._label_offset = int(y_train.min())
        y_train_0idx = y_train - self._label_offset
        self.classifier.fit(X_train, y_train_0idx)

    def predict(self, metric_value, previous_values=None):
        """Predict with XGBoost - handle 0-indexed labels."""
        if np.isscalar(metric_value):
            metric_value = np.array([metric_value])
        elif hasattr(metric_value, 'ndim') and metric_value.ndim == 0:
            metric_value = metric_value.reshape(1)

        if self.use_transition and previous_values is not None:
            feat = _build_sklearn_features(metric_value, previous_values,
                                           self.history_length, self.feature_mode)
            X = feat.reshape(1, -1)
        else:
            X = np.atleast_1d(metric_value).reshape(1, -1)

        proba = self.classifier.predict_proba(X)[0]

        # Map back to 1-indexed grid points
        max_class = int(max(self.classifier.classes_)) + self._label_offset
        posterior = np.zeros(max_class)
        for i, class_label in enumerate(self.classifier.classes_):
            posterior[int(class_label) + self._label_offset - 1] = proba[i]

        return posterior

    def predict_batch(self, metric_values, test_indices):
        """Batch-predict with XGBoost - handle 0-indexed labels."""
        if metric_values.ndim == 1:
            metric_values = metric_values.reshape(-1, 1)
        
        history_length = self.history_length if self.use_transition else 0
        min_idx = history_length
        
        valid_mask = test_indices >= min_idx
        valid_indices = test_indices[valid_mask]
        
        if len(valid_indices) == 0:
            return np.array([]), valid_mask
        
        if self.use_transition and history_length > 0:
            features_list = []
            for idx in valid_indices:
                previous = [metric_values[idx - h] for h in range(history_length, 0, -1)]
                feat = _build_sklearn_features(metric_values[idx], previous,
                                               history_length, self.feature_mode)
                features_list.append(feat)
            X = np.array(features_list)
        else:
            X = metric_values[valid_indices]
        
        # XGBoost predict returns 0-indexed labels, add offset back
        preds_0idx = self.classifier.predict(X)
        predictions = preds_0idx.astype(int) + self._label_offset
        
        return predictions, valid_mask


class MLPModel(BaseSklearnModel):
    """Multi-Layer Perceptron classifier for localization.

    Uses StandardScaler internally since MLPs are sensitive to feature scales.
    """

    def __init__(self, use_transition=False, history_length=1,
                 hidden_layers=(256, 128, 64), max_iter=500, feature_mode='raw'):
        clf = make_pipeline(
            StandardScaler(),
            MLPClassifier(
                hidden_layer_sizes=hidden_layers,
                activation='relu',
                solver='adam',
                max_iter=max_iter,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1
            )
        )
        mode = "Transition" if use_transition else "Static"
        fm = f", {feature_mode}" if use_transition else ""
        name = f"MLP ({mode}, h={history_length}{fm})"
        super().__init__(clf, name, use_transition, history_length, feature_mode)


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
        # Use batch prediction when available (much faster for sklearn models)
        if hasattr(model, 'predict_batch'):
            predictions, valid_mask = model.predict_batch(metric_values, test_indices)
            test_indices_used = test_indices[valid_mask]
        else:
            predictions = []
            test_indices_used = test_indices
            
            for idx in test_indices:
                posterior = model.predict(metric_values[idx])
                pred_location = np.argmax(posterior) + 1  # Convert to 1-indexed
                predictions.append(pred_location)
        
        # Compute metrics
        predictions = np.array(predictions)
        true_labels = np.array([true_locations[idx] for idx in test_indices_used])
        
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
        # Get history length from model
        history_length = getattr(model, 'history_length', 1)
        
        # Use batch prediction when available (~100x faster)
        if hasattr(model, 'predict_batch'):
            predictions, valid_mask = model.predict_batch(metric_values, test_indices)
            valid_test_indices = test_indices[valid_mask]
        else:
            # Per-sample prediction fallback
            predictions = []
            valid_test_indices = []
            
            is_gaussian = isinstance(model, GaussianTransitionModel)
            
            for idx in test_indices:
                if idx >= history_length:
                    if is_gaussian:
                        previous_values = [metric_values[idx - h] for h in range(history_length, 0, -1)]
                        posterior = model.predict(metric_values[idx], 
                                                previous_values=previous_values,
                                                previous_location=None)
                    else:
                        previous_values = [metric_values[idx - h] for h in range(history_length, 0, -1)]
                        posterior = model.predict(metric_values[idx], previous_values=previous_values)
                    
                    pred_location = np.argmax(posterior) + 1
                    predictions.append(pred_location)
                    valid_test_indices.append(idx)
            
            predictions = np.array(predictions)
            valid_test_indices = np.array(valid_test_indices)
        
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
    
    def __init__(self, data_dir, output_dir=None, test_ratio=0.2, max_history=3,
                 split_method='random', feature_mode='raw'):
        t_start = time.time()
        self.data = SimulationData(data_dir)
        t_load = time.time() - t_start

        self.output_dir = Path(output_dir) if output_dir else self._create_output_dir()
        self.splitter = DataSplitter(test_ratio=test_ratio, split_method=split_method)
        self.max_history = max_history
        self.feature_mode = feature_mode
        self.results = {}
        self.timing = {'data_loading': t_load}
    
    def _create_output_dir(self):
        """Create timestamped output directory"""
        scenario = self.data.config['channel']['scenario']
        los_nlos = 'LOS' if 'LOS' in scenario and 'NLOS' not in scenario else 'NLOS'
        grid_size = self.data.config['grid']['size']
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = PROJECT_ROOT / f"results/grid_localization/grid_{grid_size}x{grid_size}/exp13e_{los_nlos}_{timestamp}"
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
    
    def _create_model(self, model_type, is_transition, history_length,
                      n_estimators=100, n_jobs=4, max_depth=30):
        """Factory method to create the appropriate model."""
        if model_type == 'gaussian':
            if is_transition:
                return GaussianTransitionModel(self.data.neighbors, history_length=history_length)
            else:
                return GaussianStaticModel()
        elif model_type == 'random_forest':
            return RandomForestModel(
                use_transition=is_transition, history_length=history_length,
                n_estimators=n_estimators, max_depth=max_depth, n_jobs=n_jobs,
                feature_mode=self.feature_mode
            )
        elif model_type == 'xgboost':
            return XGBoostModel(
                use_transition=is_transition, history_length=history_length,
                n_estimators=n_estimators, max_depth=min(max_depth, 10) if max_depth else 6,
                n_jobs=n_jobs, feature_mode=self.feature_mode
            )
        elif model_type == 'mlp':
            return MLPModel(
                use_transition=is_transition, history_length=history_length,
                feature_mode=self.feature_mode
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def run(self, metrics_to_test=['rss', 'sinr', 'cqi'], model_type='gaussian',
             n_estimators=100, n_jobs=4, max_depth=30, max_train_samples=None):
        """Run complete pipeline

        Args:
            metrics_to_test: List of metric specifications. Each can be:
                           - String: 'rss', 'sinr', 'cqi'
                           - List: ['RSS', 'SINR'] for combined metrics
            model_type: 'gaussian', 'random_forest', 'xgboost', or 'mlp'
            n_estimators: Number of estimators (trees for RF/XGBoost)
            n_jobs: Number of parallel jobs
            max_depth: Maximum tree depth
            max_train_samples: Subsample training data to this many samples
        """
        t_pipeline_start = time.time()

        print(f"\n{'='*70}")
        print(f"LOCALIZATION PIPELINE")
        print(f"{'='*70}")
        print(f"Output directory: {self.output_dir}")
        print(f"Model type: {model_type}")
        if model_type != 'gaussian':
            print(f"Feature mode: {self.feature_mode}")
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

            # Gaussian models only work with 1D features (single metric)
            if model_type == 'gaussian' and metric_values.ndim > 1:
                print(f"\n  WARNING: Gaussian models only support single metrics.")
                print(f"           Skipping {metric_name}. Use --model random_forest instead.")
                continue

            metric_timing = {}

            # --- Static model ---
            print(f"\nTraining {model_type} (static)...")
            t_train = time.time()
            static_model = self._create_model(model_type, False, 0,
                                              n_estimators, n_jobs, max_depth)
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

            # --- Transition models with different history lengths ---
            transition_results = []
            metric_timing['transition_train'] = []
            metric_timing['transition_eval'] = []

            for h in range(1, self.max_history + 1):
                print(f"\nTraining {model_type} (transition, h={h})...")
                t_train = time.time()
                trans_model = self._create_model(model_type, True, h,
                                                 n_estimators, n_jobs, max_depth)
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
    parser.add_argument('--model', choices=['gaussian', 'random_forest', 'xgboost', 'mlp'],
                       default='gaussian', help='Model type to use')
    parser.add_argument('--feature-mode', choices=['raw', 'smart'], default='raw',
                       help='Feature mode: raw (stack history) or smart (engineered transition features)')
    parser.add_argument('--metrics', nargs='+', default=['rss', 'sinr', 'cqi'],
                       help='Metrics to evaluate. Use comma-separated for combinations (e.g., "RSS,SINR")')
    parser.add_argument('--n-estimators', type=int, default=100, help='Number of trees for Random Forest')
    parser.add_argument('--n-jobs', type=int, default=4, help='Parallel jobs for Random Forest')
    parser.add_argument('--max-depth', type=int, default=30, help='Max tree depth for Random Forest')
    parser.add_argument('--max-train-samples', type=int, default=None,
                        help='Subsample training data to this many samples (for memory constraints)')
    
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
        split_method=args.split_method,
        feature_mode=args.feature_mode
    )
    
    pipeline.run(metrics_to_test=parsed_metrics, model_type=args.model,
                 n_estimators=args.n_estimators, n_jobs=args.n_jobs,
                 max_depth=args.max_depth, max_train_samples=args.max_train_samples)


if __name__ == '__main__':
    main()
