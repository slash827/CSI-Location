
# GRID LOCALIZATION - CRITICAL ISSUES AND SOLUTIONS


This document outlines key challenges in the grid localization pipeline and
provides actionable solutions for improving performance and scalability.


# SECTION 1: DATA LEAKAGE IN TRAIN/TEST SPLIT


QUESTIONS:
----------
- Check if the current train vs test split is not causing data leakage
- How can we even make sure there is no data leakage in such scenario of random walking?
- Maybe instead of random walking, we add some ordered walking (scanning rows then scanning columns etc)

CURRENT ISSUE:
--------------
Random train/test split on consecutive samples from a random walk creates temporal leakage:
- Sample t (train) and sample t+1 (test) are highly correlated
- Model can memorize trajectory patterns → overestimated performance
- Real deployment will perform WORSE than reported metrics

SOLUTIONS:

1. TEMPORAL SPLITTING (Quick Fix):
   train_cutoff = int(n_samples * 0.8)
   train_indices = np.arange(0, train_cutoff)
   test_indices = np.arange(train_cutoff, n_samples)
   
   ✓ No temporal leakage
   ✓ Simulates train-on-past, predict-future scenario
   ✗ Spatial distribution might differ between train/test

2. MULTIPLE INDEPENDENT WALKS (Best Approach):
   Generate 5 separate walks, use walks 1-4 for train, walk 5 for test
   ✓ Complete independence
   ✓ True generalization test
   ✗ Requires modifying MATLAB data generation

3. ORDERED WALKING PATTERNS (Recommended Addition):
   Add systematic scanning patterns alongside random walks:
   - Row-by-row scanning (snake pattern)
   - Column-by-column scanning
   - Spiral patterns
   - Diagonal patterns
   
   Benefits:
   ✓ Clean evaluation (leave-one-scan-out cross-validation)
   ✓ No temporal leakage
   ✓ Realistic for surveillance/monitoring scenarios
   ✓ Better coverage of grid space



# SECTION 2: CURSE OF DIMENSIONALITY


PROBLEMS IDENTIFIED:
--------------------
1. 4-neighbor vs 8-neighbor topology
2. Scalability to larger grids (10x10, 15x15, 20x20)
3. Computational explosion with history length
4. Path enumeration grows exponentially

PROBLEM 2.1: 4-NEIGHBORS vs 8-NEIGHBORS


CURRENT IMPLEMENTATION (4-neighbors):
--------------------------------------
For each grid point, only horizontal and vertical neighbors are allowed:
  Point (i,j) → neighbors: (i±1,j), (i,j±1)
  
  Grid visualization:
       |
    ---●---
       |
  
Maximum neighbors per point: 4 (corner: 2, edge: 3, interior: 4)

INSTRUCTOR'S REQUEST (8-neighbors):
------------------------------------
Include diagonal neighbors as well:
  Point (i,j) → neighbors: (i±1,j), (i,j±1), (i±1,j±1), (i±1,j-1)
  
  Grid visualization:
    \ | /
    --●--
    / | \
  
Maximum neighbors per point: 8 (corner: 3, edge: 5, interior: 8)

COMPUTATIONAL IMPACT:
---------------------
For a 10x10 grid with history h=3:

4-neighbors:
  - Interior points: 4 possible previous locations
  - Path enumeration: ~4 × 4 × 4 = 64 paths per sample
  - Total iterations: 100 samples × 64 paths = 6,400

8-neighbors:
  - Interior points: 8 possible previous locations
  - Path enumeration: ~8 × 8 × 8 = 512 paths per sample
  - Total iterations: 100 samples × 512 paths = 51,200
  
  ⚠️ 8x MORE COMPUTATION!

SOLUTION 2.1.1: Optimize Neighbor Lookup (Already Implemented)
---------------------------------------------------------------
Current code uses reverse_neighbors dict for O(1) lookup:
  self.reverse_neighbors[curr_loc] = [locs that have curr_loc as neighbor]
  
