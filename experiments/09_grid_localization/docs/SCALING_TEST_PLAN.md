# Scaling Test Plan: 3×3 to 20×20 Grids

## Why Scale Tests?
- Test if transition-based approach scales with grid size
- Understand how accuracy degrades with more classes
- See if spatial constraints become more valuable in larger grids

## Recommended Test Sequence

### Phase 1: Small Grids (Validation)
**Goal:** Verify baseline performance

| Grid Size | Points | Steps | Samples/Point | Runtime Est. | Priority |
|:----------|:-------|:------|:--------------|:-------------|:---------|
| 3×3 | 9 | 10,000 | ~1,111 | ~2 min | ✅ Done |
| 4×4 | 16 | 20,000 | ~1,250 | ~4 min | High |
| 5×5 | 25 | 30,000 | ~1,200 | ~6 min | High |

### Phase 2: Medium Grids (Transition Point)
**Goal:** Find where static accuracy drops significantly

| Grid Size | Points | Steps | Samples/Point | Runtime Est. | Priority |
|:----------|:-------|:------|:--------------|:-------------|:---------|
| 6×6 | 36 | 50,000 | ~1,389 | ~10 min | High |
| 8×8 | 64 | 80,000 | ~1,250 | ~16 min | Medium |
| 10×10 | 100 | 120,000 | ~1,200 | ~24 min | Medium |

### Phase 3: Large Grids (Challenge Zone)
**Goal:** Test limits of both approaches

| Grid Size | Points | Steps | Samples/Point | Runtime Est. | Priority |
|:----------|:-------|:------|:--------------|:-------------|:---------|
| 12×12 | 144 | 180,000 | ~1,250 | ~35 min | Low |
| 15×15 | 225 | 270,000 | ~1,200 | ~55 min | Low |
| 20×20 | 400 | 500,000 | ~1,250 | ~100 min | Low |

## Key Parameters to Adjust

### Steps Calculation
```matlab
% Aim for ~1,200 samples per grid point
config.n_steps = grid_size^2 * 1200;
```

### Expected Accuracy Trends

**Static Approach:**
- 3×3 (9 classes): ~97% LOS, ~32% NLOS
- 5×5 (25 classes): ~80%? LOS, ~15%? NLOS
- 10×10 (100 classes): ~50%? LOS, ~5%? NLOS
- 20×20 (400 classes): ~20%? LOS, ~2%? NLOS

**Transition Approach - Hypotheses:**

✅ **Hypothesis 1:** Improvement increases with grid size
- Spatial constraints become more valuable when there are more classes
- Expected: +1% (3×3) → +5% (10×10) → +10% (20×20)

❌ **Hypothesis 2:** Improvement remains constant
- Spatial constraint helps equally regardless of grid size
- Expected: +1-2% improvement at all scales

❌ **Hypothesis 3:** Improvement decreases with grid size
- Noise overwhelms the constraint in larger grids
- Expected: +1% (3×3) → +0.5% (10×10) → +0% (20×20)

## Recommended Test Schedule

### Day 1: Baseline (LOS only)
```matlab
grid_sizes = [3, 4, 5, 6, 8];
for each: run LOS, record static & transition accuracy
```

### Day 2: Full Comparison (LOS + NLOS)
```matlab
grid_sizes = [3, 5, 8, 10];
for each: run both LOS and NLOS
```

### Day 3: Large Scale (if time permits)
```matlab
grid_sizes = [12, 15, 20];
LOS only (NLOS accuracy will be too low to be useful)
```

## Computational Considerations

### Memory
- 20×20 grid with 500k steps: ~500k × 256 subcarriers × complex = ~512 MB
- Should fit in memory, but may be slow

### Time
- Channel generation: ~0.02 sec/snapshot → 500k steps = ~3 hours just for channels
- **Recommendation:** Start with 10×10 to validate before jumping to 20×20

### Optimization Options
If tests are too slow:
1. Reduce `n_subcarriers` from 256 to 128
2. Use only RSS (skip SINR, CQI)
3. Reduce samples per point to 800-1000

## Analysis to Track

For each grid size, record:
1. **Static accuracy** (RSS, LOS/NLOS)
2. **Transition accuracy** (RSS, LOS/NLOS)
3. **Improvement** = Transition - Static
4. **Random baseline** = 1/n_points × 100%
5. **Separation** = Static accuracy - Random baseline

### Expected Pattern
```
Grid  | Random | Static | Transition | Improvement | Separation
------|--------|--------|------------|-------------|------------
3×3   | 11.1%  | 97%    | 98%       | +1%         | 86%
5×5   | 4.0%   | 80%    | 84%?      | +4%?        | 76%
10×10 | 1.0%   | 50%    | 60%?      | +10%?       | 49%
20×20 | 0.25%  | 20%    | 35%?      | +15%?       | 19.75%
```

## Success Criteria

**Transition approach is valuable if:**
- Improvement ≥ 2% for grid sizes ≥ 5×5
- Improvement increases with grid size
- Works in both LOS and NLOS

**Static approach is sufficient if:**
- Improvement < 1% at all scales
- Computational cost doesn't justify small gains

## Recommended Code Template

```matlab
%% Scaling Test Script
grid_sizes = [3, 4, 5, 6, 8, 10];
scenarios = {'3GPP_38.901_UMa_LOS', '3GPP_38.901_UMa_NLOS'};

results_table = [];

for g_idx = 1:length(grid_sizes)
    grid_size = grid_sizes(g_idx);
    n_steps = grid_size^2 * 1200;
    
    for s_idx = 1:length(scenarios)
        scenario = scenarios{s_idx};
        
        % Update config
        config.grid_size = grid_size;
        config.n_steps = n_steps;
        config.scenario = scenario;
        
        % Run experiment
        fprintf('Running: %dx%d, %s\n', grid_size, grid_size, scenario);
        % ... run classification ...
        
        % Store results
        results_table(end+1, :) = [grid_size, strcmp(scenario, 'LOS'), ...
                                   static_acc, transition_acc];
    end
end

% Plot results
figure;
plot(grid_sizes.^2, results_table(:,3), 'o-', 'DisplayName', 'Static');
hold on;
plot(grid_sizes.^2, results_table(:,4), 's-', 'DisplayName', 'Transition');
xlabel('Number of Grid Points');
ylabel('Accuracy (%)');
legend;
title('Scaling: Static vs Transition');
```

## Next Steps

1. **Start with 5×5 grid** to validate the approach scales
2. If improvement increases, continue to 8×8, 10×10
3. If improvement stays flat or decreases, document and stop at 10×10
4. Only attempt 20×20 if computational budget allows and trend is promising
