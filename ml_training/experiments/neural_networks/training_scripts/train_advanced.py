"""
Advanced training script with multiple optimization strategies.

Features:
- Multiple LR schedulers (Cosine, OneCycle, Warmup+Cosine)
- Hyperparameter configurations
- Extended training epochs
- Better monitoring and checkpointing
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
import math
import logging

from models import create_model, count_parameters
from config import DEFAULT_DATASET_PATH, RANDOM_SEED, OUTPUT_DIR
from data_loader import CSIDataLoader
from preprocessing import preprocess_dataset


# Set random seeds for reproducibility
torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Create runs directory
RUNS_DIR = OUTPUT_DIR.parent / 'runs'
RUNS_DIR.mkdir(parents=True, exist_ok=True)


class CSIDataset(Dataset):
    """PyTorch dataset for CSI features."""
    
    def __init__(self, features, targets, model_type='mlp'):
        self.features = torch.FloatTensor(features)
        self.targets = torch.FloatTensor(targets)
        self.model_type = model_type
        
        # Reshape for CNN/ResNet if needed
        if model_type in ['cnn', 'resnet']:
            # Reshape to (batch, channels=3, subcarriers=1024)
            # Assuming 3075 features = 3 wideband + 4 BSs × 1024 subcarriers × 3 types
            n_samples = self.features.shape[0]
            n_features = self.features.shape[1]
            
            # Extract per-subcarrier features (skip first 3 wideband)
            sc_features = self.features[:, 3:].reshape(n_samples, -1, 1024)
            self.features = sc_features.permute(0, 2, 1)  # (batch, 1024, channels)
            self.features = self.features.permute(0, 2, 1)  # (batch, channels, 1024)
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return self.features[idx], self.targets[idx]


class CosineAnnealingWarmRestarts(optim.lr_scheduler._LRScheduler):
    """Cosine annealing with warm restarts."""
    
    def __init__(self, optimizer, T_0, T_mult=1, eta_min=0, last_epoch=-1):
        self.T_0 = T_0
        self.T_mult = T_mult
        self.eta_min = eta_min
        self.T_cur = last_epoch
        self.T_i = T_0
        super().__init__(optimizer, last_epoch)
    
    def get_lr(self):
        return [self.eta_min + (base_lr - self.eta_min) * 
                (1 + math.cos(math.pi * self.T_cur / self.T_i)) / 2
                for base_lr in self.base_lrs]
    
    def step(self, epoch=None):
        if epoch is None:
            epoch = self.last_epoch + 1
        self.T_cur = self.T_cur + 1 if self.T_cur + 1 < self.T_i else 0
        if self.T_cur == 0:
            self.T_i = self.T_i * self.T_mult
        self.last_epoch = math.floor(epoch)
        for param_group, lr in zip(self.optimizer.param_groups, self.get_lr()):
            param_group['lr'] = lr


def create_scheduler(optimizer, scheduler_type, config, steps_per_epoch=None):
    """Create learning rate scheduler."""
    
    if scheduler_type == 'plateau':
        return optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
    
    elif scheduler_type == 'cosine':
        # Cosine annealing over all epochs
        return optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=config['epochs'], eta_min=config['lr'] * 0.01
        )
    
    elif scheduler_type == 'cosine_restarts':
        # Cosine annealing with warm restarts every T_0 epochs
        T_0 = config.get('restart_period', 20)
        return CosineAnnealingWarmRestarts(
            optimizer, T_0=T_0, T_mult=2, eta_min=config['lr'] * 0.01
        )
    
    elif scheduler_type == 'onecycle':
        # OneCycleLR - requires steps_per_epoch
        if steps_per_epoch is None:
            raise ValueError("steps_per_epoch required for OneCycleLR")
        return optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=config['lr'],
            epochs=config['epochs'],
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3,  # 30% warmup
            anneal_strategy='cos'
        )
    
    elif scheduler_type == 'warmup_cosine':
        # Warmup + Cosine annealing
        warmup_epochs = config.get('warmup_epochs', 5)
        
        def lr_lambda(epoch):
            if epoch < warmup_epochs:
                return (epoch + 1) / warmup_epochs
            else:
                progress = (epoch - warmup_epochs) / (config['epochs'] - warmup_epochs)
                return 0.01 + 0.99 * (1 + math.cos(math.pi * progress)) / 2
        
        return optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    
    else:
        raise ValueError(f"Unknown scheduler type: {scheduler_type}")


def train_epoch(model, train_loader, criterion, optimizer, device, scheduler=None, use_onecycle=False):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    
    for batch_idx, (features, targets) in enumerate(train_loader):
        features, targets = features.to(device), targets.to(device)
        
        optimizer.zero_grad()
        outputs = model(features)
        loss = criterion(outputs, targets)
        loss.backward()
        
        # Gradient clipping (helps stability)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        # Step OneCycleLR after each batch
        if use_onecycle and scheduler is not None:
            scheduler.step()
        
        total_loss += loss.item() * features.size(0)
    
    return total_loss / len(train_loader.dataset)


def validate(model, val_loader, criterion, device):
    """Validate model."""
    model.eval()
    total_loss = 0
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for features, targets in val_loader:
            features, targets = features.to(device), targets.to(device)
            outputs = model(features)
            loss = criterion(outputs, targets)
            
            total_loss += loss.item() * features.size(0)
            all_preds.append(outputs.cpu().numpy())
            all_targets.append(targets.cpu().numpy())
    
    all_preds = np.concatenate(all_preds)
    all_targets = np.concatenate(all_targets)
    
    # Calculate metrics
    errors = np.linalg.norm(all_preds - all_targets, axis=1)
    mae = np.mean(errors)
    
    # R² score
    ss_res = np.sum((all_targets - all_preds) ** 2)
    ss_tot = np.sum((all_targets - np.mean(all_targets, axis=0)) ** 2)
    r2 = 1 - ss_res / ss_tot
    
    metrics = {
        'loss': total_loss / len(val_loader.dataset),
        'position_mae': mae,
        'r2': r2
    }
    
    return metrics


def setup_logger(run_dir, config_name):
    """Setup logging for training run."""
    log_file = run_dir / 'training.log'
    
    # Create logger
    logger = logging.getLogger(f'train_{config_name}')
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Clear existing handlers
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def train_model(model, train_loader, val_loader, config, device, logger=None, run_dir=None):
    """
    Train neural network model with advanced optimization.
    
    Args:
        model: PyTorch model
        train_loader: Training data loader
        val_loader: Validation data loader
        config: Training configuration
        device: 'cuda' or 'cpu'
        logger: Logger instance (optional)
        run_dir: Run directory for saving checkpoints (optional)
    
    Returns:
        history: Training history
        best_model_state: State dict of best model
    """
    # Log configuration
    if logger:
        logger.info("=" * 70)
        logger.info("TRAINING CONFIGURATION")
        logger.info("=" * 70)
        logger.info(f"Device: {device}")
        logger.info(f"Model parameters: {count_parameters(model):,}")
        logger.info(f"Scheduler: {config['scheduler']}")
        logger.info(f"Learning rate: {config['lr']}")
        logger.info(f"Batch size: {config['batch_size']}")
        logger.info(f"Epochs: {config['epochs']}")
        logger.info(f"Weight decay: {config['weight_decay']}")
        logger.info("=" * 70)
    
    print(f"\nTraining Configuration:")
    print(f"  Device: {device}")
    print(f"  Model parameters: {count_parameters(model):,}")
    print(f"  Scheduler: {config['scheduler']}")
    print(f"  Learning rate: {config['lr']}")
    print(f"  Batch size: {config['batch_size']}")
    print(f"  Epochs: {config['epochs']}")
    print(f"  Weight decay: {config['weight_decay']}")
    
    model = model.to(device)
    
    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=config['lr'], weight_decay=config['weight_decay'])
    
    # Learning rate scheduler
    use_onecycle = config['scheduler'] == 'onecycle'
    steps_per_epoch = len(train_loader) if use_onecycle else None
    scheduler = create_scheduler(optimizer, config['scheduler'], config, steps_per_epoch)
    
    # Training history
    history = {
        'train_loss': [],
        'val_loss': [],
        'val_mae': [],
        'val_r2': [],
        'lr': [],
        'epoch_times': []
    }
    
    # Create epoch metrics file
    if run_dir:
        epoch_metrics_file = run_dir / 'epoch_metrics.csv'
        with open(epoch_metrics_file, 'w') as f:
            f.write('epoch,train_loss,val_loss,val_mae,val_r2,lr,epoch_time,best\n')
    
    best_val_mae = float('inf')
    best_val_r2 = -float('inf')
    best_model_state = None
    patience_counter = 0
    
    print(f"\n{'='*70}")
    print("Starting Training")
    print(f"{'='*70}\n")
    
    if logger:
        logger.info("Starting Training")
    
    start_time = time.time()
    
    for epoch in range(config['epochs']):
        epoch_start = time.time()
        
        # Train
        train_loss = train_epoch(
            model, train_loader, criterion, optimizer, device, 
            scheduler if use_onecycle else None, use_onecycle
        )
        
        # Validate
        val_metrics = validate(model, val_loader, criterion, device)
        
        # Update scheduler (non-OneCycle schedulers)
        if not use_onecycle:
            if config['scheduler'] == 'plateau':
                scheduler.step(val_metrics['loss'])
            else:
                scheduler.step()
        
        # Record history
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_metrics['loss'])
        history['val_mae'].append(val_metrics['position_mae'])
        history['val_r2'].append(val_metrics['r2'])
        history['lr'].append(optimizer.param_groups[0]['lr'])
        
        epoch_time = time.time() - epoch_start
        history['epoch_times'].append(epoch_time)
        
        # Check if best model
        is_best = val_metrics['r2'] > best_val_r2
        
        # Print progress
        msg = f"Epoch {epoch+1}/{config['epochs']} ({epoch_time:.1f}s)"
        print(msg)
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_metrics['loss']:.4f}")
        print(f"  Val MAE: {val_metrics['position_mae']:.2f} m")
        print(f"  Val R²: {val_metrics['r2']:.4f}")
        print(f"  LR: {optimizer.param_groups[0]['lr']:.6f}")
        
        # Log to file
        if logger:
            logger.info(f"Epoch {epoch+1}/{config['epochs']} - "
                       f"Train Loss: {train_loss:.4f}, Val Loss: {val_metrics['loss']:.4f}, "
                       f"Val MAE: {val_metrics['position_mae']:.2f}m, Val R²: {val_metrics['r2']:.4f}, "
                       f"LR: {optimizer.param_groups[0]['lr']:.6f}, Time: {epoch_time:.1f}s")
        
        # Save epoch metrics to CSV
        if run_dir:
            with open(epoch_metrics_file, 'a') as f:
                f.write(f"{epoch+1},{train_loss:.6f},{val_metrics['loss']:.6f},"
                       f"{val_metrics['position_mae']:.4f},{val_metrics['r2']:.6f},"
                       f"{optimizer.param_groups[0]['lr']:.8f},{epoch_time:.2f},{int(is_best)}\n")
        
        # Save best model (based on R² primarily)
        if is_best:
            best_val_r2 = val_metrics['r2']
            best_val_mae = val_metrics['position_mae']
            best_model_state = model.state_dict().copy()
            patience_counter = 0
            msg = f"  ✓ New best model! (R²: {best_val_r2:.4f}, MAE: {best_val_mae:.2f} m)"
            print(msg)
            if logger:
                logger.info(f"New best model - R²: {best_val_r2:.4f}, MAE: {best_val_mae:.2f}m")
            
            # Save checkpoint
            if run_dir:
                checkpoint_path = run_dir / 'best_model_checkpoint.pth'
                torch.save({
                    'epoch': epoch + 1,
                    'model_state_dict': best_model_state,
                    'optimizer_state_dict': optimizer.state_dict(),
                    'val_r2': best_val_r2,
                    'val_mae': best_val_mae,
                    'config': config
                }, checkpoint_path)
        else:
            patience_counter += 1
        
        print()
        
        # Early stopping
        if patience_counter >= config['early_stopping_patience']:
            msg = f"Early stopping triggered after {epoch+1} epochs"
            print(msg)
            if logger:
                logger.info(msg)
            break
    
    total_time = time.time() - start_time
    print(f"{'='*70}")
    print(f"Training completed in {total_time/60:.1f} minutes")
    print(f"Best validation R²: {best_val_r2:.4f}")
    print(f"Best validation MAE: {best_val_mae:.2f} m")
    print(f"{'='*70}\n")
    
    if logger:
        logger.info("=" * 70)
        logger.info(f"Training completed in {total_time/60:.1f} minutes")
        logger.info(f"Best validation R²: {best_val_r2:.4f}")
        logger.info(f"Best validation MAE: {best_val_mae:.2f} m")
        logger.info("=" * 70)
    
    return history, best_model_state


# ============================================================================
# PREDEFINED CONFIGURATIONS
# ============================================================================

CONFIGS = {
    # Baseline (your current setup)
    'baseline_resnet': {
        'model': 'resnet',
        'lr': 0.0005,
        'batch_size': 128,
        'epochs': 50,
        'weight_decay': 0.0,
        'scheduler': 'plateau',
        'early_stopping_patience': 10,  # More aggressive
    },
    
    # Extended training with cosine annealing
    'resnet_cosine_100': {
        'model': 'resnet',
        'lr': 0.001,
        'batch_size': 128,
        'epochs': 100,
        'weight_decay': 1e-5,
        'scheduler': 'cosine',
        'early_stopping_patience': 12,  # More aggressive to prevent overfitting
    },
    
    # Cosine with warm restarts
    'resnet_cosine_restarts': {
        'model': 'resnet',
        'lr': 0.001,
        'batch_size': 128,
        'epochs': 120,
        'weight_decay': 1e-5,
        'scheduler': 'cosine_restarts',
        'restart_period': 20,
        'early_stopping_patience': 15,  # More aggressive
    },
    
    # OneCycleLR - fast convergence
    'resnet_onecycle': {
        'model': 'resnet',
        'lr': 0.003,  # Higher max LR for OneCycle
        'batch_size': 256,
        'epochs': 80,
        'weight_decay': 1e-4,
        'scheduler': 'onecycle',
        'early_stopping_patience': 12,  # More aggressive
    },
    
    # Warmup + Cosine
    'resnet_warmup_cosine': {
        'model': 'resnet',
        'lr': 0.002,
        'batch_size': 256,
        'epochs': 100,
        'weight_decay': 5e-5,
        'scheduler': 'warmup_cosine',
        'warmup_epochs': 10,
        'early_stopping_patience': 12,  # More aggressive
    },
    
    # High-capacity MLP with aggressive training
    'mlp_aggressive': {
        'model': 'mlp',
        'lr': 0.002,
        'batch_size': 512,
        'epochs': 100,
        'weight_decay': 1e-4,
        'scheduler': 'cosine',
        'early_stopping_patience': 12,  # More aggressive
    },
    
    # CNN with OneCycle
    'cnn_onecycle': {
        'model': 'cnn',
        'lr': 0.002,
        'batch_size': 256,
        'epochs': 100,
        'weight_decay': 1e-4,
        'scheduler': 'onecycle',
        'early_stopping_patience': 12,  # More aggressive
    },
}


def select_device(preference='auto'):
    """Select compute device."""
    if preference == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    else:
        device = preference
    
    if device == 'cuda' and not torch.cuda.is_available():
        print("Warning: CUDA not available, falling back to CPU")
        device = 'cpu'
    
    return device


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Advanced neural network training')
    parser.add_argument('--config', type=str, required=True,
                       choices=list(CONFIGS.keys()),
                       help='Training configuration')
    parser.add_argument('--device', type=str, default='auto',
                       choices=['auto', 'cuda', 'cpu'],
                       help='Compute device')
    parser.add_argument('--data-path', type=str, default=str(DEFAULT_DATASET_PATH),
                       help='Path to dataset')
    parser.add_argument('--patience', type=int, default=None,
                       help='Override early stopping patience (default: use config value)')
    
    args = parser.parse_args()
    
    # Get configuration
    config = CONFIGS[args.config].copy()
    
    # Override patience if specified
    if args.patience is not None:
        config['early_stopping_patience'] = args.patience
        print(f"⚠️  Overriding early stopping patience: {args.patience} epochs")
    
    # Create run directory
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    run_name = f"{args.config}_{timestamp}"
    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logger
    logger = setup_logger(run_dir, args.config)
    
    print("=" * 70)
    print("CSI LOCALIZATION - ADVANCED NEURAL NETWORK TRAINING")
    print("=" * 70)
    print(f"Configuration: {args.config}")
    print(f"Model: {config['model'].upper()}")
    print(f"Dataset: {args.data_path}")
    print(f"Run directory: {run_dir}")
    
    logger.info("=" * 70)
    logger.info("CSI LOCALIZATION - ADVANCED NEURAL NETWORK TRAINING")
    logger.info("=" * 70)
    logger.info(f"Configuration: {args.config}")
    logger.info(f"Model: {config['model'].upper()}")
    logger.info(f"Dataset: {args.data_path}")
    logger.info(f"Run directory: {run_dir}")
    
    # Save configuration
    config_path = run_dir / 'config.json'
    with open(config_path, 'w') as f:
        json.dump({
            'config_name': args.config,
            'model': config['model'],
            'device': args.device,
            'dataset_path': args.data_path,
            'training_config': config,
            'timestamp': timestamp
        }, f, indent=2)
    logger.info(f"Configuration saved to: {config_path}")
    
    # Load and preprocess data
    print("\nLoading and preprocessing dataset...")
    logger.info("Loading and preprocessing dataset...")
    X_train, y_train, X_val, y_val, preprocessor = \
        preprocess_dataset(args.data_path)
    
    print(f"Train samples: {len(X_train)}")
    print(f"Val samples: {len(X_val)}")
    print(f"Features: {X_train.shape[1]}")
    
    logger.info(f"Train samples: {len(X_train)}")
    logger.info(f"Val samples: {len(X_val)}")
    logger.info(f"Features: {X_train.shape[1]}")
    
    # Create datasets and loaders
    train_dataset = CSIDataset(X_train, y_train, config['model'])
    val_dataset = CSIDataset(X_val, y_val, config['model'])
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=config['batch_size'], 
        shuffle=True,
        num_workers=0  # Windows compatibility
    )
    val_loader = DataLoader(
        val_dataset, 
        batch_size=config['batch_size'], 
        shuffle=False,
        num_workers=0
    )
    
    # Create model
    print(f"\nCreating {config['model'].upper()} model...")
    logger.info(f"Creating {config['model'].upper()} model...")
    if config['model'] == 'mlp':
        model = create_model(config['model'], input_size=X_train.shape[1])
    else:
        model = create_model(config['model'])
    
    # Select device
    device = select_device(args.device)
    
    # Train
    history, best_model_state = train_model(model, train_loader, val_loader, config, device, logger, run_dir)
    
    # Load best model for final evaluation
    model.load_state_dict(best_model_state)
    model.eval()
    
    # Final evaluation
    print("\n" + "=" * 70)
    print("FINAL EVALUATION")
    print("=" * 70)
    logger.info("=" * 70)
    logger.info("FINAL EVALUATION")
    logger.info("=" * 70)
    
    criterion = nn.MSELoss()
    final_metrics = validate(model, val_loader, criterion, device)
    
    print(f"Validation MAE: {final_metrics['position_mae']:.2f} m")
    print(f"Validation R²: {final_metrics['r2']:.4f}")
    print(f"Validation Loss: {final_metrics['loss']:.4f}")
    
    logger.info(f"Validation MAE: {final_metrics['position_mae']:.2f} m")
    logger.info(f"Validation R²: {final_metrics['r2']:.4f}")
    logger.info(f"Validation Loss: {final_metrics['loss']:.4f}")
    
    # Save model
    model_path = run_dir / f'{config["model"]}_model.pth'
    torch.save(best_model_state, model_path)
    print(f"\nModel saved to: {model_path}")
    logger.info(f"Model saved to: {model_path}")
    
    # Save complete results
    results = {
        'config': args.config,
        'model_type': config['model'],
        'run_name': run_name,
        'timestamp': timestamp,
        'final_metrics': {
            'val_mae': float(final_metrics['position_mae']),
            'val_r2': float(final_metrics['r2']),
            'val_loss': float(final_metrics['loss']),
        },
        'best_metrics': {
            'best_r2': float(max(history['val_r2'])),
            'best_mae': float(min(history['val_mae'])),
            'best_epoch': int(np.argmax(history['val_r2']) + 1),
        },
        'training_summary': {
            'total_epochs': len(history['train_loss']),
            'total_time_minutes': sum(history['epoch_times']) / 60,
            'avg_epoch_time': np.mean(history['epoch_times']),
        },
        'training_config': config,
        'dataset_info': {
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'n_features': X_train.shape[1],
        },
        'history': {k: [float(v) for v in vals] for k, vals in history.items()},
    }
    
    results_path = run_dir / 'results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {results_path}")
    logger.info(f"Results saved to: {results_path}")
    
    # Create summary file
    summary_path = run_dir / 'SUMMARY.txt'
    with open(summary_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("TRAINING RUN SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Configuration: {args.config}\n")
        f.write(f"Model: {config['model'].upper()}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Run Directory: {run_dir}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("TRAINING CONFIGURATION\n")
        f.write("=" * 70 + "\n")
        f.write(f"Learning Rate: {config['lr']}\n")
        f.write(f"Batch Size: {config['batch_size']}\n")
        f.write(f"Scheduler: {config['scheduler']}\n")
        f.write(f"Weight Decay: {config['weight_decay']}\n")
        f.write(f"Max Epochs: {config['epochs']}\n")
        f.write(f"Early Stopping Patience: {config['early_stopping_patience']}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("DATASET INFO\n")
        f.write("=" * 70 + "\n")
        f.write(f"Training Samples: {len(X_train):,}\n")
        f.write(f"Validation Samples: {len(X_val):,}\n")
        f.write(f"Features: {X_train.shape[1]}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("TRAINING RESULTS\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total Epochs: {len(history['train_loss'])}\n")
        f.write(f"Total Training Time: {sum(history['epoch_times'])/60:.2f} minutes\n")
        f.write(f"Average Epoch Time: {np.mean(history['epoch_times']):.2f} seconds\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("BEST MODEL METRICS\n")
        f.write("=" * 70 + "\n")
        f.write(f"Best Epoch: {int(np.argmax(history['val_r2']) + 1)}\n")
        f.write(f"Best Validation R²: {max(history['val_r2']):.4f}\n")
        f.write(f"Best Validation MAE: {min(history['val_mae']):.2f} m\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("FINAL EVALUATION\n")
        f.write("=" * 70 + "\n")
        f.write(f"Final Validation R²: {final_metrics['r2']:.4f}\n")
        f.write(f"Final Validation MAE: {final_metrics['position_mae']:.2f} m\n")
        f.write(f"Final Validation Loss: {final_metrics['loss']:.4f}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("OUTPUT FILES\n")
        f.write("=" * 70 + "\n")
        f.write(f"- Training log: training.log\n")
        f.write(f"- Epoch metrics: epoch_metrics.csv\n")
        f.write(f"- Best model: {config['model']}_model.pth\n")
        f.write(f"- Best checkpoint: best_model_checkpoint.pth\n")
        f.write(f"- Full results: results.json\n")
        f.write(f"- Configuration: config.json\n")
    
    print(f"Summary saved to: {summary_path}")
    logger.info(f"Summary saved to: {summary_path}")
    
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE!")
    print("=" * 70)
    print(f"\n📁 All outputs saved to: {run_dir}")
    print(f"\n📊 Key Results:")
    print(f"   - Best R²: {max(history['val_r2']):.4f}")
    print(f"   - Best MAE: {min(history['val_mae']):.2f} m")
    print(f"   - Training time: {sum(history['epoch_times'])/60:.1f} minutes")
    print(f"\n📄 Files created:")
    print(f"   - training.log (full training log)")
    print(f"   - epoch_metrics.csv (per-epoch metrics)")
    print(f"   - {config['model']}_model.pth (best model)")
    print(f"   - results.json (complete results)")
    print(f"   - SUMMARY.txt (human-readable summary)")
    print("=" * 70 + "\n")
    
    logger.info("=" * 70)
    logger.info("TRAINING COMPLETE!")
    logger.info("=" * 70)


if __name__ == '__main__':
    main()
