"""
Improved CNN training with timing and enhanced architecture.

Improvements over SimpleCNN:
1. Deeper network (3 conv layers instead of 2)
2. Batch normalization for better training stability
3. Dropout for regularization
4. Epoch timing
5. More detailed logging
"""

import sys
from pathlib import Path
import time

# Add ml_training to path
ml_training_path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ml_training_path))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import numpy as np
from sklearn.preprocessing import StandardScaler
from config import DEFAULT_DATASET_PATH
from data_loader import CSIDataLoader
import argparse

class ImprovedCNN(nn.Module):
    """
    Improved CNN with BatchNorm and Dropout.
    
    Architecture:
    - 3 conv blocks (instead of 2)
    - Batch normalization after each conv
    - Dropout for regularization
    - Larger hidden layer
    """
    def __init__(self, dropout=0.3):
        super(ImprovedCNN, self).__init__()
        
        # Conv Block 1: [batch, 3, 4096] -> [batch, 32, 1024]
        self.conv1 = nn.Conv1d(3, 32, kernel_size=7, padding=3)
        self.bn1 = nn.BatchNorm1d(32)
        self.pool1 = nn.MaxPool1d(4)
        
        # Conv Block 2: [batch, 32, 1024] -> [batch, 64, 256]
        self.conv2 = nn.Conv1d(32, 64, kernel_size=5, padding=2)
        self.bn2 = nn.BatchNorm1d(64)
        self.pool2 = nn.MaxPool1d(4)
        
        # Conv Block 3: [batch, 64, 256] -> [batch, 128, 64]
        self.conv3 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm1d(128)
        self.pool3 = nn.MaxPool1d(4)
        
        # Fully connected layers: [batch, 128*64=8192] -> [batch, 256] -> [batch, 2]
        self.fc1 = nn.Linear(128 * 64, 256)
        self.dropout1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(256, 128)
        self.dropout2 = nn.Dropout(dropout)
        self.fc3 = nn.Linear(128, 2)
        
        # Initialize output layer for position range [10, 90]
        nn.init.constant_(self.fc3.bias, 50.0)
        nn.init.normal_(self.fc3.weight, std=0.01)
        
    def forward(self, x):
        # Conv Block 1
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.pool1(x)
        
        # Conv Block 2
        x = torch.relu(self.bn2(self.conv2(x)))
        x = self.pool2(x)
        
        # Conv Block 3
        x = torch.relu(self.bn3(self.conv3(x)))
        x = self.pool3(x)
        
        # Flatten
        x = x.view(x.size(0), -1)
        
        # Fully connected
        x = torch.relu(self.fc1(x))
        x = self.dropout1(x)
        x = torch.relu(self.fc2(x))
        x = self.dropout2(x)
        x = self.fc3(x)
        
        return x

class SimpleCNN(nn.Module):
    """Original simple CNN (for comparison)."""
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv1d(3, 16, kernel_size=5, padding=2)
        self.pool = nn.MaxPool1d(4)
        self.conv2 = nn.Conv1d(16, 32, kernel_size=5, padding=2)
        self.fc1 = nn.Linear(32 * 256, 128)
        self.fc2 = nn.Linear(128, 2)
        nn.init.constant_(self.fc2.bias, 50.0)
        nn.init.normal_(self.fc2.weight, std=0.01)
    
    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = self.pool(x)
        x = torch.relu(self.conv2(x))
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CSIDataset(Dataset):
    """Dataset for CSI features."""
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
        # Remove wideband features (first 3)
        self.X = self.X[:, 3:]  # Now [N, 12288]
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        x = self.X[idx].view(3, 4096)
        return x, self.y[idx]

def train_epoch(model, loader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    
    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)
        
        optimizer.zero_grad()
        predictions = model(X_batch)
        loss = criterion(predictions, y_batch)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    return total_loss / len(loader)

@torch.no_grad()
def validate(model, loader, criterion, device):
    """Validate model."""
    model.eval()
    total_loss = 0
    all_preds = []
    all_targets = []
    
    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)
        
        predictions = model(X_batch)
        loss = criterion(predictions, y_batch)
        
        total_loss += loss.item()
        all_preds.append(predictions.cpu().numpy())
        all_targets.append(y_batch.cpu().numpy())
    
    all_preds = np.vstack(all_preds)
    all_targets = np.vstack(all_targets)
    
    # Calculate MAE
    mae = np.mean(np.linalg.norm(all_preds - all_targets, axis=1))
    
    # Calculate R²
    ss_res = np.sum((all_targets - all_preds) ** 2)
    ss_tot = np.sum((all_targets - all_targets.mean(axis=0)) ** 2)
    r2 = 1 - (ss_res / ss_tot)
    
    return total_loss / len(loader), mae, r2

