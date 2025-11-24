"""
Utility functions for ML pipeline.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Tuple


def calculate_localization_error(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """
    Calculate Euclidean distance error for localization.
    
    Args:
        y_true: True positions [N, 2]
        y_pred: Predicted positions [N, 2]
    
    Returns:
        Distance errors [N,] in meters
    """
    return np.linalg.norm(y_true - y_pred, axis=1)


def plot_prediction_scatter(y_true: np.ndarray, y_pred: np.ndarray, 
                           title: str = "Predictions", 
                           save_path: Path = None):
    """
    Plot true vs predicted positions.
    
    Args:
        y_true: True positions [N, 2]
        y_pred: Predicted positions [N, 2]
        title: Plot title
        save_path: Path to save figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # X coordinate
    axes[0].scatter(y_true[:, 0], y_pred[:, 0], alpha=0.5, s=20)
    axes[0].plot([y_true[:, 0].min(), y_true[:, 0].max()], 
                [y_true[:, 0].min(), y_true[:, 0].max()], 
                'r--', linewidth=2, label='Perfect Prediction')
    axes[0].set_xlabel('True X (m)', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Predicted X (m)', fontsize=12, fontweight='bold')
    axes[0].set_title('X Coordinate Prediction', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_aspect('equal')
    
    # Y coordinate
    axes[1].scatter(y_true[:, 1], y_pred[:, 1], alpha=0.5, s=20)
    axes[1].plot([y_true[:, 1].min(), y_true[:, 1].max()], 
                [y_true[:, 1].min(), y_true[:, 1].max()], 
                'r--', linewidth=2, label='Perfect Prediction')
    axes[1].set_xlabel('True Y (m)', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('Predicted Y (m)', fontsize=12, fontweight='bold')
    axes[1].set_title('Y Coordinate Prediction', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].set_aspect('equal')
    
    plt.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    plt.close()


def plot_error_distribution(errors: np.ndarray, 
                            title: str = "Localization Error Distribution",
                            save_path: Path = None):
    """
    Plot distribution of localization errors.
    
    Args:
        errors: Distance errors [N,]
        title: Plot title
        save_path: Path to save figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Histogram
    axes[0].hist(errors, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
    axes[0].axvline(errors.mean(), color='red', linestyle='--', 
                   linewidth=2, label=f'Mean: {errors.mean():.2f}m')
    axes[0].axvline(np.median(errors), color='orange', linestyle='--', 
                   linewidth=2, label=f'Median: {np.median(errors):.2f}m')
    axes[0].set_xlabel('Localization Error (m)', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Frequency', fontsize=12, fontweight='bold')
    axes[0].set_title('Error Histogram', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # CDF
    sorted_errors = np.sort(errors)
    cdf = np.arange(1, len(sorted_errors) + 1) / len(sorted_errors)
    axes[1].plot(sorted_errors, cdf * 100, linewidth=2, color='steelblue')
    
    # Mark percentiles
    percentiles = [50, 75, 90, 95]
    for p in percentiles:
        val = np.percentile(errors, p)
        axes[1].axvline(val, color='red', linestyle=':', alpha=0.5)
        axes[1].text(val, p - 5, f'{p}th: {val:.1f}m', 
                    fontsize=9, rotation=90, va='bottom')
    
    axes[1].set_xlabel('Localization Error (m)', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('CDF (%)', fontsize=12, fontweight='bold')
    axes[1].set_title('Cumulative Distribution', fontsize=14, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim([0, 105])
    
    plt.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    plt.close()


def plot_spatial_errors(y_true: np.ndarray, y_pred: np.ndarray,
                        title: str = "Spatial Error Distribution",
                        save_path: Path = None):
    """
    Plot errors in spatial context.
    
    Args:
        y_true: True positions [N, 2]
        y_pred: Predicted positions [N, 2]
        title: Plot title
        save_path: Path to save figure
    """
    errors = calculate_localization_error(y_true, y_pred)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # True positions colored by error
    scatter1 = axes[0].scatter(y_true[:, 0], y_true[:, 1], 
                              c=errors, cmap='hot_r', 
                              s=50, alpha=0.7, edgecolors='k', linewidth=0.5)
    axes[0].set_xlabel('X Position (m)', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Y Position (m)', fontsize=12, fontweight='bold')
    axes[0].set_title('True Positions (colored by error)', fontsize=14, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_aspect('equal')
    cbar1 = plt.colorbar(scatter1, ax=axes[0])
    cbar1.set_label('Error (m)', fontsize=11)
    
    # Error vectors
    axes[1].quiver(y_true[:, 0], y_true[:, 1], 
                  y_pred[:, 0] - y_true[:, 0], 
                  y_pred[:, 1] - y_true[:, 1],
                  errors, cmap='hot_r', alpha=0.6, scale=1, scale_units='xy')
    axes[1].scatter(y_true[:, 0], y_true[:, 1], 
                   c='blue', s=30, marker='o', alpha=0.3, label='True')
    axes[1].scatter(y_pred[:, 0], y_pred[:, 1], 
                   c='red', s=30, marker='x', alpha=0.3, label='Predicted')
    axes[1].set_xlabel('X Position (m)', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('Y Position (m)', fontsize=12, fontweight='bold')
    axes[1].set_title('Error Vectors', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].set_aspect('equal')
    
    plt.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    plt.close()


def print_metrics_summary(metrics: dict, model_name: str = "Model"):
    """
    Print formatted metrics summary.
    
    Args:
        metrics: Dictionary with evaluation metrics
        model_name: Name of the model
    """
    print(f"\n{'=' * 60}")
    print(f"{model_name.upper()} EVALUATION METRICS")
    print(f"{'=' * 60}")
    print(f"\nPosition Errors:")
    print(f"  MAE:        {metrics['position_mae']:.2f} m")
    print(f"  RMSE:       {metrics['position_rmse']:.2f} m")
    print(f"  Max Error:  {metrics['position_max']:.2f} m")
    print(f"  Median:     {metrics['position_median']:.2f} m")
    
    print(f"\nError Percentiles:")
    print(f"  50th:       {metrics['position_50th']:.2f} m")
    print(f"  75th:       {metrics['position_75th']:.2f} m")
    print(f"  90th:       {metrics['position_90th']:.2f} m")
    print(f"  95th:       {metrics['position_95th']:.2f} m")
    
    print(f"\nCoordinate-wise Metrics:")
    print(f"  MAE:        {metrics['mae']:.2f}")
    print(f"  RMSE:       {metrics['rmse']:.2f}")
    print(f"  R² Score:   {metrics['r2']:.4f}")
    
    if 'training_time' in metrics:
        print(f"\nTraining Time: {metrics['training_time']:.2f} seconds")
    
    print(f"{'=' * 60}\n")


def create_summary_plots(model, X_val, y_val, model_name: str, output_dir: Path):
    """
    Create comprehensive evaluation plots for a model.
    
    Args:
        model: Trained model with predict() method
        X_val: Validation features
        y_val: Validation targets
        model_name: Name of the model
        output_dir: Directory to save plots
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Make predictions
    y_pred = model.predict(X_val)
    errors = calculate_localization_error(y_val, y_pred)
    
    # Plot 1: Prediction scatter
    plot_prediction_scatter(y_val, y_pred, 
                           title=f"{model_name} - Predictions",
                           save_path=output_dir / f"{model_name}_predictions.png")
    
    # Plot 2: Error distribution
    plot_error_distribution(errors,
                           title=f"{model_name} - Error Distribution",
                           save_path=output_dir / f"{model_name}_errors.png")
    
    # Plot 3: Spatial errors
    plot_spatial_errors(y_val, y_pred,
                       title=f"{model_name} - Spatial Errors",
                       save_path=output_dir / f"{model_name}_spatial.png")
    
    print(f"\nGenerated evaluation plots for {model_name} in: {output_dir}")


if __name__ == "__main__":
    # Example usage
    print("Utility functions for ML pipeline")
    print("Import and use in your scripts:")
    print("  from utils import calculate_localization_error, plot_error_distribution, ...")
