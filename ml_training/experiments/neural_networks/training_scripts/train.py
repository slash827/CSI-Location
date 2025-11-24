"""
Training script for neural network models.

Trains MLP, CNN, and ResNet on CSI localization task.
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import time
from datetime import datetime
import json
import argparse

from models import create_model, count_parameters
from config import DEFAULT_DATASET_PATH, RANDOM_SEED, OUTPUT_DIR
from data_loader import CSIDataLoader
from preprocessing import preprocess_dataset


# Set random seeds for reproducibility
torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)


class CSIDataset(Dataset):
    """PyTorch dataset for CSI data."""
    
    def __init__(self, X, y, model_type='mlp'):
        """
        Initialize dataset.
        
        Args:
            X: Features [N, 3075]
            y: Targets [N, 2]
            model_type: 'mlp', 'cnn', or 'resnet'
        """
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
        self.model_type = model_type
        
        # Reshape for CNN/ResNet if needed
        if model_type in ['cnn', 'resnet']:
            # Reshape from [N, 3075] to [N, 3, 1024]
            # Assume: 3 wideband + 1024 RSS + 1024 SINR + 1024 H_mag
            self.X = self._reshape_for_cnn(self.X)
    
    def _reshape_for_cnn(self, X):
        """
        Reshape features for CNN input.
        
        From: [N, 3075] where features are [wideband(3), RSS(1024), SINR(1024), H_mag(1024)]
        To: [N, 3, 1024] where channels are [RSS, SINR, H_mag]
        """
        N = X.shape[0]
        
        # Extract per-subcarrier features (skip wideband for now)
        rss = X[:, 3:3+1024]      # [N, 1024]
        sinr = X[:, 3+1024:3+2048]  # [N, 1024]
        h_mag = X[:, 3+2048:3+3072]  # [N, 1024]
        
        # Stack as channels
        X_reshaped = torch.stack([rss, sinr, h_mag], dim=1)  # [N, 3, 1024]
        
        return X_reshaped
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def compute_metrics(y_true, y_pred):
    """
    Compute position-based metrics.
    
    Args:
        y_true: True positions [N, 2]
        y_pred: Predicted positions [N, 2]
    
    Returns:
        metrics: Dictionary of metrics
    """
    # Convert to numpy if needed
    if isinstance(y_true, torch.Tensor):
        y_true = y_true.cpu().numpy()
    if isinstance(y_pred, torch.Tensor):
        y_pred = y_pred.cpu().numpy()
    
    # Position errors (Euclidean distance)
    position_errors = np.sqrt(np.sum((y_true - y_pred)**2, axis=1))
    
    metrics = {
        'position_mae': np.mean(position_errors),
        'position_rmse': np.sqrt(np.mean(position_errors**2)),
        'x_mae': np.mean(np.abs(y_true[:, 0] - y_pred[:, 0])),
        'y_mae': np.mean(np.abs(y_true[:, 1] - y_pred[:, 1])),
        'r2': 1 - np.sum((y_true - y_pred)**2) / np.sum((y_true - y_true.mean(axis=0))**2),
    }
    
    return metrics


def train_epoch(model, train_loader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    
    for batch_X, batch_y in train_loader:
        batch_X = batch_X.to(device)
        batch_y = batch_y.to(device)
        
        # Forward pass
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item() * batch_X.size(0)
    
    return total_loss / len(train_loader.dataset)


def validate(model, val_loader, criterion, device):
    """Validate model."""
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for batch_X, batch_y in val_loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            
            total_loss += loss.item() * batch_X.size(0)
            all_preds.append(outputs.cpu())
            all_targets.append(batch_y.cpu())
    
    all_preds = torch.cat(all_preds, dim=0)
    all_targets = torch.cat(all_targets, dim=0)
    
    metrics = compute_metrics(all_targets, all_preds)
    metrics['loss'] = total_loss / len(val_loader.dataset)
    
    return metrics


def train_model(model, train_loader, val_loader, config, device):
    """
    Train neural network model.
    
    Args:
        model: PyTorch model
        train_loader: Training data loader
        val_loader: Validation data loader
        config: Training configuration
        device: 'cuda' or 'cpu'
    
    Returns:
        history: Training history
        best_model_state: State dict of best model
    """
    print(f"\nTraining on device: {device}")
    print(f"Model parameters: {count_parameters(model):,}")
    
    model = model.to(device)
    
    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=config['lr'], weight_decay=config['weight_decay'])
    
    # Learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5
    )
    
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
        val_metrics = validate(model, val_loader, criterion, device)
        
        # Update scheduler
        scheduler.step(val_metrics['loss'])
        
        # Record history
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_metrics['loss'])
        history['val_mae'].append(val_metrics['position_mae'])
        history['val_r2'].append(val_metrics['r2'])
        history['lr'].append(optimizer.param_groups[0]['lr'])
        
        epoch_time = time.time() - epoch_start
        
        # Print progress
        print(f"Epoch {epoch+1}/{config['epochs']} ({epoch_time:.1f}s)")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_metrics['loss']:.4f}")
        print(f"  Val MAE: {val_metrics['position_mae']:.2f} m")
        print(f"  Val R²: {val_metrics['r2']:.4f}")
        print(f"  LR: {optimizer.param_groups[0]['lr']:.6f}")
        
        # Save best model
        if val_metrics['position_mae'] < best_val_mae:
            best_val_mae = val_metrics['position_mae']
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
    print(f"{'='*70}")
    print(f"Training completed in {total_time/60:.1f} minutes")
    print(f"Best validation MAE: {best_val_mae:.2f} m")
    print(f"{'='*70}\n")
    
    return history, best_model_state


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train neural network models')
    parser.add_argument('--model', type=str, default='mlp',
                       choices=['mlp', 'cnn', 'resnet'],
                       help='Model type (default: mlp)')
    parser.add_argument('--epochs', type=int, default=100,
                       help='Number of epochs (default: 100)')
    parser.add_argument('--batch_size', type=int, default=256,
                       help='Batch size (default: 256)')
    parser.add_argument('--lr', type=float, default=0.001,
                       help='Learning rate (default: 0.001)')
    parser.add_argument('--weight_decay', type=float, default=1e-4,
                       help='Weight decay (default: 1e-4)')
    parser.add_argument('--early_stopping_patience', type=int, default=15,
                       help='Early stopping patience (default: 15)')
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
    print(f"NEURAL NETWORK TRAINING - {args.model.upper()}")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Model: {args.model}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.lr}")
    print(f"  Weight decay: {args.weight_decay}")
    print(f"  Device: {device}")
    print()
    
    # Load and preprocess data
    print("="*70)
    print("LOADING DATA")
    print("="*70)
    
    X_train, y_train, X_val, y_val, preprocessor = preprocess_dataset(DEFAULT_DATASET_PATH)
    
    print(f"\n✓ Data loaded:")
    print(f"  Training: X={X_train.shape}, y={y_train.shape}")
    print(f"  Validation: X={X_val.shape}, y={y_val.shape}")
    
    # Create datasets and loaders
    train_dataset = CSIDataset(X_train, y_train, model_type=args.model)
    val_dataset = CSIDataset(X_val, y_val, model_type=args.model)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    
    print(f"\n✓ Created data loaders:")
    print(f"  Train batches: {len(train_loader)}")
    print(f"  Val batches: {len(val_loader)}")
    
    # Create model
    print(f"\n{'='*70}")
    print("CREATING MODEL")
    print(f"{'='*70}")
    
    model = create_model(args.model)
    print(f"\n✓ Created {args.model.upper()} model")
    print(f"  Parameters: {count_parameters(model):,}")
    
    # Training configuration
    config = {
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'lr': args.lr,
        'weight_decay': args.weight_decay,
        'early_stopping_patience': args.early_stopping_patience,
    }
    
    # Train model
    history, best_model_state = train_model(model, train_loader, val_loader, config, device)
    
    # Load best model and evaluate
    model.load_state_dict(best_model_state)
    final_metrics = validate(model, val_loader, nn.MSELoss(), device)
    
    print("="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"\nValidation Metrics:")
    print(f"  Position MAE: {final_metrics['position_mae']:.2f} m")
    print(f"  Position RMSE: {final_metrics['position_rmse']:.2f} m")
    print(f"  X MAE: {final_metrics['x_mae']:.2f} m")
    print(f"  Y MAE: {final_metrics['y_mae']:.2f} m")
    print(f"  R² Score: {final_metrics['r2']:.4f}")
    
    # Save model and results
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    save_dir = OUTPUT_DIR / 'results' / f'neural_net_{args.model}_{timestamp}'
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model
    model_path = save_dir / f'{args.model}_model.pth'
    torch.save(best_model_state, model_path)
    print(f"\n✓ Model saved to: {model_path}")
    
    # Save config and results
    results = {
        'model_type': args.model,
        'config': config,
        'final_metrics': {k: float(v) for k, v in final_metrics.items()},
        'history': {k: [float(x) for x in v] for k, v in history.items()},
        'timestamp': timestamp
    }
    
    results_path = save_dir / 'results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✓ Results saved to: {results_path}")
    
    print(f"\n{'='*70}")
    print("TRAINING COMPLETE!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
