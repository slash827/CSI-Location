"""
Debug script with simple CNN on 10% of data.

Test if model can learn at all with:
1. Simple architecture (fewer parameters)
2. Small dataset (10% of data for fast iteration)
3. Extensive diagnostics
"""

import sys
from pathlib import Path

# Add ml_training to path
ml_training_path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ml_training_path))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, Subset
import numpy as np
from sklearn.preprocessing import StandardScaler
from config import DEFAULT_DATASET_PATH
from data_loader import CSIDataLoader
import matplotlib.pyplot as plt

class SimpleCNN(nn.Module):
    """Very simple CNN for debugging."""
    def __init__(self):
        super(SimpleCNN, self).__init__()
        # Input: [batch, 3, 4096]
        self.conv1 = nn.Conv1d(3, 16, kernel_size=5, padding=2)
        self.pool = nn.MaxPool1d(4)  # [batch, 16, 1024]
        self.conv2 = nn.Conv1d(16, 32, kernel_size=5, padding=2)
        # After pool: [batch, 32, 256]
        
        self.fc1 = nn.Linear(32 * 256, 128)
        self.fc2 = nn.Linear(128, 2)
        
        # Initialize output layer properly
        nn.init.constant_(self.fc2.bias, 50.0)  # Mean position
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

def check_gradients(model):
    """Check if gradients are flowing."""
    total_norm = 0
    param_count = 0
    for name, p in model.named_parameters():
        if p.grad is not None:
            param_norm = p.grad.data.norm(2)
            total_norm += param_norm.item() ** 2
            param_count += 1
    total_norm = total_norm ** 0.5
    return total_norm, param_count

def diagnose_batch(model, X_batch, y_batch, criterion):
    """Diagnose a single batch."""
    print("\n" + "=" * 70)
    print("BATCH DIAGNOSTICS")
    print("=" * 70)
    
    print(f"\nInput:")
    print(f"  Shape: {X_batch.shape}")
    print(f"  Mean: {X_batch.mean():.6f}, Std: {X_batch.std():.6f}")
    print(f"  Range: [{X_batch.min():.2f}, {X_batch.max():.2f}]")
    print(f"  Has NaN: {torch.isnan(X_batch).any()}")
    print(f"  Has Inf: {torch.isinf(X_batch).any()}")
    
    print(f"\nTargets:")
    print(f"  Shape: {y_batch.shape}")
    print(f"  Mean: {y_batch.mean(dim=0)}")
    print(f"  Std: {y_batch.std(dim=0)}")
    print(f"  Range: [{y_batch.min():.2f}, {y_batch.max():.2f}]")
    
    # Forward pass
    predictions = model(X_batch)
    loss = criterion(predictions, y_batch)
    
    print(f"\nPredictions:")
    print(f"  Shape: {predictions.shape}")
    print(f"  Mean: {predictions.mean(dim=0).detach().cpu()}")
    print(f"  Std: {predictions.std(dim=0).detach().cpu()}")
    print(f"  Range: [{predictions.min():.2f}, {predictions.max():.2f}]")
    print(f"  Has NaN: {torch.isnan(predictions).any()}")
    print(f"  Has Inf: {torch.isinf(predictions).any()}")
    
    print(f"\nLoss:")
    print(f"  Value: {loss.item():.2f}")
    print(f"  Has NaN: {torch.isnan(loss).any()}")
    print(f"  Has Inf: {torch.isinf(loss).any()}")
    
    # Backward pass
    loss.backward()
    grad_norm, param_count = check_gradients(model)
    
    print(f"\nGradients:")
    print(f"  Total norm: {grad_norm:.6f}")
    print(f"  Parameters with gradients: {param_count}")
    
    # Check specific layers
    print(f"\nLayer-wise gradient norms:")
    for name, p in model.named_parameters():
        if p.grad is not None:
            print(f"  {name:20s}: {p.grad.norm():.6f}")
    
    print("=" * 70)

