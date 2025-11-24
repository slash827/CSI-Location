"""
Test ResNet vs Simple CNN on same small dataset.
"""

import sys
from pathlib import Path

ml_training_path = Path(__file__).resolve().parents[2]
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(ml_training_path))
sys.path.insert(0, str(current_dir))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import numpy as np
from sklearn.preprocessing import StandardScaler
from config import DEFAULT_DATASET_PATH
from data_loader import CSIDataLoader
import models

ResNetLocalization = models.ResNetLocalization

class CSIDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
        self.X = self.X[:, 3:]  # Remove wideband
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        x = self.X[idx].view(3, 4096)
        return x, self.y[idx]

def test_model(model_class, model_name, train_loader, val_loader, device):
    print(f"\n{'='*70}")
    print(f"TESTING {model_name}")
    print(f"{'='*70}")
    
    model = model_class().to(device)
    print(f"Parameters: {sum(p.numel() for p in model.parameters())}")
    
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Train for 5 epochs
    for epoch in range(5):
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            
            optimizer.zero_grad()
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)
            
            if torch.isnan(loss):
                print(f"  NaN loss at epoch {epoch+1}!")
                return
            
            loss.backward()
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
        
        mae = np.mean(np.linalg.norm(all_preds - all_targets, axis=1))
        ss_res = np.sum((all_targets - all_preds) ** 2)
        ss_tot = np.sum((all_targets - all_targets.mean(axis=0)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        
        print(f"Epoch {epoch+1}/5: Train={train_loss:.2f}, Val={val_loss:.2f}, MAE={mae:.2f}m, R²={r2:.3f}")

def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print("="*70)
    print("COMPARING RESNET VS SIMPLE CNN")
    print("="*70)
    
    # Load 10% of data
    loader = CSIDataLoader(DEFAULT_DATASET_PATH)
    X_train, y_train, X_val, y_val = loader.load_all()
    
    n_train = int(0.1 * len(X_train))
    n_val = int(0.1 * len(X_val))
    
    indices_train = np.random.choice(len(X_train), n_train, replace=False)
    indices_val = np.random.choice(len(X_val), n_val, replace=False)
    
    X_train = X_train[indices_train]
    y_train = y_train[indices_train]
    X_val = X_val[indices_val]
    y_val = y_val[indices_val]
    
    print(f"\nData: {X_train.shape[0]} train, {X_val.shape[0]} val")
    
    # Independent normalization
    scaler_train = StandardScaler()
    scaler_val = StandardScaler()
    
    X_train_norm = scaler_train.fit_transform(X_train)
    X_val_norm = scaler_val.fit_transform(X_val)
    
    # Create datasets
    train_dataset = CSIDataset(X_train_norm, y_train)
    val_dataset = CSIDataset(X_val_norm, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    # Define models
    class SimpleCNN(nn.Module):
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
    
    class ResNetWrapper(nn.Module):
        def __init__(self):
            super(ResNetWrapper, self).__init__()
            self.model = ResNetLocalization(n_subcarriers=1024, n_channels=3)
        
        def forward(self, x):
            return self.model(x)
    
    # Test both models
    test_model(SimpleCNN, "SIMPLE CNN", train_loader, val_loader, device)
    test_model(ResNetWrapper, "RESNET", train_loader, val_loader, device)

if __name__ == '__main__':
    main()
