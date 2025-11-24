"""
Quick comparison of Simple CNN vs Improved CNN results.
Run after both models have been trained.
"""

import matplotlib.pyplot as plt
import numpy as np

# Results from training runs
results = {
    'Simple CNN': {
        'mae': 14.48,
        'r2': 0.785,
        'params': 1_051_810,
        'epochs': 26,
        'best_epoch': 11
    },
    'Improved CNN': {
        'mae': None,  # To be filled after training
        'r2': None,
        'params': 2_400_000,  # Estimated
        'epochs': None,
        'best_epoch': None
    }
}

print("=" * 70)
print("CNN MODEL COMPARISON")
print("=" * 70)

for model_name, stats in results.items():
    print(f"\n{model_name}:")
    print(f"  Parameters: {stats['params']:,}")
    if stats['mae'] is not None:
        print(f"  Best MAE: {stats['mae']:.2f}m")
        print(f"  Best R²: {stats['r2']:.3f}")
        print(f"  Total epochs: {stats['epochs']}")
        print(f"  Best epoch: {stats['best_epoch']}")
    else:
        print("  Status: Training in progress...")

print("\n" + "=" * 70)
print("\nKey Improvements in Improved CNN:")
print("  ✓ 3 conv layers (vs 2)")
print("  ✓ Batch Normalization")
print("  ✓ Dropout regularization")
print("  ✓ Deeper FC layers (256→128 vs 128)")
print("  ✓ More channels (32→64→128 vs 16→32)")
print("=" * 70)

# Visualization placeholder
if results['Improved CNN']['mae'] is not None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    models = ['Simple CNN', 'Improved CNN']
    maes = [results[m]['mae'] for m in models]
    r2s = [results[m]['r2'] for m in models]
    params = [results[m]['params'] / 1e6 for m in models]
    
    # MAE comparison
    axes[0].bar(models, maes, color=['#3498db', '#e74c3c'])
    axes[0].set_ylabel('MAE (meters)')
    axes[0].set_title('Location Error (Lower is Better)')
    axes[0].grid(axis='y', alpha=0.3)
    for i, v in enumerate(maes):
        axes[0].text(i, v + 0.3, f'{v:.2f}m', ha='center', fontweight='bold')
    
    # R² comparison
    axes[1].bar(models, r2s, color=['#3498db', '#e74c3c'])
    axes[1].set_ylabel('R² Score')
    axes[1].set_title('Model Fit (Higher is Better)')
    axes[1].set_ylim([0.75, 0.85])
    axes[1].grid(axis='y', alpha=0.3)
    for i, v in enumerate(r2s):
        axes[1].text(i, v + 0.002, f'{v:.3f}', ha='center', fontweight='bold')
    
    # Parameters comparison
    axes[2].bar(models, params, color=['#3498db', '#e74c3c'])
    axes[2].set_ylabel('Parameters (millions)')
    axes[2].set_title('Model Complexity')
    axes[2].grid(axis='y', alpha=0.3)
    for i, v in enumerate(params):
        axes[2].text(i, v + 0.05, f'{v:.2f}M', ha='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('cnn_comparison.png', dpi=150, bbox_inches='tight')
    print("\n✓ Saved comparison plot to: cnn_comparison.png")
else:
    print("\n⚠️  Improved CNN training not complete yet")
    print("   Run this script again after training finishes")
