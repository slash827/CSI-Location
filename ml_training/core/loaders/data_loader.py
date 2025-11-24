"""
Data loader for CSI datasets from QuaDRiGa simulations.

Loads .mat files and prepares data for ML training.
"""

import numpy as np
from scipy.io import loadmat
from pathlib import Path
from typing import Tuple, Dict, Optional
import warnings

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False
    warnings.warn("h5py not installed. MATLAB v7.3 files will not be readable. "
                 "Install with: pip install h5py")

from config import DEFAULT_DATASET_PATH, FEATURE_GROUPS, TARGETS, METADATA_FIELDS


class CSIDataLoader:
    """
    Load and prepare CSI data from MATLAB .mat files.
    
    Expected data structure (from exp09):
        train_data.mat / val_data.mat:
            - positions_x: [N,] array
            - positions_y: [N,] array
            - distances: [N,] array
            - RSS_wb: [N,] array
            - SINR_wb: [N,] array
            - CQI_wb: [N,] array
            - RSS_per_sc: [N, 256] array
            - SINR_per_sc: [N, 256] array
            - H_mag_per_sc: [N, 256] array
            - trajectory_id: [N,] array
            - snapshot_id: [N,] array
    """
    
    def __init__(self, dataset_path: Optional[Path] = None):
        """
        Initialize data loader.
        
        Args:
            dataset_path: Path to dataset folder containing train_data.mat and val_data.mat
                         If None, uses DEFAULT_DATASET_PATH from config
        """
        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
        
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset path not found: {self.dataset_path}")
        
        self.train_file = self.dataset_path / "train_data.mat"
        self.val_file = self.dataset_path / "val_data.mat"
        self.metadata_file = self.dataset_path / "metadata.mat"
        self.nlos_metadata_file = self.dataset_path / "nlos_metadata.mat"
        
        # Check if files exist
        if not self.train_file.exists():
            raise FileNotFoundError(f"Training data not found: {self.train_file}")
        if not self.val_file.exists():
            warnings.warn(f"Validation data not found: {self.val_file}")
        
        self.train_data = None
        self.val_data = None
        self.metadata = None
        self.nlos_metadata = None
    
    def load_mat_file(self, file_path: Path) -> Dict:
        """
        Load a .mat file and return as dictionary.
        Supports both older MATLAB formats and v7.3 (HDF5) format.
        
        Args:
            file_path: Path to .mat file
            
        Returns:
            Dictionary with data
        """
        try:
            # Try loading with scipy (older MATLAB formats)
            data = loadmat(file_path, squeeze_me=True, struct_as_record=False)
            # Remove MATLAB metadata fields
            data = {k: v for k, v in data.items() if not k.startswith('__')}
            return data
        
        except NotImplementedError:
            # File is MATLAB v7.3 (HDF5 format), use h5py
            if not HAS_H5PY:
                raise ImportError(
                    "MATLAB v7.3 files require h5py. Install with: pip install h5py"
                )
            
            print(f"  - Loading MATLAB v7.3 file with h5py...")
            data = {}
            
            with h5py.File(file_path, 'r') as f:
                # Extract all datasets from the HDF5 file
                for key in f.keys():
                    if key.startswith('#'):  # Skip HDF5 internal references
                        continue
                    
                    try:
                        dataset = f[key]
                        
                        if isinstance(dataset, h5py.Dataset):
                            # Load the dataset
                            arr = dataset[()]
                            
                            # Handle MATLAB's column-major to Python's row-major
                            if arr.ndim == 2 and arr.shape[0] > 1 and arr.shape[1] > 1:
                                arr = arr.T
                            
                            # Convert byte strings to regular strings if needed
                            if arr.dtype.kind == 'S' or arr.dtype.kind == 'U':
                                arr = arr.astype(str)
                            
                            data[key] = np.squeeze(arr) if arr.size == 1 else arr
                        
                        elif isinstance(dataset, h5py.Group):
                            # It's a struct/group, recursively load it
                            data[key] = self._load_h5py_group(dataset)
                    
                    except Exception as e:
                        warnings.warn(f"Could not load '{key}': {e}")
                        continue
            
            return data
    
    def _load_h5py_group(self, group: 'h5py.Group') -> Dict:
        """
        Recursively load an HDF5 group (MATLAB struct).
        
        Args:
            group: h5py Group object
            
        Returns:
            Dictionary with group contents
        """
        result = {}
        for key in group.keys():
            if key.startswith('#'):
                continue
            
            item = group[key]
            if isinstance(item, h5py.Dataset):
                arr = item[()]
                # Handle transpose for 2D arrays
                if arr.ndim == 2 and arr.shape[0] > 1 and arr.shape[1] > 1:
                    arr = arr.T
                result[key] = np.squeeze(arr) if arr.size == 1 else arr
            elif isinstance(item, h5py.Group):
                result[key] = self._load_h5py_group(item)
        
        return result
    
    def load_train_data(self) -> Dict:
        """Load training data."""
        if self.train_data is None:
            print(f"Loading training data from: {self.train_file}")
            self.train_data = self.load_mat_file(self.train_file)
            print(f"  - Loaded {len(self._get_field(self.train_data, 'positions_x'))} samples")
        return self.train_data
    
    def load_val_data(self) -> Optional[Dict]:
        """Load validation data."""
        if self.val_data is None and self.val_file.exists():
            print(f"Loading validation data from: {self.val_file}")
            self.val_data = self.load_mat_file(self.val_file)
            print(f"  - Loaded {len(self._get_field(self.val_data, 'positions_x'))} samples")
        return self.val_data
    
    def load_metadata(self) -> Optional[Dict]:
        """Load metadata if available."""
        if self.metadata is None and self.metadata_file.exists():
            print(f"Loading metadata from: {self.metadata_file}")
            self.metadata = self.load_mat_file(self.metadata_file)
        return self.metadata
    
    def load_nlos_metadata(self) -> Optional[Dict]:
        """
        Load NLOS metadata if available (from exp11).
        
        Returns:
            Dictionary with NLOS metadata:
                - train_conditions: [N_train,] array with NLOS type codes
                  (1=pure_los, 2=light_nlos, 3=moderate_nlos, 4=heavy_nlos)
                - val_conditions: [N_val,] array with NLOS type codes
                - train_scenarios: list of scenario names for training samples
                - val_scenarios: list of scenario names for validation samples
        """
        if self.nlos_metadata is None and self.nlos_metadata_file.exists():
            print(f"Loading NLOS metadata from: {self.nlos_metadata_file}")
            self.nlos_metadata = self.load_mat_file(self.nlos_metadata_file)
            
            # Display NLOS distribution
            if 'train_conditions' in self.nlos_metadata:
                train_cond = self.nlos_metadata['train_conditions']
                print(f"  - Training NLOS distribution:")
                nlos_labels = ['Pure LOS', 'Light NLOS', 'Moderate NLOS', 'Heavy NLOS']
                for i in range(1, 5):
                    count = np.sum(train_cond == i)
                    pct = 100 * count / len(train_cond)
                    print(f"    {nlos_labels[i-1]}: {count} samples ({pct:.1f}%)")
            
            if 'val_conditions' in self.nlos_metadata:
                val_cond = self.nlos_metadata['val_conditions']
                print(f"  - Validation NLOS distribution:")
                for i in range(1, 5):
                    count = np.sum(val_cond == i)
                    pct = 100 * count / len(val_cond)
                    print(f"    {nlos_labels[i-1]}: {count} samples ({pct:.1f}%)")
        
        elif self.nlos_metadata is None:
            print("  - No NLOS metadata found (dataset is LOS-only or pre-exp11)")
        
        return self.nlos_metadata
    
    def _get_field(self, data: Dict, field_name: str) -> np.ndarray:
        """
        Get a field from data dictionary, handling MATLAB struct format.
        
        Args:
            data: Data dictionary
            field_name: Field name
            
        Returns:
            Numpy array
        """
        # Handle both direct dict access and MATLAB struct format
        value = None
        
        # Try direct access first
        if field_name in data:
            value = data[field_name]
        
        # Try nested struct access (for MATLAB v7.3)
        elif 'train_data' in data:
            if isinstance(data['train_data'], dict) and field_name in data['train_data']:
                value = data['train_data'][field_name]
            elif hasattr(data['train_data'], field_name):
                value = getattr(data['train_data'], field_name)
        
        elif 'val_data' in data:
            if isinstance(data['val_data'], dict) and field_name in data['val_data']:
                value = data['val_data'][field_name]
            elif hasattr(data['val_data'], field_name):
                value = getattr(data['val_data'], field_name)
        
        if value is None:
            raise KeyError(f"Field '{field_name}' not found in data. Available keys: {list(data.keys())}")
        
        # Ensure it's a numpy array
        if not isinstance(value, np.ndarray):
            value = np.array(value)
        
        # Handle MATLAB's column-major vs Python's row-major
        # For 2D arrays where first dimension is smaller, transpose
        if value.ndim == 2:
            if value.shape[0] < value.shape[1] and value.shape[0] in [1, 2, 3, 256]:
                # Likely needs transpose (e.g., [1, 640] → [640,] or [256, 640] → [640, 256])
                value = value.T
            
            # Handle 1D arrays stored as [1, N] or [N, 1]
            if value.shape[0] == 1:
                value = value.ravel()
            elif value.shape[1] == 1:
                value = value.ravel()
        
        return value
    
    def extract_features(self, data: Dict, feature_groups: list = None) -> np.ndarray:
        """
        Extract features from data dictionary.
        
        Args:
            data: Data dictionary
            feature_groups: List of feature group names to extract.
                          Options: 'wideband', 'rss_per_sc', 'sinr_per_sc', 'h_mag_per_sc'
                          If None, extracts all features (771 total)
        
        Returns:
            Feature matrix [N, D] where D is number of features
        """
        if feature_groups is None:
            # Use all feature groups
            feature_groups = list(FEATURE_GROUPS.keys())
        
        features_list = []
        feature_names = []
        
        for group in feature_groups:
            if group == 'wideband':
                # Extract wideband features (3)
                for feat in FEATURE_GROUPS['wideband']:
                    feat_data = self._get_field(data, feat)
                    if feat_data.ndim == 1:
                        feat_data = feat_data[:, np.newaxis]
                    features_list.append(feat_data)
                    feature_names.append(feat)
            
            elif group in ['rss_per_sc', 'sinr_per_sc', 'h_mag_per_sc']:
                # Extract per-subcarrier features (256 or 1024 each)
                feat_name = FEATURE_GROUPS[group]
                feat_data = self._get_field(data, feat_name)
                
                # Handle shape: MATLAB saves as [features, samples] but we need [samples, features]
                if feat_data.ndim == 1:
                    feat_data = feat_data[:, np.newaxis]
                elif feat_data.shape[0] < feat_data.shape[1]:
                    # If first dimension is smaller, it's likely [features, samples] - transpose it
                    feat_data = feat_data.T
                
                features_list.append(feat_data)
                feature_names.extend([f"{feat_name}_{i}" for i in range(feat_data.shape[1])])
        
        # Concatenate all features
        X = np.concatenate(features_list, axis=1)
        
        print(f"  - Extracted {X.shape[1]} features: {', '.join(feature_groups)}")
        
        return X
    
    def extract_targets(self, data: Dict) -> np.ndarray:
        """
        Extract target labels (x, y positions).
        
        Args:
            data: Data dictionary
            
        Returns:
            Target matrix [N, 2] with (x, y) positions
        """
        positions_x = self._get_field(data, 'positions_x')
        positions_y = self._get_field(data, 'positions_y')
        
        y = np.column_stack([positions_x, positions_y])
        
        return y
    
    def load_all(self, feature_groups: list = None) -> Tuple[np.ndarray, np.ndarray, 
                                                               Optional[np.ndarray], 
                                                               Optional[np.ndarray]]:
        """
        Load all data (train and validation).
        
        Args:
            feature_groups: List of feature groups to extract (default: all)
        
        Returns:
            X_train, y_train, X_val, y_val
        """
        # Load train data
        train_data = self.load_train_data()
        X_train = self.extract_features(train_data, feature_groups)
        y_train = self.extract_targets(train_data)
        
        # Load validation data
        X_val, y_val = None, None
        val_data = self.load_val_data()
        if val_data is not None:
            X_val = self.extract_features(val_data, feature_groups)
            y_val = self.extract_targets(val_data)
        
        return X_train, y_train, X_val, y_val
    
    def get_metadata_info(self, data: Dict) -> Dict:
        """
        Extract metadata information.
        
        Args:
            data: Data dictionary
            
        Returns:
            Dictionary with metadata
        """
        metadata = {}
        
        for field in METADATA_FIELDS:
            try:
                metadata[field] = self._get_field(data, field)
            except KeyError:
                warnings.warn(f"Metadata field '{field}' not found")
        
        return metadata
    
    def inspect_dataset(self):
        """Print dataset information."""
        print("\n" + "=" * 70)
        print("DATASET INSPECTION")
        print("=" * 70)
        print(f"\nDataset path: {self.dataset_path}")
        
        # Load data
        train_data = self.load_train_data()
        val_data = self.load_val_data()
        
        # Load NLOS metadata if available
        nlos_meta = self.load_nlos_metadata()
        
        # Extract features and targets
        X_train = self.extract_features(train_data)
        y_train = self.extract_targets(train_data)
        
        print(f"\n--- Training Set ---")
        print(f"Samples: {X_train.shape[0]}")
        print(f"Features: {X_train.shape[1]}")
        print(f"Targets: {y_train.shape[1]} (x, y positions)")
        
        if val_data is not None:
            X_val = self.extract_features(val_data)
            y_val = self.extract_targets(val_data)
            print(f"\n--- Validation Set ---")
            print(f"Samples: {X_val.shape[0]}")
            print(f"Features: {X_val.shape[1]}")
        
        # Position statistics
        print(f"\n--- Position Statistics (Training) ---")
        print(f"X range: [{y_train[:, 0].min():.2f}, {y_train[:, 0].max():.2f}] m")
        print(f"Y range: [{y_train[:, 1].min():.2f}, {y_train[:, 1].max():.2f}] m")
        print(f"X mean: {y_train[:, 0].mean():.2f} ± {y_train[:, 0].std():.2f} m")
        print(f"Y mean: {y_train[:, 1].mean():.2f} ± {y_train[:, 1].std():.2f} m")
        
        # Feature statistics (wideband only)
        print(f"\n--- Wideband Feature Statistics (Training) ---")
        for i, feat_name in enumerate(FEATURE_GROUPS['wideband']):
            feat_data = self._get_field(train_data, feat_name)
            print(f"{feat_name:10s}: mean={feat_data.mean():8.2f}, std={feat_data.std():7.2f}, "
                  f"range=[{feat_data.min():8.2f}, {feat_data.max():8.2f}]")
        
        # NLOS statistics (if available)
        if nlos_meta and 'train_conditions' in nlos_meta:
            print(f"\n--- NLOS Condition Statistics ---")
            train_cond = np.array(nlos_meta['train_conditions']).ravel()  # Ensure 1D
            nlos_labels = ['Pure LOS', 'Light NLOS', 'Moderate NLOS', 'Heavy NLOS']
            
            print("Training set:")
            for i in range(1, 5):
                mask = train_cond == i
                if np.any(mask):
                    # Get RSRP stats for this condition
                    rsrp = self._get_field(train_data, 'RSRP').ravel()  # Ensure 1D
                    rsrp_cond = rsrp[mask]
                    print(f"  {nlos_labels[i-1]:15s}: {np.sum(mask):5d} samples, "
                          f"RSRP: {rsrp_cond.mean():6.2f} ± {rsrp_cond.std():5.2f} dBm")
            
            if 'val_conditions' in nlos_meta and val_data is not None:
                val_cond = np.array(nlos_meta['val_conditions']).ravel()  # Ensure 1D
                print("\nValidation set:")
                for i in range(1, 5):
                    mask = val_cond == i
                    if np.any(mask):
                        rsrp = self._get_field(val_data, 'RSRP').ravel()  # Ensure 1D
                        rsrp_cond = rsrp[mask]
                        print(f"  {nlos_labels[i-1]:15s}: {np.sum(mask):5d} samples, "
                              f"RSRP: {rsrp_cond.mean():6.2f} ± {rsrp_cond.std():5.2f} dBm")
        
        # Metadata
        metadata = self.get_metadata_info(train_data)
        if metadata:
            print(f"\n--- Metadata ---")
            if 'trajectory_id' in metadata:
                n_traj = len(np.unique(metadata['trajectory_id']))
                print(f"Trajectories: {n_traj}")
            if 'distances' in metadata:
                print(f"Distance range: [{metadata['distances'].min():.2f}, "
                      f"{metadata['distances'].max():.2f}] m")
        
        print("=" * 70 + "\n")


def main():
    """Example usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load and inspect CSI dataset')
    parser.add_argument('--dataset_path', type=str, default=None,
                       help='Path to dataset folder (default: from config)')
    parser.add_argument('--inspect', action='store_true',
                       help='Print dataset inspection report')
    parser.add_argument('--feature_groups', nargs='+', 
                       choices=['wideband', 'rss_per_sc', 'sinr_per_sc', 'h_mag_per_sc'],
                       help='Feature groups to load (default: all)')
    
    args = parser.parse_args()
    
    # Create loader
    loader = CSIDataLoader(args.dataset_path)
    
    if args.inspect:
        # Inspect dataset
        loader.inspect_dataset()
    else:
        # Load data
        X_train, y_train, X_val, y_val = loader.load_all(args.feature_groups)
        
        print(f"\nData loaded successfully!")
        print(f"Training: X={X_train.shape}, y={y_train.shape}")
        if X_val is not None:
            print(f"Validation: X={X_val.shape}, y={y_val.shape}")


if __name__ == "__main__":
    main()
