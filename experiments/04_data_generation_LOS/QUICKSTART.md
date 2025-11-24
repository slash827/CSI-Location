# Experiment 10: Quick Start Guide

## 🎯 Goal

Generate a large, diverse CSI dataset with **32,000+ training samples** and **8,000+ validation samples** for ML training.

## ⚡ Quick Start (5 minutes to launch)

### Step 1: Navigate to folder
```matlab
cd experiments/04_data_generation
```

### Step 2: Run data generation
```matlab
exp10_large_dataset
```

**That's it!** The script will run for 30-60 minutes.

## 📊 What Gets Generated

### Dataset Files
```
results/exp10_YYYY-MM-DD_HH-MM-SS/
├── dataset/
│   ├── train_data.mat     (~32,000 samples × 771 features)
│   └── val_data.mat       (~8,000 samples × 771 features)
├── trajectories/          (Sample trajectory visualizations)
├── experiment_report.txt  (Detailed statistics)
└── validation_*.png       (Validation plots)
```

### Features per Sample
- **Wideband** (3): CQI_wb, RSRP, SINR_wb
- **Per-subcarrier** (768): 
  - RSS_per_sc (256)
  - SINR_per_sc (256)
  - H_mag_per_sc (256)

## 🎨 Trajectory Types

The dataset includes 7 types of trajectories:

1. **Linear** (20%): Straight-line motion
2. **Circular** (15%): Clockwise/counter-clockwise circles
3. **Zigzag** (15%): Sharp directional changes
4. **Random Walk** (20%): Natural, stochastic movement
5. **Grid** (10%): Systematic area coverage
6. **Spiral** (10%): Expanding/contracting spirals
7. **Figure-8** (10%): Lemniscate curves

## ⚙️ Customization

### Change Number of Trajectories

Edit `config_large_dataset.m`:
```matlab
config.n_trajectories = 1000;  % Instead of 500 (doubles dataset size)
```

### Change Trajectory Distribution

Edit `config_large_dataset.m`:
```matlab
config.trajectory_distribution = struct(...
    'linear', 0.30, ...        % More linear paths
    'circular', 0.10, ...      
    'zigzag', 0.10, ...        
    'random_walk', 0.30, ...   % More random walks
    'grid', 0.05, ...          
    'spiral', 0.05, ...        
    'figure8', 0.10 ...
);
```

### Change Area Size

Edit `config_large_dataset.m`:
```matlab
config.scenario.bounds = struct(...
    'x_min', 0, ...      % Expand area
    'x_max', 100, ...
    'y_min', 0, ...
    'y_max', 100, ...
    'z', 1.5
);
```

## 🔍 Validation

After generation completes, validate the dataset:

```matlab
% Assuming exp10 output is in: results/exp10_2025-11-07_12-00-00/
validate_dataset('../../results/exp10_2025-11-07_12-00-00/dataset/')
```

This will:
- Check data integrity (no NaN/Inf)
- Verify spatial coverage (>90% target)
- Analyze diversity
- Generate validation plots

## 🤖 ML Training

After dataset generation:

### Step 1: Update config
Edit `ml_training/config.py`:
```python
DEFAULT_DATASET_PATH = Path('results/exp10_2025-11-07_12-00-00/dataset')
```

### Step 2: Run EDA
```bash
cd ml_training
python eda.py
```

### Step 3: Train models
```bash
python models/baseline_models.py
```

### Expected Performance
- **Current** (640 samples): 28.24 m MAE
- **Expected** (32,000 samples): **5-10 m MAE** ⭐
- **Target** (with neural nets): **<3 m MAE** 🎯

## ⏱️ Timeline

| Step | Duration | Description |
|------|----------|-------------|
| Configuration | 2-5 min | Edit config if needed |
| **Data Generation** | **30-60 min** | QuaDRiGa simulation |
| Validation | 2-5 min | Check dataset quality |
| ML Training | 10-15 min | Train baseline models |
| Analysis | 10-15 min | Evaluate results |
| **Total** | **~1-2 hours** | End-to-end |

## 💡 Tips

### Faster Generation
- Reduce `n_trajectories` to 200 (test run)
- Disable plots: `config.output.generate_plots = false`
- Use fewer timesteps: `config.n_timesteps = 50`

### Larger Dataset
- Increase `n_trajectories` to 1000+
- Will take longer but improve model performance
- Monitor disk space (~2-5 GB per 500 trajectories)

### Quality Check
Watch for these in the output:
- "✓ Generated 500 trajectories" 
- "✓ Simulation complete"
- "Training samples: 32000"
- "Validation samples: 8000"

## 🐛 Troubleshooting

### Issue: "Out of memory"
**Solution**: Reduce `n_trajectories` or process in batches

### Issue: Simulation very slow
**Solution**: 
- Check QuaDRiGa installation
- Reduce `n_timesteps` 
- Disable progress plots

### Issue: Dataset file not found
**Solution**: Check output path in console, update `config.py` accordingly

## 📖 Next Steps

After successful generation:

1. ✅ Validate dataset quality
2. ✅ Update ML config path
3. ✅ Run exploratory data analysis
4. ✅ Train baseline models
5. ✅ Compare with small dataset (640 samples)
6. ✅ If performance good → train neural networks
7. ✅ If performance poor → generate more trajectories

## 🎯 Success Criteria

Your dataset is ready for ML if:
- ✅ 30,000+ training samples
- ✅ 8,000+ validation samples
- ✅ >90% spatial coverage
- ✅ No NaN/Inf values
- ✅ All 7 trajectory types represented

---

**Expected Impact**: Reduce localization error from **28m → 5-10m** 🚀
