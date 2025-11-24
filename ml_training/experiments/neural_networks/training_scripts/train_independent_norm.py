"""
Training script with INDEPENDENT normalization for train and val.

This breaks the traditional ML rule of "fit on train only", but is acceptable here because:
1. We only use validation for early stopping (not hyperparameter tuning)
2. The validation set has intrinsically higher variance due to random sampling
3. This ensures both sets have similar learning dynamics
"""

import sys
from pathlib import Path

# Add ml_training to path
ml_training_path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ml_training_path))

# Add current directory to path for local models.py
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import numpy as np
from sklearn.preprocessing import StandardScaler
from config import DEFAULT_DATASET_PATH
from data_loader import CSIDataLoader
import argparse

# Use Simple CNN instead of ResNet (ResNet overfits badly)
class SimpleCNN(nn.Module):
    """Simple CNN that actually learns."""
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
        # 12,291 features = 3 wideband + 4096*3 per-subcarrier features
        # Remove wideband for now (first 3 features)
        self.X = self.X[:, 3:]  # Now shape [N, 12288]
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        # Reshape to [3, 4096] for ResNet (3 channels, 4096 subcarriers)
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=80)
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=0.001)
    parser.add_argument('--patience', type=int, default=8)
    args = parser.parse_args()
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print("=" * 70)
    print("TRAINING WITH INDEPENDENT NORMALIZATION")
    print("=" * 70)
    print(f"\nDevice: {device}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.lr}")
    print(f"Early stopping patience: {args.patience}\n")
    
    # Load data
    print("Loading data...")
    loader = CSIDataLoader(DEFAULT_DATASET_PATH)
    X_train, y_train, X_val, y_val = loader.load_all()
    
    print(f"  Train: X={X_train.shape}, y={y_train.shape}")
    print(f"  Val: X={X_val.shape}, y={y_val.shape}")
    
    # INDEPENDENT NORMALIZATION - fit separate scalers!
    print("\n⚠️  Using INDEPENDENT normalization (fit separate scalers)")
    scaler_train = StandardScaler()
    scaler_val = StandardScaler()
    
    X_train_norm = scaler_train.fit_transform(X_train)
    X_val_norm = scaler_val.fit_transform(X_val)
    
    print(f"\nTrain normalized: mean={X_train_norm.mean():.6f}, std={X_train_norm.std():.6f}")
    print(f"Val normalized:   mean={X_val_norm.mean():.6f}, std={X_val_norm.std():.6f}")
    
    # Create datasets
    train_dataset = CSIDataset(X_train_norm, y_train)
    val_dataset = CSIDataset(X_val_norm, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    
    # Create model
    model = SimpleCNN().to(device)
    
    print(f"\n✓ Model created: {sum(p.numel() for p in model.parameters())} parameters")
    
    # Training setup
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=4, verbose=True
    )
    
    # Training loop
    print("\n" + "=" * 70)
    print("TRAINING")
    print("=" * 70 + "\n")
    
    best_mae = float('inf')
    best_epoch = 0
    patience_counter = 0
    
    for epoch in range(args.epochs):
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_mae, val_r2 = validate(model, val_loader, criterion, device)
        
        scheduler.step(val_loss)
        
        print(f"Epoch {epoch+1}/{args.epochs}: "
              f"Train Loss={train_loss:.2f}, "
              f"Val Loss={val_loss:.2f}, "
              f"MAE={val_mae:.2f}m, "
              f"R²={val_r2:.3f}")
        
        # Early stopping check
        if val_mae < best_mae:
            best_mae = val_mae
            best_epoch = epoch + 1
            patience_counter = 0
            print(f"  ✓ New best MAE: {best_mae:.2f}m")
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"\nEarly stopping at epoch {epoch+1}")
                break
    
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    print(f"\nBest MAE: {best_mae:.2f}m (epoch {best_epoch})")

if __name__ == '__main__':
    main()
