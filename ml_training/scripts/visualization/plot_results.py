"""Quick visualization of feature selection results."""
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('output/generated_data/feature_selection_comparison.csv')

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# MAE plot
for method in df['method'].unique():
    data = df[df['method']==method].sort_values('n_features')
    ax1.plot(data['n_features'], data['mae'], marker='o', label=method, linewidth=2)

ax1.axhline(28.24, color='red', linestyle='--', linewidth=2, label='Baseline (771 feat)', alpha=0.7)
ax1.set_xlabel('Number of Features', fontweight='bold', fontsize=12)
ax1.set_ylabel('MAE (meters)', fontweight='bold', fontsize=12)
ax1.set_title('Performance vs Number of Features', fontweight='bold', fontsize=14)
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.set_ylim([27.5, 30])

# R² plot
for method in df['method'].unique():
    data = df[df['method']==method].sort_values('n_features')
    ax2.plot(data['n_features'], data['r2'], marker='o', label=method, linewidth=2)

ax2.axhline(0.2467, color='red', linestyle='--', linewidth=2, label='Baseline (771 feat)', alpha=0.7)
ax2.set_xlabel('Number of Features', fontweight='bold', fontsize=12)
ax2.set_ylabel('R² Score', fontweight='bold', fontsize=12)
ax2.set_title('R² vs Number of Features', fontweight='bold', fontsize=14)
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('output/generated_data/feature_selection_summary.png', dpi=150, bbox_inches='tight')
print('✓ Plot saved: output/generated_data/feature_selection_summary.png')
plt.close()