This is already optimal. The issue is the NUMBER of neighbors, not lookup speed.

SOLUTION 2.1.2: Transition Probability Pruning
-----------------------------------------------
Don't enumerate ALL paths - prune unlikely transitions:

def predict_with_pruning(self, metric_value, previous_values, threshold=-10):
    # Pre-compute log probabilities for each possible prev location
    prev_loc_scores = {}
    
    for prev_loc in range(n_points):
        # Score based on previous observation
        score = norm.logpdf(previous_values[-1], 
                           self.static_models[prev_loc]['mean'],
                           self.static_models[prev_loc]['std'])
        prev_loc_scores[prev_loc] = score
    
    # PRUNE: Only keep top K most likely previous locations
    top_k = 20  # Instead of all 100 points
    top_prev_locs = sorted(prev_loc_scores.items(), 
                          key=lambda x: x[1], reverse=True)[:top_k]
    
    # Now enumerate paths only through these top-k locations
    for prev_loc_idx, _ in top_prev_locs:
        # Continue with normal path enumeration...

Expected speedup: 100/20 = 5x faster with minimal accuracy loss

SOLUTION 2.1.3: Beam Search Instead of Full Enumeration
--------------------------------------------------------
Instead of considering ALL possible paths, maintain top-K candidates:

h=1: Keep top 20 most likely previous locations
h=2: For each of those 20, keep top 5 second-previous → 20×5 = 100 paths
h=3: For each of 100, keep top 3 third-previous → 100×3 = 300 paths

Total: 300 paths instead of 8^3 = 512 paths
Speedup: ~1.7x with high accuracy retention

