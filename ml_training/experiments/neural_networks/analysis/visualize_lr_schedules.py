"""
Visualize different learning rate schedules to understand their behavior.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import OUTPUT_DIR


def plateau_schedule(epochs=100, initial_lr=0.001):
    """Simulate ReduceLROnPlateau."""
    lr = [initial_lr] * epochs
    # Simulated plateaus at epochs 20, 40, 60
    for i in range(20, epochs):
        lr[i] = initial_lr * 0.5
    for i in range(40, epochs):
        lr[i] = initial_lr * 0.25
    for i in range(60, epochs):
        lr[i] = initial_lr * 0.125
    return lr


def cosine_schedule(epochs=100, initial_lr=0.001, min_lr=0.00001):
    """Cosine annealing schedule."""
    lr = []
    for epoch in range(epochs):
        lr_t = min_lr + (initial_lr - min_lr) * (1 + np.cos(np.pi * epoch / epochs)) / 2
        lr.append(lr_t)
    return lr


def cosine_restarts_schedule(epochs=120, initial_lr=0.001, T_0=20, T_mult=2, min_lr=0.00001):
    """Cosine annealing with warm restarts."""
    lr = []
    T_cur = 0
    T_i = T_0
    
    for epoch in range(epochs):
        lr_t = min_lr + (initial_lr - min_lr) * (1 + np.cos(np.pi * T_cur / T_i)) / 2
        lr.append(lr_t)
        
        T_cur += 1
        if T_cur >= T_i:
            T_cur = 0
            T_i *= T_mult
    
    return lr


def onecycle_schedule(epochs=80, max_lr=0.003, pct_start=0.3):
    """OneCycleLR schedule."""
    lr = []
    warmup_epochs = int(epochs * pct_start)
    
    for epoch in range(epochs):
        if epoch < warmup_epochs:
            # Warmup phase
            lr_t = max_lr * (epoch + 1) / warmup_epochs
        else:
            # Cosine annealing down
            progress = (epoch - warmup_epochs) / (epochs - warmup_epochs)
            lr_t = max_lr * (1 + np.cos(np.pi * progress)) / 2 * 0.01  # Down to 1% of max
        lr.append(lr_t)
    
    return lr


def warmup_cosine_schedule(epochs=100, max_lr=0.002, warmup_epochs=10, min_lr=0.00002):
    """Warmup + Cosine annealing."""
    lr = []
    
    for epoch in range(epochs):
        if epoch < warmup_epochs:
            # Linear warmup
            lr_t = max_lr * (epoch + 1) / warmup_epochs
        else:
            # Cosine decay
            progress = (epoch - warmup_epochs) / (epochs - warmup_epochs)
            lr_t = min_lr + (max_lr - min_lr) * (1 + np.cos(np.pi * progress)) / 2
        lr.append(lr_t)
    
    return lr


def plot_schedules():
    """Plot all learning rate schedules."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Learning Rate Schedules Comparison', fontsize=16, fontweight='bold')
    
    schedules = [
        ('Plateau (Current)', plateau_schedule(100, 0.0005), 0, 0),
        ('Cosine Annealing', cosine_schedule(100, 0.001), 0, 1),
        ('Cosine with Restarts', cosine_restarts_schedule(120, 0.001), 0, 2),
        ('OneCycleLR', onecycle_schedule(80, 0.003), 1, 0),
        ('Warmup + Cosine', warmup_cosine_schedule(100, 0.002), 1, 1),
        ('Comparison', None, 1, 2),  # Combined plot
    ]
    
    all_schedules = {}
    
    for name, schedule, row, col in schedules:
        ax = axes[row, col]
        
        if name == 'Comparison':
            # Plot all schedules together (normalized)
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            labels = ['Plateau', 'Cosine', 'Cosine Restarts', 'OneCycle', 'Warmup+Cosine']
            
            for i, (label, (_, sched, _, _)) in enumerate(zip(labels, schedules[:-1])):
                epochs = list(range(len(sched)))
                # Normalize to [0, 1] for comparison
                sched_norm = np.array(sched) / max(sched)
                ax.plot(epochs, sched_norm, label=label, linewidth=2, color=colors[i])
            
            ax.set_xlabel('Epoch', fontsize=12)
            ax.set_ylabel('Normalized Learning Rate', fontsize=12)
            ax.set_title('All Schedules Comparison', fontsize=13, fontweight='bold')
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
            
        else:
            epochs = list(range(len(schedule)))
            ax.plot(epochs, schedule, linewidth=2.5, color='#2ca02c')
            ax.fill_between(epochs, schedule, alpha=0.3, color='#2ca02c')
            
            ax.set_xlabel('Epoch', fontsize=12)
            ax.set_ylabel('Learning Rate', fontsize=12)
            ax.set_title(name, fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Add annotations
            max_lr = max(schedule)
            min_lr = min(schedule)
            ax.axhline(max_lr, color='red', linestyle='--', alpha=0.5, linewidth=1)
            ax.axhline(min_lr, color='blue', linestyle='--', alpha=0.5, linewidth=1)
            ax.text(len(schedule)*0.05, max_lr*1.05, f'Max: {max_lr:.6f}', fontsize=9)
            ax.text(len(schedule)*0.05, min_lr*1.1, f'Min: {min_lr:.6f}', fontsize=9)
            
            all_schedules[name] = schedule
    
    plt.tight_layout()
    
    # Save plot
    save_dir = OUTPUT_DIR / 'plots'
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / 'lr_schedules_comparison.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {save_path}")
    
    plt.show()
    
    # Print summary
    print("\n" + "=" * 70)
    print("LEARNING RATE SCHEDULES SUMMARY")
    print("=" * 70)
    
    summaries = [
        ("Plateau", "Step-wise drops when loss plateaus", "Safe, but can get stuck"),
        ("Cosine", "Smooth decay from max to min", "Better exploration, more epochs"),
        ("Cosine Restarts", "Periodic restarts escape local minima", "Best for long training"),
        ("OneCycle", "Fast rise then decay", "Fast convergence, high accuracy"),
        ("Warmup + Cosine", "Linear warmup then cosine", "Most stable, prevents divergence"),
    ]
    
    for name, description, notes in summaries:
        print(f"\n{name}:")
        print(f"  Description: {description}")
        print(f"  Notes: {notes}")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print("1. For extended training (100+ epochs): Cosine Annealing")
    print("2. For fast convergence (50-80 epochs): OneCycleLR")
    print("3. For stability with high LR: Warmup + Cosine")
    print("4. For very long training (120+ epochs): Cosine with Restarts")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    print("Generating learning rate schedule comparisons...\n")
    plot_schedules()
    print("\n✅ Visualization complete!")
