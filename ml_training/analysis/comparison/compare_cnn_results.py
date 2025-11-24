"""
Compare CNN Results Visualization
Generates bar charts comparing Simple CNN vs Improved CNN performance
"""

import matplotlib.pyplot as plt
import numpy as np

# Results from training
models = ['Simple CNN', 'Improved CNN']
mae_values = [14.48, 11.47]  # meters
r2_values = [0.785, 0.858]
params = [1.05, 2.17]  # millions
epochs = [26, 61]
training_time = [0.7, 12.9]  # minutes

# Create figure with subplots
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
fig.suptitle('CNN Models Comparison - exp11 NLOS Dataset', fontsize=16, fontweight='bold')

# 1. MAE Comparison
ax1 = axes[0, 0]
bars1 = ax1.bar(models, mae_values, color=['#3498db', '#2ecc71'], alpha=0.8, edgecolor='black')
ax1.set_ylabel('Mean Absolute Error (m)', fontsize=12, fontweight='bold')
ax1.set_title('Localization Accuracy', fontsize=13, fontweight='bold')
ax1.grid(axis='y', alpha=0.3)
# Add value labels on bars
for bar, val in zip(bars1, mae_values):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{val:.2f}m',
             ha='center', va='bottom', fontweight='bold', fontsize=11)
# Add improvement annotation
improvement = ((mae_values[0] - mae_values[1]) / mae_values[0]) * 100
ax1.text(0.5, max(mae_values) * 0.7, f'↓ {improvement:.1f}% better', 
         ha='center', fontsize=12, color='green', fontweight='bold',
         bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

# 2. R² Comparison
ax2 = axes[0, 1]
bars2 = ax2.bar(models, r2_values, color=['#3498db', '#2ecc71'], alpha=0.8, edgecolor='black')
ax2.set_ylabel('R² Score', fontsize=12, fontweight='bold')
ax2.set_title('Model Fit Quality', fontsize=13, fontweight='bold')
ax2.set_ylim([0.7, 0.9])
ax2.grid(axis='y', alpha=0.3)
for bar, val in zip(bars2, r2_values):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{val:.3f}',
             ha='center', va='bottom', fontweight='bold', fontsize=11)

# 3. Parameters Comparison
ax3 = axes[0, 2]
bars3 = ax3.bar(models, params, color=['#3498db', '#2ecc71'], alpha=0.8, edgecolor='black')
ax3.set_ylabel('Parameters (millions)', fontsize=12, fontweight='bold')
ax3.set_title('Model Complexity', fontsize=13, fontweight='bold')
ax3.grid(axis='y', alpha=0.3)
for bar, val in zip(bars3, params):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{val:.2f}M',
             ha='center', va='bottom', fontweight='bold', fontsize=11)

# 4. Epochs Comparison
ax4 = axes[1, 0]
bars4 = ax4.bar(models, epochs, color=['#3498db', '#2ecc71'], alpha=0.8, edgecolor='black')
ax4.set_ylabel('Training Epochs', fontsize=12, fontweight='bold')
ax4.set_title('Convergence Speed', fontsize=13, fontweight='bold')
ax4.grid(axis='y', alpha=0.3)
for bar, val in zip(bars4, epochs):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
             f'{val}',
             ha='center', va='bottom', fontweight='bold', fontsize=11)

# 5. Training Time Comparison
ax5 = axes[1, 1]
bars5 = ax5.bar(models, training_time, color=['#3498db', '#2ecc71'], alpha=0.8, edgecolor='black')
ax5.set_ylabel('Training Time (minutes)', fontsize=12, fontweight='bold')
ax5.set_title('Computational Cost', fontsize=13, fontweight='bold')
ax5.grid(axis='y', alpha=0.3)
for bar, val in zip(bars5, training_time):
    height = bar.get_height()
    ax5.text(bar.get_x() + bar.get_width()/2., height,
             f'{val:.1f}m',
             ha='center', va='bottom', fontweight='bold', fontsize=11)

# 6. Summary Table
ax6 = axes[1, 2]
ax6.axis('off')
table_data = [
    ['Metric', 'Simple CNN', 'Improved CNN', 'Δ'],
    ['MAE', f'{mae_values[0]:.2f}m', f'{mae_values[1]:.2f}m', f'↓{improvement:.1f}%'],
    ['R²', f'{r2_values[0]:.3f}', f'{r2_values[1]:.3f}', f'↑{((r2_values[1]-r2_values[0])/r2_values[0]*100):.1f}%'],
    ['Params', f'{params[0]:.2f}M', f'{params[1]:.2f}M', f'↑{((params[1]-params[0])/params[0]*100):.0f}%'],
    ['Epochs', f'{epochs[0]}', f'{epochs[1]}', f'↑{((epochs[1]-epochs[0])/epochs[0]*100):.0f}%'],
    ['Time', f'{training_time[0]:.1f}m', f'{training_time[1]:.1f}m', f'↑{((training_time[1]-training_time[0])/training_time[0]*100):.0f}%'],
]

table = ax6.table(cellText=table_data, cellLoc='center', loc='center',
                  colWidths=[0.25, 0.25, 0.25, 0.25])
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2)

# Style header row
for i in range(4):
    table[(0, i)].set_facecolor('#34495e')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Color improvement column
for i in range(1, 6):
    table[(i, 3)].set_facecolor('#d5f4e6' if '↓' in table_data[i][3] or (i in [2] and '↑' in table_data[i][3]) else '#ffe6e6')
    table[(i, 3)].set_text_props(weight='bold')

ax6.set_title('Performance Summary', fontsize=13, fontweight='bold', pad=20)

plt.tight_layout()

# Save figure
output_path = 'results/cnn_comparison.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"✅ Comparison plot saved to: {output_path}")

# Also save to neural_networks folder
output_path2 = 'experiments/neural_networks/cnn_comparison.png'
plt.savefig(output_path2, dpi=300, bbox_inches='tight')
print(f"✅ Comparison plot also saved to: {output_path2}")

plt.show()

print("\n" + "="*60)
print("📊 CNN MODELS COMPARISON SUMMARY")
print("="*60)
print(f"Dataset: exp11 (40K samples, 70% NLOS)")
print(f"\n🏆 WINNER: Improved CNN")
print(f"   - MAE: {mae_values[1]:.2f}m (↓{improvement:.1f}% better)")
print(f"   - R²: {r2_values[1]:.3f} (↑{((r2_values[1]-r2_values[0])/r2_values[0]*100):.1f}% better)")
print(f"   - Cost: 2× parameters, 18× training time")
print(f"\n💡 Key Insight: Worth the extra complexity!")
print(f"   - 21% better accuracy justifies 2× parameters")
print(f"   - Still fast: 12.7s/epoch on GTX 1650")
print("="*60)