def format_time(seconds):
    """Format time in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"

def main():
    parser = argparse.ArgumentParser(description='Improved CNN training')
    parser.add_argument('--model', type=str, default='improved', choices=['simple', 'improved'],
                       help='Model architecture (default: improved)')
    parser.add_argument('--epochs', type=int, default=80,
                       help='Number of epochs (default: 80)')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Batch size (default: 32)')
    parser.add_argument('--lr', type=float, default=0.001,
                       help='Learning rate (default: 0.001)')
    parser.add_argument('--patience', type=int, default=15,
                       help='Early stopping patience (default: 15)')
    parser.add_argument('--dropout', type=float, default=0.3,
                       help='Dropout rate for improved model (default: 0.3)')
    args = parser.parse_args()
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print("=" * 70)
    print(f"IMPROVED CNN TRAINING - {args.model.upper()}")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Model: {args.model}")
    print(f"  Device: {device}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.lr}")
    print(f"  Early stopping patience: {args.patience}")
    if args.model == 'improved':
        print(f"  Dropout: {args.dropout}")
    print()
    
    # Load data
    print("Loading data...")
    start_load = time.time()
    loader = CSIDataLoader(DEFAULT_DATASET_PATH)
    X_train, y_train, X_val, y_val = loader.load_all()
    load_time = time.time() - start_load
    
    print(f"  Train: X={X_train.shape}, y={y_train.shape}")
    print(f"  Val: X={X_val.shape}, y={y_val.shape}")
    print(f"  Load time: {format_time(load_time)}")
    
    # Independent normalization
    print("\n⚠️  Using independent normalization")
    scaler_train = StandardScaler()
    scaler_val = StandardScaler()
    
    X_train_norm = scaler_train.fit_transform(X_train)
    X_val_norm = scaler_val.fit_transform(X_val)
    
    print(f"  Train: mean={X_train_norm.mean():.6f}, std={X_train_norm.std():.6f}")
    print(f"  Val:   mean={X_val_norm.mean():.6f}, std={X_val_norm.std():.6f}")
    
    # Create datasets
    train_dataset = CSIDataset(X_train_norm, y_train)
    val_dataset = CSIDataset(X_val_norm, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    
    # Create model
    if args.model == 'simple':
        model = SimpleCNN().to(device)
    else:
        model = ImprovedCNN(dropout=args.dropout).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"\n✓ Model created: {n_params:,} parameters")
    
    # Training setup
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=4
    )
    
    # Training loop
    print("\n" + "=" * 70)
    print("TRAINING")
    print("=" * 70)
    print()
    
    best_mae = float('inf')
    best_epoch = 0
    best_model_state = None
    patience_counter = 0
    total_train_time = 0
    
    for epoch in range(args.epochs):
        epoch_start = time.time()
        
        # Train
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        
        # Validate
        val_loss, val_mae, val_r2 = validate(model, val_loader, criterion, device)
        
        # Update scheduler
        scheduler.step(val_loss)
        
        epoch_time = time.time() - epoch_start
        total_train_time += epoch_time
        
        # Get current learning rate
        current_lr = optimizer.param_groups[0]['lr']
        
        # Print progress with timing
        print(f"Epoch {epoch+1:3d}/{args.epochs}: "
              f"Train={train_loss:6.2f}, Val={val_loss:6.2f}, "
              f"MAE={val_mae:5.2f}m, R²={val_r2:5.3f}, "
              f"LR={current_lr:.1e}, Time={format_time(epoch_time)}")
        
        # Early stopping check
        if val_mae < best_mae:
            best_mae = val_mae
            best_epoch = epoch + 1
            best_model_state = model.state_dict().copy()
            patience_counter = 0
            print(f"  ✓ New best MAE: {best_mae:.2f}m")
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"\nEarly stopping at epoch {epoch+1}")
                break
    
    # Load best model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    # Final evaluation
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    print(f"\nBest Performance:")
    print(f"  Epoch: {best_epoch}/{epoch+1}")
    print(f"  MAE: {best_mae:.2f}m")
    print(f"\nTiming:")
    print(f"  Total training time: {format_time(total_train_time)}")
    print(f"  Average epoch time: {format_time(total_train_time / (epoch+1))}")
    print(f"  Data loading time: {format_time(load_time)}")
    
    # Save model
    output_dir = Path(__file__).parent / "saved_models"
    output_dir.mkdir(exist_ok=True)
    model_path = output_dir / f"{args.model}_cnn_best.pth"
    torch.save({
        'model_state_dict': best_model_state,
        'best_mae': best_mae,
        'best_epoch': best_epoch,
        'model_type': args.model,
        'n_parameters': n_params
    }, model_path)
    print(f"\n✓ Saved best model to: {model_path}")
    print("=" * 70)

if __name__ == '__main__':
    main()