SOLUTION 2.1.4: Implement 8-Neighbors with Weighted Transitions
----------------------------------------------------------------
Make diagonal transitions less likely (they're longer distance):

When generating neighbors dict:
  # 4-neighbors (distance = grid_spacing)
  horizontal_vertical_weight = 1.0
  
  # Diagonal neighbors (distance = grid_spacing × √2)
  diagonal_weight = 0.5  # Less likely to move diagonally
  
Apply weight in probability calculation:
  transition_prob = weight × norm.pdf(delta, mean_delta, std_delta)

This naturally prunes unlikely diagonal transitions.

IMPLEMENTATION GUIDE FOR 8-NEIGHBORS:
--------------------------------------
Modify experiments/09_grid_localization/generate_simulation_data.m:

% Generate 8-neighbor topology
function neighbors = generate_8_neighbors(grid_size)
    neighbors = cell(grid_size * grid_size, 1);
    
    for row = 1:grid_size
        for col = 1:grid_size
            idx = (row-1) * grid_size + col;
            neighbor_list = [];
            
            % 4-neighbors (horizontal/vertical)
            directions_4 = [-1,0; 1,0; 0,-1; 0,1];
            for d = 1:size(directions_4, 1)
                new_row = row + directions_4(d,1);
                new_col = col + directions_4(d,2);
                if new_row >= 1 && new_row <= grid_size && ...
                   new_col >= 1 && new_col <= grid_size
                    neighbor_idx = (new_row-1) * grid_size + new_col;
                    neighbor_list = [neighbor_list, neighbor_idx];
                end
            end
            
            % Additional diagonal neighbors
            directions_diag = [-1,-1; -1,1; 1,-1; 1,1];
            for d = 1:size(directions_diag, 1)
                new_row = row + directions_diag(d,1);
                new_col = col + directions_diag(d,2);
                if new_row >= 1 && new_row <= grid_size && ...
                   new_col >= 1 && new_col <= grid_size
                    neighbor_idx = (new_row-1) * grid_size + new_col;
                    neighbor_list = [neighbor_list, neighbor_idx];
                end
            end
            
            neighbors{idx} = neighbor_list;
        end
    end
end

Add to config.json:
  "grid": {
    "neighbor_topology": "8-connected",  // or "4-connected"
    ...
  }


PROBLEM 2.2: SCALABILITY TO LARGER GRIDS
=

CURRENT STATUS:
---------------
Grid Size | Points | h=3 Paths (4-neigh) | h=3 Paths (8-neigh) | Eval Time
----------|--------|---------------------|---------------------|----------
3x3       |   9    |        64           |        512          |   ~5s
5x5       |  25    |        64           |        512          |  ~40s
10x10     | 100    |        64           |        512          | ~700s
15x15     | 225    |        64           |        512          |~2500s (42min)
20x20     | 400    |        64           |        512          |~7000s (2hr)

⚠️ EXPONENTIAL GROWTH with grid size!

Why it's slow:
  - For each test sample: iterate over ALL grid points
  - For each grid point: enumerate paths through neighbors
  - For each path: compute log probabilities

Bottleneck: The outer loop over ALL grid points (100 for 10x10)

SOLUTION 2.2.1: Hierarchical Coarse-to-Fine Prediction
-------------------------------------------------------
Don't search all 100 points - narrow down first:

Step 1 (Coarse): Divide grid into 4 quadrants, pick most likely quadrant
Step 2 (Medium): Within quadrant, pick most likely sub-region  
Step 3 (Fine): Within region, do full transition-based prediction

Example for 20x20 grid:
  Coarse:  4 regions (10x10 each) → pick 1
  Medium: 4 sub-regions (5x5 each) → pick 1  
  Fine:   25 points in 5x5 → full search
  
  Total candidates: 4 + 4 + 25 = 33 instead of 400
  Speedup: 400/33 = 12x faster!

SOLUTION 2.2.2: Static Prediction to Narrow Search Space
---------------------------------------------------------
Use static model first to get top-K candidates, then apply transition:

def predict_hierarchical(self, metric_value, previous_values):
    # Step 1: Static prediction to get top-K candidates
    static_posterior = self.static_predict(metric_value)
    top_k_indices = np.argsort(static_posterior)[-20:]  # Top 20
    
    # Step 2: Transition-based search ONLY within top-K
    transition_posterior = np.zeros(n_points)
    for curr_loc in top_k_indices:
        # Enumerate paths ending at curr_loc
        transition_posterior[curr_loc] = self._compute_transition_prob(
            curr_loc, metric_value, previous_values
        )
    
    return transition_posterior

Expected speedup: 100/20 = 5x with minimal accuracy loss

SOLUTION 2.2.3: GPU Acceleration for Probability Computation
-------------------------------------------------------------
Move PDF calculations to GPU using CuPy:

import cupy as cp
from cupyx.scipy.stats import norm as cu_norm

# Pre-compute on GPU
deltas_gpu = cp.array(deltas_observed)
means_gpu = cp.array([model['mean_delta'] for model in models])
stds_gpu = cp.array([model['std_delta'] for model in models])

# Vectorized computation on GPU
log_probs = cu_norm.logpdf(deltas_gpu[:, None], means_gpu, stds_gpu)

Expected speedup: 10-50x for large grids (requires CUDA GPU)

SOLUTION 2.2.4: Parallel Processing with Multiprocessing
---------------------------------------------------------
Evaluate multiple test samples in parallel:

from multiprocessing import Pool

def evaluate_sample(args):
    idx, metric_value, previous_values = args
    return model.predict(metric_value, previous_values)

with Pool(processes=8) as pool:
    results = pool.map(evaluate_sample, 
                      [(idx, metric_values[idx], prev_vals[idx]) 
                       for idx in test_indices])

Expected speedup: Linear with CPU cores (~8x on 8-core CPU)

SOLUTION 2.2.5: Approximate Nearest Neighbor Search
----------------------------------------------------
Use spatial indexing (KD-tree) to quickly find nearby grid points:

from scipy.spatial import KDTree

# Build KD-tree of grid positions
tree = KDTree(grid_positions)

# For prediction, only consider spatially nearby points
nearby_indices = tree.query_ball_point(estimated_position, r=10.0)

Then only search within nearby_indices instead of all points.


PROBLEM 2.3: MEMORY OPTIMIZATION
=

CURRENT ISSUE:
--------------
For large grids, storing confusion matrices and all predictions uses lots of RAM:
  10x10 grid: confusion_matrix is 100×100 = 10,000 elements
  20x20 grid: confusion_matrix is 400×400 = 160,000 elements

SOLUTION 2.3.1: Sparse Confusion Matrix
----------------------------------------
Most entries are zero (predictions cluster around truth):

from scipy.sparse import lil_matrix

cm = lil_matrix((n_points, n_points), dtype=np.int32)
for true_loc, pred_loc in zip(true_labels, predictions):
    cm[true_loc-1, pred_loc-1] += 1

Memory savings: ~90% for large sparse matrices

SOLUTION 2.3.2: Stream Processing
----------------------------------
Don't store all predictions - compute metrics incrementally:

total_correct = 0
total_error = 0
for idx in test_indices:
    pred = model.predict(metric_values[idx], ...)
    total_correct += (pred == true_locations[idx])
    total_error += abs(pred - true_locations[idx])

accuracy = total_correct / len(test_indices)
mae = total_error / len(test_indices)

Memory: O(1) instead of O(n_test)


PROBLEM 2.4: HISTORY LENGTH vs COMPUTATION TRADEOFF


OBSERVATION:
------------
From your results (3x3 LOS, RSS):
  h=1: 79.14% accuracy, 2.18s eval
  h=2: 83.45% accuracy, 4.77s eval  (2.2x slower, +4.3% accuracy)
  h=3: 87.48% accuracy, 4.26s eval  (2.0x slower, +4.0% accuracy)

Diminishing returns: Each additional history costs ~2x time for ~4% improvement

SOLUTION 2.4.1: Adaptive History Length
----------------------------------------
Use shorter history when confidence is high:

def predict_adaptive(self, metric_value, previous_values, max_history=3):
    # Start with h=1
    posterior_h1 = self.predict_h1(metric_value, previous_values[-1:])
    confidence = np.max(posterior_h1)
    
    if confidence > 0.8:
        return posterior_h1  # Confident enough, stop
    
    # Try h=2
    posterior_h2 = self.predict_h2(metric_value, previous_values[-2:])
    confidence = np.max(posterior_h2)
    
    if confidence > 0.7:
        return posterior_h2
    
    # Fall back to h=3
    return self.predict_h3(metric_value, previous_values[-3:])

Expected speedup: 2-3x on average while maintaining accuracy

SOLUTION 2.4.2: Early Stopping in Path Enumeration
---------------------------------------------------
Stop exploring paths when probability becomes negligible:

for prev_loc in possible_prev_locs:
    log_prob = compute_path_prob(prev_loc, ...)
    
    if log_prob < best_log_prob - 10:  # 10 orders of magnitude worse
        continue  # Skip this path
    
    # Only explore promising paths
    for prev_prev_loc in ...

Speedup: ~2-5x with negligible accuracy loss


RECOMMENDED IMPLEMENTATION PRIORITIES:
===

PRIORITY 1 (This Week) - Low-Hanging Fruit:
--------------------------------------------
1. ✅ Implement temporal splitting (already discussed)
2. ✅ Add transition probability pruning (top-K candidates)
3. ✅ Implement adaptive history length

Expected Impact: 5-10x speedup, minimal accuracy loss
Effort: 1-2 days coding

PRIORITY 2 (Next Week) - Moderate Effort:
------------------------------------------
4. ✅ Implement hierarchical coarse-to-fine search
5. ✅ Add multiprocessing for parallel evaluation
6. ✅ Implement 8-neighbor topology with diagonal weighting

Expected Impact: 10-20x speedup, handle 15x15 grids easily
Effort: 3-5 days coding + testing

PRIORITY 3 (Long-term) - Advanced Optimizations:
-------------------------------------------------
7. ⚠️ GPU acceleration (requires CUDA setup)
8. ⚠️ Approximate nearest neighbor search
9. ⚠️ Sparse matrix optimizations

Expected Impact: 50-100x speedup, handle 20x20+ grids
Effort: 1-2 weeks + GPU hardware


SAMPLE CODE FOR TOP PRIORITIES:


IMPLEMENTATION: Top-K Pruning
------------------------------
Add to GaussianTransitionModel.predict():

def predict(self, metric_value, previous_values=None, top_k=30):
    n_points = len(self.static_models)
    
    if previous_values is None or len(previous_values) == 0:
        # Static fallback
        posterior = np.zeros(n_points)
        for i, model in enumerate(self.static_models):
            posterior[i] = norm.pdf(metric_value, model['mean'], model['std'])
        return posterior
    
    # OPTIMIZATION 1: Get top-K candidates from static model first
    static_scores = np.array([
        norm.pdf(metric_value, model['mean'], model['std'])
        for model in self.static_models
    ])
    top_k_candidates = np.argsort(static_scores)[-top_k:]  # Top K indices
    
    # OPTIMIZATION 2: Only enumerate paths to top-K candidates
    posterior = np.zeros(n_points)
    
    for curr_loc_idx in top_k_candidates:
        curr_loc = curr_loc_idx + 1  # Convert to 1-indexed
        # ... rest of path enumeration ...
        # (same as before but only for top-K candidates)
    
    return posterior


IMPLEMENTATION: Multiprocessing Evaluation
-------------------------------------------
Add to Evaluator.evaluate_transition():

from multiprocessing import Pool
import os

def _evaluate_single_sample(args):
    """Helper function for parallel processing"""
    idx, metric_value, previous_values, model = args
    posterior = model.predict(metric_value, previous_values=previous_values)
    return np.argmax(posterior) + 1

@staticmethod
def evaluate_transition_parallel(model, metric_values, true_locations, 
                                 test_indices, grid_positions=None, n_workers=None):
    if n_workers is None:
        n_workers = os.cpu_count()
    
    history_length = getattr(model, 'history_length', 1)
    valid_test_indices = [idx for idx in test_indices if idx >= history_length]
    
    # Prepare arguments for parallel processing
    args_list = []
    for idx in valid_test_indices:
        previous_values = [metric_values[idx - h] 
                          for h in range(history_length, 0, -1)]
        args_list.append((idx, metric_values[idx], previous_values, model))
    
    # Parallel prediction
    with Pool(processes=n_workers) as pool:
        predictions = pool.map(_evaluate_single_sample, args_list)
    
    # Compute metrics (same as before)
    predictions = np.array(predictions)
    true_labels = np.array([true_locations[idx] for idx in valid_test_indices])
    accuracy = np.mean(predictions == true_labels) * 100
    # ... rest of metrics ...


BENCHMARKING TARGETS:
=

After implementing optimizations, target performance:

Grid Size | Current Time | Target Time | Optimizations Needed
----------|--------------|-------------|---------------------
10x10     |    ~700s     |    ~70s     | Top-K + Adaptive h
15x15     |   ~2500s     |   ~200s     | + Hierarchical + Parallel
20x20     |   ~7000s     |   ~400s     | + All optimizations

These targets are achievable with Priority 1 + 2 optimizations.


TESTING STRATEGY:
=

1. Implement optimizations incrementally
2. For each optimization, run on 3x3 grid to verify accuracy unchanged
3. Measure speedup on 5x5, 10x10 grids
4. Document accuracy vs speed tradeoffs
5. Choose optimal configuration for your thesis

Validation metrics:
  - Accuracy should stay within ±1% of original
  - MAE should stay within ±0.1m of original
  - Speedup should be measurable and reproducible
