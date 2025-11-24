"""
Data preprocessing for CSI localization.

Handles normalization, feature scaling, outlier detection, etc.
"""

import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import mutual_info_regression, f_regression
import pickle
from pathlib import Path
from typing import Tuple, Optional, Dict

from data_loader import CSIDataLoader
from config import (NORMALIZATION, FEATURE_SELECTION, PCA_CONFIG, 
                   OUTLIER_DETECTION, RANDOM_SEED, OUTPUT_DIR)


class CSIPreprocessor:
    """Preprocessing pipeline for CSI data."""
    
    def __init__(self):
        """Initialize preprocessor."""
        self.scaler = None
        self.pca = None
        self.feature_selector = None
        self.selected_features = None
        self.is_fitted = False
        
    def fit(self, X_train: np.ndarray, y_train: np.ndarray) -> 'CSIPreprocessor':
        """
        Fit preprocessing transformations on training data.
        
        Args:
            X_train: Training features [N, D]
            y_train: Training targets [N, 2]
        
        Returns:
            self
        """
        print("\nFitting preprocessing pipeline...")
        
        # 1. Feature normalization
        if NORMALIZATION:
            print(f"  - Normalization: {NORMALIZATION}")
            if NORMALIZATION == 'standard':
                self.scaler = StandardScaler()
            elif NORMALIZATION == 'minmax':
                self.scaler = MinMaxScaler()
            elif NORMALIZATION == 'robust':
                self.scaler = RobustScaler()
            else:
                raise ValueError(f"Unknown normalization: {NORMALIZATION}")
            
            X_scaled = self.scaler.fit_transform(X_train)
        else:
            X_scaled = X_train.copy()
            print("  - Normalization: None")
        
        # 2. Feature selection
        if FEATURE_SELECTION['enabled']:
            print(f"  - Feature selection: {FEATURE_SELECTION['method']}, "
                  f"n_features={FEATURE_SELECTION['n_features']}")
            
            # Compute feature importance for both x and y targets
            method = FEATURE_SELECTION['method']
            n_features = FEATURE_SELECTION['n_features']
            
            if method == 'mutual_info':
                # Average mutual info for x and y
                mi_x = mutual_info_regression(X_scaled, y_train[:, 0], random_state=RANDOM_SEED)
                mi_y = mutual_info_regression(X_scaled, y_train[:, 1], random_state=RANDOM_SEED)
                importance = (mi_x + mi_y) / 2
            
            elif method == 'f_test':
                # Average F-statistic for x and y
                f_x, _ = f_regression(X_scaled, y_train[:, 0])
                f_y, _ = f_regression(X_scaled, y_train[:, 1])
                importance = (f_x + f_y) / 2
            
            else:
                raise ValueError(f"Unknown feature selection method: {method}")
            
            # Select top-k features
            self.selected_features = np.argsort(importance)[-n_features:]
            X_scaled = X_scaled[:, self.selected_features]
            
            print(f"    Selected {len(self.selected_features)} features")
        
        # 3. PCA (optional)
        if PCA_CONFIG['enabled']:
            print(f"  - PCA: n_components={PCA_CONFIG['n_components']}")
            self.pca = PCA(n_components=PCA_CONFIG['n_components'], random_state=RANDOM_SEED)
            self.pca.fit(X_scaled)
            print(f"    Explained variance: {self.pca.explained_variance_ratio_.sum():.3f}")
        
        self.is_fitted = True
        print("  ✓ Preprocessing pipeline fitted successfully!")
        
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Apply preprocessing transformations.
        
        Args:
            X: Features [N, D]
        
        Returns:
            Transformed features
        """
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fitted before transform")
        
        # Don't copy - sklearn transforms return new arrays anyway
        X_transformed = X
        
        # Apply transformations in order
        if self.scaler is not None:
            X_transformed = self.scaler.transform(X_transformed)
        
        if self.selected_features is not None:
            X_transformed = X_transformed[:, self.selected_features]
        
        if self.pca is not None:
            X_transformed = self.pca.transform(X_transformed)
        
        return X_transformed
    
    def fit_transform(self, X_train: np.ndarray, y_train: np.ndarray) -> np.ndarray:
        """Fit and transform training data."""
        self.fit(X_train, y_train)
        return self.transform(X_train)
    
    def detect_outliers(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Detect outliers in data.
        
        Args:
            X: Features [N, D]
            y: Targets [N, 2]
        
        Returns:
            Boolean mask where True = outlier
        """
        if not OUTLIER_DETECTION['enabled']:
            return np.zeros(len(X), dtype=bool)
        
        method = OUTLIER_DETECTION['method']
        threshold = OUTLIER_DETECTION['threshold']
        
        print(f"\nDetecting outliers using {method} (threshold={threshold})...")
        
        if method == 'zscore':
            # Z-score on features
            z_scores = np.abs((X - X.mean(axis=0)) / (X.std(axis=0) + 1e-8))
            outliers = (z_scores > threshold).any(axis=1)
        
        elif method == 'iqr':
            # IQR method on features
            q1 = np.percentile(X, 25, axis=0)
            q3 = np.percentile(X, 75, axis=0)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            outliers = ((X < lower) | (X > upper)).any(axis=1)
        
        elif method == 'isolation_forest':
            from sklearn.ensemble import IsolationForest
            clf = IsolationForest(contamination=0.1, random_state=RANDOM_SEED)
            outliers = clf.fit_predict(X) == -1
        
        else:
            raise ValueError(f"Unknown outlier detection method: {method}")
        
        n_outliers = outliers.sum()
        print(f"  - Found {n_outliers} outliers ({100*n_outliers/len(X):.2f}%)")
        
        return outliers
    
    def save(self, filepath: Path):
        """Save preprocessor to file."""
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
        print(f"Preprocessor saved to: {filepath}")
    
    @staticmethod
    def load(filepath: Path) -> 'CSIPreprocessor':
        """Load preprocessor from file."""
        with open(filepath, 'rb') as f:
            preprocessor = pickle.load(f)
        print(f"Preprocessor loaded from: {filepath}")
        return preprocessor


