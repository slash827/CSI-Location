#!/usr/bin/env python3
"""
Optimized training script for NLOS-enhanced dataset (exp11).

Key improvements:
- Uses exp11 NLOS dataset by default
- Reduced early stopping patience (8 instead of 15)
- Better learning rate scheduling
- Improved network architecture options
- Supports different scheduler types
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import argparse
import time
from pathlib import Path

from config import DEFAULT_DATASET_PATH
from preprocessing import preprocess_dataset
from models import MLPLocalization, CNNLocalization, ResNetLocalization
from utils import calculate_localization_error
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Additional schedulers
from torch.optim.lr_scheduler import (
    ReduceLROnPlateau,
    CosineAnnealingLR, 
    OneCycleLR,
    StepLR
)


class CSIDataset(Dataset):
    """PyTorch dataset for CSI data with proper reshaping for CNN/ResNet."""
    
    def __init__(self, X, y, model_type='mlp'):
        """
        Initialize dataset.
        
        Args:
            X: Features [N, 12291] (3 wideband + 4*1024*3 per-subcarrier)
            y: Targets [N, 2]
            model_type: 'mlp', 'cnn', or 'resnet'
        """
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
        self.model_type = model_type
        
        # Reshape for CNN/ResNet if needed
        if model_type in ['cnn', 'resnet']:
            self.X = self._reshape_for_cnn(self.X)
    
    def _reshape_for_cnn(self, X):
        """
        Reshape features for CNN input.
        
        From: [N, 12291] where features are [wideband(3), RSS(4*1024), SINR(4*1024), H_mag(4*1024)]
        To: [N, 3, 4*1024] where channels are [RSS, SINR, H_mag]
        """
        N = X.shape[0]
        n_features = X.shape[1]
        
        # Calculate per-subcarrier features
        n_wideband = 3
        n_subcarrier_features = n_features - n_wideband
        n_subcarriers = n_subcarrier_features // 3  # RSS, SINR, H_mag
        
        # Extract per-subcarrier features (skip wideband)
        rss = X[:, 3:3+n_subcarriers]              # [N, 4096]
        sinr = X[:, 3+n_subcarriers:3+2*n_subcarriers]  # [N, 4096]
        h_mag = X[:, 3+2*n_subcarriers:3+3*n_subcarriers]  # [N, 4096]
        
        # Stack into channels: [N, 3, n_subcarriers]
        X_reshaped = torch.stack([rss, sinr, h_mag], dim=1)
        
        return X_reshaped
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def calculate_metrics(y_true, y_pred):
    """
    Calculate comprehensive metrics for position prediction.
    
    Args:
        y_true: True positions [N, 2]
        y_pred: Predicted positions [N, 2]
    
    Returns:
        Dictionary with metrics
    """
    # Coordinate-wise metrics
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    
    # Position errors (Euclidean distance)
    position_errors = calculate_localization_error(y_true, y_pred)
    
    # Per-coordinate MAE
    mae_x = mean_absolute_error(y_true[:, 0], y_pred[:, 0])
    mae_y = mean_absolute_error(y_true[:, 1], y_pred[:, 1])
    
    return {
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'mae_x': mae_x,
        'mae_y': mae_y,
        'position_mae': position_errors.mean(),
        'position_rmse': np.sqrt((position_errors**2).mean()),
        'position_median': np.median(position_errors),
        'position_90th': np.percentile(position_errors, 90),
        'position_95th': np.percentile(position_errors, 95),
    }


def train_epoch(model, loader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    
    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)
        
        optimizer.zero_grad()
        
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)
        
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item() * X_batch.size(0)
    
    return total_loss / len(loader.dataset)


def validate(model, loader, criterion, device, target_scaler=None):
    """Validate model."""
    model.eval()
    total_loss = 0
    predictions = []
    targets = []
    
    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            
            total_loss += loss.item() * X_batch.size(0)
            
            predictions.append(outputs.cpu().numpy())
            targets.append(y_batch.cpu().numpy())
    
    predictions = np.vstack(predictions)
    targets = np.vstack(targets)
    
    # Denormalize if scaler provided
    if target_scaler is not None:
        predictions = target_scaler.inverse_transform(predictions)
        targets = target_scaler.inverse_transform(targets)
    
    val_loss = total_loss / len(loader.dataset)
    metrics = calculate_metrics(targets, predictions)
    
    return val_loss, metrics, predictions


def train_model(model, train_loader, val_loader, config, device, target_scaler=None):
    """Training loop with optimizations."""
    
    model = model.to(device)
    
    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(
        model.parameters(), 
        lr=config['lr'], 
        weight_decay=config['weight_decay']
    )
    
    # Learning rate scheduler
    if config['scheduler'] == 'plateau':
        scheduler = ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, 
            patience=config['scheduler_patience']
        )
    elif config['scheduler'] == 'cosine':
        scheduler = CosineAnnealingLR(
            optimizer, T_max=config['epochs'], eta_min=1e-6
        )
    elif config['scheduler'] == 'onecycle':
        scheduler = OneCycleLR(
            optimizer, max_lr=config['lr'], 
            epochs=config['epochs'],
            steps_per_epoch=len(train_loader)
        )
    elif config['scheduler'] == 'step':
        scheduler = StepLR(
            optimizer, step_size=config['step_size'], gamma=0.5
        )
    else:
        scheduler = None
    
    # Training history
    history = {
        'train_loss': [],
        'val_loss': [],
        'val_mae': [],
        'val_r2': [],
        'lr': []
    }
    
    best_val_mae = float('inf')
    best_model_state = None
    patience_counter = 0
    
    print(f"\n{'='*70}")
    print("Starting Training")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    for epoch in range(config['epochs']):
        epoch_start = time.time()
        
        # Train
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        
        # Validate
        val_loss, metrics, _ = validate(model, val_loader, criterion, device, target_scaler)
        
        # Learning rate scheduling
        if config['scheduler'] == 'plateau':
            scheduler.step(val_loss)
        elif config['scheduler'] in ['cosine', 'step']:
            scheduler.step()
        # OneCycleLR steps per batch, not per epoch
        
        current_lr = optimizer.param_groups[0]['lr']
        
        # Store history
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_mae'].append(metrics['mae'])
        history['val_r2'].append(metrics['r2'])
        history['lr'].append(current_lr)
        
        epoch_time = time.time() - epoch_start
        
        # Print progress
        print(f"Epoch {epoch+1}/{config['epochs']} ({epoch_time:.1f}s)")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_loss:.4f}")
        print(f"  Val MAE: {metrics['mae']:.2f} m")
        print(f"  Val R²: {metrics['r2']:.4f}")
        print(f"  LR: {current_lr:.6f}")
        
        # Early stopping check
        if metrics['mae'] < best_val_mae:
            best_val_mae = metrics['mae']
            best_model_state = model.state_dict().copy()
            patience_counter = 0
            print(f"  ✓ New best model! (MAE: {best_val_mae:.2f} m)")
        else:
            patience_counter += 1
        
        print()
        
        # Early stopping
        if patience_counter >= config['early_stopping_patience']:
            print(f"Early stopping triggered after {epoch+1} epochs")
            break
    
    total_time = time.time() - start_time
    
    print("="*70)
    print(f"Training completed in {total_time/60:.1f} minutes")
    print(f"Best validation MAE: {best_val_mae:.2f} m")
    print("="*70)
    
    # Load best model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    return model, history


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Optimized neural network training for NLOS dataset')
    
    # Model configuration
    parser.add_argument('--model', type=str, default='resnet',
                       choices=['mlp', 'cnn', 'resnet'],
                       help='Model type (default: resnet)')
    parser.add_argument('--epochs', type=int, default=100,
                       help='Number of epochs (default: 100)')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Batch size (default: 32)')
    
    # Optimizer settings
    parser.add_argument('--lr', type=float, default=0.001,
                       help='Learning rate (default: 0.001)')
    parser.add_argument('--weight_decay', type=float, default=1e-4,
                       help='Weight decay (default: 1e-4)')
    
    # Scheduler settings
    parser.add_argument('--scheduler', type=str, default='plateau',
                       choices=['plateau', 'cosine', 'onecycle', 'step', 'none'],
                       help='LR scheduler type (default: plateau)')
    parser.add_argument('--scheduler_patience', type=int, default=4,
                       help='Patience for ReduceLROnPlateau (default: 4)')
    parser.add_argument('--step_size', type=int, default=15,
                       help='Step size for StepLR (default: 15)')
    
    # Early stopping
    parser.add_argument('--early_stopping_patience', type=int, default=8,
                       help='Early stopping patience (default: 8)')
    
    # Dataset
    parser.add_argument('--dataset_path', type=str, default=None,
                       help='Path to dataset (default: exp11 from config)')
    
    # Device
    parser.add_argument('--device', type=str, default='auto',
                       choices=['auto', 'cuda', 'cpu'],
                       help='Device to use (default: auto)')
    
    args = parser.parse_args()
    
    # Determine device
    if args.device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    else:
        device = args.device
    
    print("="*70)
    print(f"OPTIMIZED NEURAL NETWORK TRAINING - {args.model.upper()}")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Model: {args.model}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.lr}")
    print(f"  Weight decay: {args.weight_decay}")
    print(f"  Scheduler: {args.scheduler}")
    print(f"  Early stopping patience: {args.early_stopping_patience}")
    print(f"  Device: {device}")
    print()
    
    # Load and preprocess data
    print("="*70)
    print("LOADING DATA")
    print("="*70)
    
    dataset_path = Path(args.dataset_path).resolve() if args.dataset_path else DEFAULT_DATASET_PATH.resolve()
    print(f"\nDataset: {dataset_path}")
    
    if not dataset_path.exists():
        print(f"\nERROR: Dataset path does not exist: {dataset_path}")
        print(f"Please ensure the dataset was generated correctly.")
        return
    
    X_train, y_train, X_val, y_val, preprocessor = preprocess_dataset(dataset_path)
    
    print(f"\n✓ Data loaded:")
    print(f"  Training: X={X_train.shape}, y={y_train.shape}")
    print(f"  Validation: X={X_val.shape}, y={y_val.shape}")
    print(f"  Position range: [{y_train.min():.1f}, {y_train.max():.1f}]")
    
    # Create datasets and loaders
    train_dataset = CSIDataset(X_train, y_train, model_type=args.model)
    val_dataset = CSIDataset(X_val, y_val, model_type=args.model)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    
    print(f"\n✓ Created data loaders:")
    print(f"  Train batches: {len(train_loader)}")
    print(f"  Val batches: {len(val_loader)}")
    
    # Create model
    print("\n" + "="*70)
    print("CREATING MODEL")
    print("="*70)
    
    n_features = X_train.shape[1]
    
    # For per-subcarrier models (CNN, ResNet)
    n_wideband = 3
    n_subcarrier_features = n_features - n_wideband
    n_subcarriers = n_subcarrier_features // 3  # RSS, SINR, H_mag per subcarrier
    
    if args.model == 'mlp':
        model = MLPLocalization(input_dim=n_features)
    elif args.model == 'cnn':
        model = CNNLocalization(n_subcarriers=n_subcarriers)
    elif args.model == 'resnet':
        model = ResNetLocalization(n_subcarriers=n_subcarriers)
    
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n✓ Created {args.model.upper()} model")
    print(f"  Parameters: {n_params:,}")
    print(f"  Device: {device}")
    
    # Training configuration
    config = {
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'lr': args.lr,
        'weight_decay': args.weight_decay,
        'scheduler': args.scheduler,
        'scheduler_patience': args.scheduler_patience,
        'step_size': args.step_size,
        'early_stopping_patience': args.early_stopping_patience,
    }
    
    # Train model
    model, history = train_model(model, train_loader, val_loader, config, device, target_scaler=None)
    
    # Final evaluation
    print("\n" + "="*70)
    print("FINAL EVALUATION")
    print("="*70)
    
    val_loss, metrics, predictions = validate(model, val_loader, nn.MSELoss(), device, target_scaler=None)
    
    print(f"\nValidation Metrics:")
    print(f"  Position MAE: {metrics['mae']:.2f} m")
    print(f"  Position RMSE: {metrics['rmse']:.2f} m")
    print(f"  X MAE: {metrics['mae_x']:.2f} m")
    print(f"  Y MAE: {metrics['mae_y']:.2f} m")
    print(f"  R² Score: {metrics['r2']:.4f}")
    
    # Save model
    output_dir = Path(__file__).parent.parent.parent / 'output' / 'results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    model_dir = output_dir / f'{args.model}_optimized_nlos_{timestamp}'
    model_dir.mkdir(exist_ok=True)
    
    model_path = model_dir / f'{args.model}_model.pth'
    torch.save(model.state_dict(), model_path)
    print(f"\n✓ Model saved to: {model_path}")
    
    # Save results
    import json
    
    # Convert numpy types to Python types for JSON serialization
    def convert_to_python_types(obj):
        if isinstance(obj, dict):
            return {k: convert_to_python_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_python_types(v) for v in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        else:
            return obj
    
    results = {
        'config': config,
        'metrics': convert_to_python_types(metrics),
        'history': {k: [float(v) for v in vals] for k, vals in history.items()},
        'dataset_path': str(dataset_path),
    }
    
    results_path = model_dir / 'results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✓ Results saved to: {results_path}")
    
    print("\n" + "="*70)
    print("TRAINING COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()