def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print("=" * 70)
    print("SIMPLE CNN DEBUG - 10% DATA")
    print("=" * 70)
    print(f"\nDevice: {device}\n")
    
    # Load data
    print("Loading data...")
    loader = CSIDataLoader(DEFAULT_DATASET_PATH)
    X_train, y_train, X_val, y_val = loader.load_all()
    
    # Use only 10% of data
    n_train = int(0.1 * len(X_train))
    n_val = int(0.1 * len(X_val))
    
    indices_train = np.random.choice(len(X_train), n_train, replace=False)
    indices_val = np.random.choice(len(X_val), n_val, replace=False)
    
    X_train = X_train[indices_train]
    y_train = y_train[indices_train]
    X_val = X_val[indices_val]
    y_val = y_val[indices_val]
    
    print(f"\n✓ Using 10% of data:")
    print(f"  Train: {X_train.shape[0]} samples")
    print(f"  Val: {X_val.shape[0]} samples")
    
    # Independent normalization
    print("\n⚠️  Using independent normalization")
    scaler_train = StandardScaler()
    scaler_val = StandardScaler()
    
    X_train_norm = scaler_train.fit_transform(X_train)
    X_val_norm = scaler_val.fit_transform(X_val)
    
    print(f"  Train: mean={X_train_norm.mean():.6f}, std={X_train_norm.std():.6f}")
    print(f"  Val:   mean={X_val_norm.mean():.6f}, std={X_val_norm.std():.6f}")
    
    # Check target statistics
    print(f"\n✓ Target statistics:")
    print(f"  Train: mean={y_train.mean(axis=0)}, std={y_train.std(axis=0)}")
    print(f"  Val:   mean={y_val.mean(axis=0)}, std={y_val.std(axis=0)}")
    
    # Create datasets
    train_dataset = CSIDataset(X_train_norm, y_train)
    val_dataset = CSIDataset(X_val_norm, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    # Create model
    model = SimpleCNN().to(device)
    print(f"\n✓ Simple CNN created: {sum(p.numel() for p in model.parameters())} parameters")
    
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Diagnose first batch
    print("\n" + "=" * 70)
    print("DIAGNOSING FIRST BATCH")
    print("=" * 70)
    
    model.train()
    X_batch, y_batch = next(iter(train_loader))
    X_batch = X_batch.to(device)
    y_batch = y_batch.to(device)
    
    diagnose_batch(model, X_batch, y_batch, criterion)
    
    # Train for a few epochs
    print("\n" + "=" * 70)
    print("TRAINING (10 EPOCHS)")
    print("=" * 70 + "\n")
    
    history = {'train_loss': [], 'val_loss': [], 'val_mae': [], 'val_r2': []}
    
    for epoch in range(10):
        # Train
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            
            optimizer.zero_grad()
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)
            loss.backward()
            
            # Check for NaN
            if torch.isnan(loss):
                print(f"\nNaN loss detected at epoch {epoch+1}!")
                return
            
            optimizer.step()
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        
        # Validate
        model.eval()
        val_loss = 0
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)
                
                predictions = model(X_batch)
                loss = criterion(predictions, y_batch)
                
                val_loss += loss.item()
                all_preds.append(predictions.cpu().numpy())
                all_targets.append(y_batch.cpu().numpy())
        
        val_loss /= len(val_loader)
        all_preds = np.vstack(all_preds)
        all_targets = np.vstack(all_targets)
        
        # Calculate metrics
        mae = np.mean(np.linalg.norm(all_preds - all_targets, axis=1))
        ss_res = np.sum((all_targets - all_preds) ** 2)
        ss_tot = np.sum((all_targets - all_targets.mean(axis=0)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_mae'].append(mae)
        history['val_r2'].append(r2)
        
        print(f"Epoch {epoch+1}/10: "
              f"Train={train_loss:.2f}, Val={val_loss:.2f}, "
              f"MAE={mae:.2f}m, R²={r2:.3f}")
    
    # Plot results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    
    # Loss curves
    axes[0, 0].plot(history['train_loss'], label='Train')
    axes[0, 0].plot(history['val_loss'], label='Val')
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].set_title('Loss Curves')
    axes[0, 0].legend()
    axes[0, 0].grid(True)
    
    # MAE
    axes[0, 1].plot(history['val_mae'])
    axes[0, 1].set_xlabel('Epoch')
    axes[0, 1].set_ylabel('MAE (m)')
    axes[0, 1].set_title('Validation MAE')
    axes[0, 1].grid(True)
    
    # R²
    axes[1, 0].plot(history['val_r2'])
    axes[1, 0].axhline(y=0, color='r', linestyle='--', label='R²=0')
    axes[1, 0].set_xlabel('Epoch')
    axes[1, 0].set_ylabel('R²')
    axes[1, 0].set_title('Validation R²')
    axes[1, 0].legend()
    axes[1, 0].grid(True)
    
    # Predictions scatter
    model.eval()
    with torch.no_grad():
        sample_idx = np.random.choice(len(val_dataset), min(500, len(val_dataset)), replace=False)
        sample_x = torch.stack([val_dataset[i][0] for i in sample_idx]).to(device)
        sample_y = torch.stack([val_dataset[i][1] for i in sample_idx]).cpu().numpy()
        sample_pred = model(sample_x).cpu().numpy()
    
    axes[1, 1].scatter(sample_y[:, 0], sample_pred[:, 0], alpha=0.5, s=10, label='X')
    axes[1, 1].scatter(sample_y[:, 1], sample_pred[:, 1], alpha=0.5, s=10, label='Y')
    axes[1, 1].plot([10, 90], [10, 90], 'r--', label='Perfect')
    axes[1, 1].set_xlabel('True Position')
    axes[1, 1].set_ylabel('Predicted Position')
    axes[1, 1].set_title('Predictions vs Truth')
    axes[1, 1].legend()
    axes[1, 1].grid(True)
    
    plt.tight_layout()
    plt.savefig('debug_simple_cnn.png', dpi=150)
    print(f"\n✓ Saved plot to: debug_simple_cnn.png")
    
    # Final diagnostics
    print(f"\nFinal Results:")
    print(f"  Best R²: {max(history['val_r2']):.3f}")
    print(f"  Best MAE: {min(history['val_mae']):.2f}m")
    print(f"  Final predictions range: [{sample_pred.min():.1f}, {sample_pred.max():.1f}]")
    print(f"  Target range: [{sample_y.min():.1f}, {sample_y.max():.1f}]")
    
    if max(history['val_r2']) < 0:
        print("\n⚠️  WARNING: R² is still negative!")
        print("   Possible issues:")
        print("   1. Input features have no predictive power")
        print("   2. Model architecture is inappropriate for the data")
        print("   3. Learning rate is too high/low")
        print("   4. Data preprocessing removes important information")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