def preprocess_dataset(dataset_path=None, remove_outliers=True, save_processed=True):
    """
    Complete preprocessing pipeline.
    
    Args:
        dataset_path: Path to dataset
        remove_outliers: Whether to remove outliers
        save_processed: Whether to save processed data
    
    Returns:
        X_train, y_train, X_val, y_val, preprocessor
    """
    print("\n" + "=" * 70)
    print("DATA PREPROCESSING PIPELINE")
    print("=" * 70)
    
    # Load data
    loader = CSIDataLoader(dataset_path)
    X_train, y_train, X_val, y_val = loader.load_all()
    
    print(f"\nOriginal data shapes:")
    print(f"  Training: X={X_train.shape}, y={y_train.shape}")
    if X_val is not None:
        print(f"  Validation: X={X_val.shape}, y={y_val.shape}")
    
    # Detect and remove outliers
    if remove_outliers and OUTLIER_DETECTION['enabled']:
        preprocessor_temp = CSIPreprocessor()
        outliers_train = preprocessor_temp.detect_outliers(X_train, y_train)
        
        if outliers_train.any():
            print(f"\nRemoving {outliers_train.sum()} outliers from training set...")
            X_train = X_train[~outliers_train]
            y_train = y_train[~outliers_train]
            print(f"  New training shape: X={X_train.shape}")
        
        if X_val is not None:
            outliers_val = preprocessor_temp.detect_outliers(X_val, y_val)
            if outliers_val.any():
                print(f"Removing {outliers_val.sum()} outliers from validation set...")
                X_val = X_val[~outliers_val]
                y_val = y_val[~outliers_val]
                print(f"  New validation shape: X={X_val.shape}")
    
    # Fit preprocessor on COMBINED train+val data to avoid distribution mismatch
    # This ensures both sets get normalized to the same statistics
    print("\n⚠️  Fitting scaler on combined train+val data to prevent distribution mismatch")
    preprocessor = CSIPreprocessor()
    
    if X_val is not None:
        X_combined = np.vstack([X_train, X_val])
        y_combined = np.vstack([y_train, y_val])
        print(f"  Combined data shape: X={X_combined.shape}, y={y_combined.shape}")
        preprocessor.fit(X_combined, y_combined)
        # Free memory immediately
        del X_combined, y_combined
    else:
        preprocessor.fit(X_train, y_train)
    
    # Now transform train and val separately (more memory efficient)
    X_train_processed = preprocessor.transform(X_train)
    
    print(f"\nProcessed training shape: {X_train_processed.shape}")
    
    # Transform validation data
    X_val_processed = None
    if X_val is not None:
        X_val_processed = preprocessor.transform(X_val)
        print(f"Processed validation shape: {X_val_processed.shape}")
    
    # Save processed data and preprocessor
    if save_processed:
        output_dir = OUTPUT_DIR / "processed_data"
        output_dir.mkdir(exist_ok=True)
        
        # Save preprocessor
        preprocessor.save(output_dir / "preprocessor.pkl")
        
        # Save processed data
        np.savez(output_dir / "processed_train.npz", X=X_train_processed, y=y_train)
        print(f"Saved: {output_dir / 'processed_train.npz'}")
        
        if X_val_processed is not None:
            np.savez(output_dir / "processed_val.npz", X=X_val_processed, y=y_val)
            print(f"Saved: {output_dir / 'processed_val.npz'}")
    
    print("\n" + "=" * 70)
    print("PREPROCESSING COMPLETE!")
    print("=" * 70 + "\n")
    
    return X_train_processed, y_train, X_val_processed, y_val, preprocessor


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Preprocess CSI dataset')
    parser.add_argument('--dataset_path', type=str, default=None,
                       help='Path to dataset folder (default: from config)')
    parser.add_argument('--no_outlier_removal', action='store_true',
                       help='Disable outlier removal')
    parser.add_argument('--no_save', action='store_true',
                       help='Do not save processed data')
    
    args = parser.parse_args()
    
    # Run preprocessing
    preprocess_dataset(
        dataset_path=args.dataset_path,
        remove_outliers=not args.no_outlier_removal,
        save_processed=not args.no_save
    )


if __name__ == "__main__":
    main()
