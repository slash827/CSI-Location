# Training Runs Directory

This directory contains all training run outputs. Each run is stored in a separate folder with a timestamp.

## Directory Structure

```
runs/
├── <config_name>_<timestamp>/
│   ├── training.log              # Full training log with timestamps
│   ├── epoch_metrics.csv         # Per-epoch metrics in CSV format
│   ├── config.json               # Training configuration
│   ├── results.json              # Complete results including history
│   ├── SUMMARY.txt               # Human-readable summary
│   ├── <model>_model.pth         # Best model weights
│   └── best_model_checkpoint.pth # Full checkpoint with optimizer state
```

## File Descriptions

### `training.log`
Full training log with timestamps. Contains:
- Configuration details
- Per-epoch progress (loss, MAE, R², LR)
- Best model updates
- Early stopping notifications
- Final evaluation results

Example:
```
2025-11-14 10:30:15 - Epoch 1/100 - Train Loss: 0.0234, Val Loss: 0.0198, Val MAE: 14.23m, Val R²: 0.7845, LR: 0.001000, Time: 12.3s
2025-11-14 10:30:28 - New best model - R²: 0.7845, MAE: 14.23m
```

### `epoch_metrics.csv`
Per-epoch metrics in CSV format for easy analysis and plotting.

Columns:
- `epoch`: Epoch number (1-indexed)
- `train_loss`: Training loss (MSE)
- `val_loss`: Validation loss (MSE)
- `val_mae`: Validation MAE (meters)
- `val_r2`: Validation R² score
- `lr`: Learning rate
- `epoch_time`: Epoch duration (seconds)
- `best`: 1 if this is the best model so far, 0 otherwise

Example:
```csv
epoch,train_loss,val_loss,val_mae,val_r2,lr,epoch_time,best
1,0.023456,0.019876,14.2345,0.784512,0.00100000,12.34,1
2,0.018765,0.017654,13.8765,0.798765,0.00099500,11.89,1
3,0.016543,0.016234,13.2345,0.812345,0.00099000,12.01,1
```

### `config.json`
Complete training configuration including:
- Model architecture
- Hyperparameters (LR, batch size, etc.)
- Scheduler settings
- Dataset path
- Timestamp

### `results.json`
Complete training results including:
- Final evaluation metrics
- Best metrics across all epochs
- Training summary (total time, epochs, etc.)
- Full training history (all epochs)
- Dataset information

### `SUMMARY.txt`
Human-readable summary of the training run. Contains:
- Configuration overview
- Dataset statistics
- Training results
- Best model metrics
- Final evaluation
- List of output files

### `<model>_model.pth`
Best model weights (state dict only). Use with:
```python
model = create_model('resnet')
model.load_state_dict(torch.load('resnet_model.pth'))
```

### `best_model_checkpoint.pth`
Full checkpoint including:
- Model state dict
- Optimizer state dict
- Epoch number
- Best metrics
- Configuration

Use for resuming training or detailed analysis.

## Usage Examples

### 1. View Training Progress
```bash
# Real-time monitoring
tail -f runs/<run_name>/training.log

# View epoch metrics
cat runs/<run_name>/epoch_metrics.csv

# Quick summary
cat runs/<run_name>/SUMMARY.txt
```

### 2. Analyze Results in Python
```python
import json
import pandas as pd

# Load epoch metrics
df = pd.read_csv('runs/<run_name>/epoch_metrics.csv')

# Plot training curves
import matplotlib.pyplot as plt
plt.figure(figsize=(12, 4))

plt.subplot(1, 3, 1)
plt.plot(df['epoch'], df['train_loss'], label='Train')
plt.plot(df['epoch'], df['val_loss'], label='Val')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.subplot(1, 3, 2)
plt.plot(df['epoch'], df['val_mae'])
plt.xlabel('Epoch')
plt.ylabel('MAE (m)')

plt.subplot(1, 3, 3)
plt.plot(df['epoch'], df['val_r2'])
plt.xlabel('Epoch')
plt.ylabel('R²')

plt.tight_layout()
plt.show()

# Load complete results
with open('runs/<run_name>/results.json', 'r') as f:
    results = json.load(f)
    
print(f"Best R²: {results['best_metrics']['best_r2']:.4f}")
print(f"Best MAE: {results['best_metrics']['best_mae']:.2f} m")
```

### 3. Compare Multiple Runs
```python
import os
import json
import pandas as pd

runs_dir = 'runs/'
all_results = []

for run_name in os.listdir(runs_dir):
    results_file = os.path.join(runs_dir, run_name, 'results.json')
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            data = json.load(f)
            all_results.append({
                'run_name': run_name,
                'config': data['config'],
                'model': data['model_type'],
                'best_r2': data['best_metrics']['best_r2'],
                'best_mae': data['best_metrics']['best_mae'],
                'final_r2': data['final_metrics']['val_r2'],
                'final_mae': data['final_metrics']['val_mae'],
                'total_epochs': data['training_summary']['total_epochs'],
                'training_time': data['training_summary']['total_time_minutes'],
            })

df_results = pd.DataFrame(all_results)
df_results = df_results.sort_values('best_r2', ascending=False)
print(df_results)
```

### 4. Resume Training from Checkpoint
```python
import torch
from models import create_model

# Load checkpoint
checkpoint = torch.load('runs/<run_name>/best_model_checkpoint.pth')

# Create model and load state
model = create_model('resnet')
model.load_state_dict(checkpoint['model_state_dict'])

# Can also resume optimizer state
optimizer = torch.optim.Adam(model.parameters())
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

print(f"Resuming from epoch {checkpoint['epoch']}")
print(f"Best R²: {checkpoint['val_r2']:.4f}")
print(f"Best MAE: {checkpoint['val_mae']:.2f} m")
```

## Monitoring Active Runs

If a training run stops unexpectedly:

1. **Check the log file**: Look for errors or warnings
   ```bash
   tail -50 runs/<run_name>/training.log
   ```

2. **Check epoch metrics**: See where training stopped
   ```bash
   tail -10 runs/<run_name>/epoch_metrics.csv
   ```

3. **Check if model was saved**: Best model is saved after each improvement
   ```bash
   ls -lh runs/<run_name>/*.pth
   ```

4. **Analyze partial results**: Even incomplete runs save epoch-by-epoch data

## Disk Space Management

Each run typically uses:
- Training log: ~50-500 KB
- Epoch metrics CSV: ~10-50 KB
- Model weights: ~2-20 MB (depends on architecture)
- Checkpoint: ~4-40 MB (includes optimizer state)
- Configuration files: <10 KB

Total per run: ~10-100 MB

To clean up old runs:
```bash
# Keep only the best run from each config
python cleanup_old_runs.py --keep-best

# Remove runs older than 30 days
python cleanup_old_runs.py --days 30
```

## Tips

1. **Monitor GPU usage** during training:
   ```bash
   watch -n 1 nvidia-smi
   ```

2. **Compare learning rate schedulers**: Look at the `lr` column in `epoch_metrics.csv`

3. **Identify overfitting**: Compare `train_loss` vs `val_loss` trends

4. **Find best epoch**: Look for `best=1` in `epoch_metrics.csv`

5. **Quick comparison**: Use `SUMMARY.txt` files for quick overview without parsing JSON

---

## Automatic Logging

All training runs automatically create these files. No manual setup required!

Simply run:
```bash
python experiments/neural_networks/train_advanced.py --config resnet_cosine_100
```

And all outputs will be saved to `runs/<config>_<timestamp>/`
