"""
Feature selection module for reducing dimensionality.

Reduces 3,075 features to ~500-1000 most informative features.
"""

import numpy as np
from sklearn.feature_selection import mutual_info_regression, SelectKBest, f_regression
from sklearn.decomposition import PCA
from typing import Tuple, List
import time


class FeatureSelector:
    """Select most informative features for localization."""
    
    def __init__(self, method='mutual_info', n_features=500, variance_threshold=0.95):
        """
        Initialize feature selector.
        
        Args:
            method: 'mutual_info', 'f_test', 'pca', or 'variance'
            n_features: Number of features to select (ignored for PCA with variance_threshold)
            variance_threshold: For PCA, keep components explaining this much variance
        """
        self.method = method
        self.n_features = n_features
        self.variance_threshold = variance_threshold
        self.selector = None
        self.selected_indices = None
        self.feature_scores = None
        
    def fit(self, X: np.ndarray, y: np.ndarray):
        """
        Fit feature selector.
        
        Args:
            X: Features [N, D]
            y: Targets [N, 2] (x, y positions)
        """
        print(f"\nFitting feature selector: {self.method}")
        print(f"  Input features: {X.shape[1]}")
        start_time = time.time()
        
        if self.method == 'mutual_info':
            self._fit_mutual_info(X, y)
        elif self.method == 'f_test':
            self._fit_f_test(X, y)
        elif self.method == 'pca':
            self._fit_pca(X)
        elif self.method == 'variance':
            self._fit_variance(X)
        else:
            raise ValueError(f"Unknown method: {self.method}")
        
        elapsed = time.time() - start_time
        print(f"  Selected features: {self.get_n_features()}")
        print(f"  Time: {elapsed:.2f}s")
        
        return self
    
    def _fit_mutual_info(self, X, y):
        """Fit using mutual information."""
        # Use average of x and y positions for scoring
        y_avg = y.mean(axis=1)
        
        print("  Computing mutual information scores...")
        scores = mutual_info_regression(X, y_avg, random_state=42)
        self.feature_scores = scores
        
        # Select top k features
        self.selected_indices = np.argsort(scores)[-self.n_features:]
        self.selected_indices = np.sort(self.selected_indices)  # Keep original order
        
    def _fit_f_test(self, X, y):
        """Fit using F-test (ANOVA)."""
        y_avg = y.mean(axis=1)
        
        print("  Computing F-scores...")
        selector = SelectKBest(f_regression, k=self.n_features)
        selector.fit(X, y_avg)
        
        self.selector = selector
        self.selected_indices = selector.get_support(indices=True)
        self.feature_scores = selector.scores_
        
    def _fit_pca(self, X):
        """Fit using PCA."""
        print(f"  Computing PCA (variance threshold: {self.variance_threshold})...")
        
        pca = PCA(n_components=self.variance_threshold, random_state=42)
        pca.fit(X)
        
        self.selector = pca
        self.selected_indices = np.arange(pca.n_components_)
        
        print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.4f}")
        
    def _fit_variance(self, X):
        """Fit using variance threshold."""
        from sklearn.feature_selection import VarianceThreshold
        
        print(f"  Computing feature variances...")
        selector = VarianceThreshold()
        selector.fit(X)
        
        variances = selector.variances_
        self.feature_scores = variances
        
        # Select top k by variance
        self.selected_indices = np.argsort(variances)[-self.n_features:]
        self.selected_indices = np.sort(self.selected_indices)
        
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Transform features.
        
        Args:
            X: Features [N, D]
        
        Returns:
            Reduced features [N, K] where K < D
        """
        if self.method == 'pca':
            return self.selector.transform(X)
        else:
            return X[:, self.selected_indices]
    
    def fit_transform(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(X, y)
        return self.transform(X)
    
    def get_n_features(self) -> int:
        """Get number of selected features."""
        if self.method == 'pca':
            return self.selector.n_components_
        else:
            return len(self.selected_indices)
    
    def get_feature_importance(self, top_k=50) -> List[Tuple[int, float]]:
        """
        Get top k most important features.
        
        Returns:
            List of (feature_index, score) tuples
        """
        if self.feature_scores is None:
            return []
        
        indices = np.argsort(self.feature_scores)[-top_k:][::-1]
        return [(int(idx), float(self.feature_scores[idx])) for idx in indices]
    
    def save(self, filepath):
        """Save selector to file."""
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
        print(f"Feature selector saved to: {filepath}")
    
    @staticmethod
    def load(filepath):
        """Load selector from file."""
        import pickle
        with open(filepath, 'rb') as f:
            selector = pickle.load(f)
        print(f"Feature selector loaded from: {filepath}")
        return selector


def quick_feature_selection(X_train, y_train, X_val, y_val, 
                            n_features=500, method='mutual_info'):
    """
    Quick feature selection helper.
    
    Args:
        X_train: Training features
        y_train: Training targets
        X_val: Validation features
        y_val: Validation targets
        n_features: Number of features to select
        method: Selection method
    
    Returns:
        X_train_reduced, X_val_reduced, selector
    """
    selector = FeatureSelector(method=method, n_features=n_features)
    
    X_train_reduced = selector.fit_transform(X_train, y_train)
    X_val_reduced = selector.transform(X_val)
    
    print(f"\n✓ Feature reduction complete:")
    print(f"  {X_train.shape[1]} → {X_train_reduced.shape[1]} features")
    print(f"  Reduction: {100 * (1 - X_train_reduced.shape[1]/X_train.shape[1]):.1f}%")
    
    return X_train_reduced, X_val_reduced, selector


if __name__ == "__main__":
    # Test with dummy data
    print("Testing feature selector...")
    
    X = np.random.randn(1000, 100)
    y = np.random.randn(1000, 2)
    
    selector = FeatureSelector(method='mutual_info', n_features=20)
    X_reduced = selector.fit_transform(X, y)
    
    print(f"\nOriginal shape: {X.shape}")
    print(f"Reduced shape: {X_reduced.shape}")
    print(f"\nTop 10 features:")
    for idx, score in selector.get_feature_importance(top_k=10):
        print(f"  Feature {idx}: {score:.4f}")
