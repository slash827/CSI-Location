================================================================================
QUESTION 1: Data Leakage in Train/Test Split
================================================================================

Q: Check if the current train vs test split is not causing data leakage.
   How can we even make sure there is no data leakage in such scenario of random walking?

ANSWER: The current implementation HAS POTENTIAL DATA LEAKAGE issues. Here's the analysis:

CURRENT SPLITTING STRATEGY (localization_pipeline.py, lines 87-118):
-------------------------------------------------------------------
1. Static split: Random 80/20 split of ALL samples
   - train_indices, test_indices = random shuffle → split
   
2. Transition split: Random 80/20 split of samples with idx >= max_history
   - Excludes first few samples (no history available)
   - But otherwise RANDOM shuffle

WHY THIS IS PROBLEMATIC (DATA LEAKAGE):
---------------------------------------
In a random walk, consecutive samples are highly correlated:
- Sample t and sample t+1 are from adjacent grid points (or same point)
- RSS values change smoothly along the trajectory
- If sample t is in training and t+1 is in test, the model can "memorize"
  the trajectory pattern

Example of leakage:
  Train: [..., sample 100, sample 102, sample 104, ...]
  Test:  [..., sample 101, sample 103, sample 105, ...]
  → Test samples are "sandwiched" between train samples!
  → Model can interpolate/extrapolate the walk pattern

This means:
✗ Test performance is OVERESTIMATED
✗ Real-world deployment will perform WORSE
✗ We're not truly testing generalization


HOW TO FIX - 3 STRATEGIES:
================================================================================

STRATEGY 1: TEMPORAL/SEQUENTIAL SPLITTING (RECOMMENDED)
--------------------------------------------------------
Split by TIME, not by random indices:

train_cutoff = int(n_samples * 0.8)
train_indices = np.arange(0, train_cutoff)
test_indices = np.arange(train_cutoff, n_samples)

Advantages:
  ✓ No temporal leakage - test is strictly "future" data
  ✓ Simulates real deployment (train on past, predict future)
  ✓ More realistic performance estimate
  
Disadvantages:
  ✗ If random walk visits different regions over time, train/test might
    have different spatial distributions
  ✗ Less data in test set for some grid points

Implementation:
  Modify DataSplitter.split_static() and split_transition()
  Replace np.random.shuffle() with sequential split


STRATEGY 2: WALK-BASED SPLITTING (BEST FOR RANDOM WALK)
--------------------------------------------------------
Generate multiple SEPARATE random walks, assign entire walks to train/test:

walks = generate_multiple_walks(n_walks=5, steps_per_walk=2000)
train_walks = walks[0:4]  # 80% of walks
test_walks = walks[4:5]   # 20% of walks

Advantages:
  ✓ NO leakage - completely independent walks
  ✓ True test of generalization to new trajectories
  ✓ Best simulates real-world scenario (new user walking)
  
Disadvantages:
  ✗ Requires changing data generation (MATLAB script)
  ✗ Need to ensure walks cover all grid points adequately
  ✗ More complex data management

Implementation:
  1. Modify generate_simulation_data.m to create multiple walks
  2. Save walk IDs with each sample
  3. Split by walk ID instead of sample index


STRATEGY 3: SPATIAL BLOCK SPLITTING (ALTERNATIVE)
--------------------------------------------------
Split grid into spatial regions, ensure train/test are separated:

# Example for 10x10 grid:
# Train: rows 0-7 (80 points)
# Test:  rows 8-9 (20 points)

Advantages:
  ✓ No temporal leakage
  ✓ Tests spatial generalization
  
Disadvantages:
  ✗ Uneven distribution (some points never seen in test)
  ✗ Not representative of random walk scenario
  ✗ Performance depends heavily on which region is held out


RECOMMENDED APPROACH FOR YOUR CASE:
================================================================================

Given that you have RANDOM WALK data, I recommend STRATEGY 1 (Temporal Split)
as a quick fix, with STRATEGY 2 (Walk-based) as the ideal long-term solution.

IMPLEMENTATION GUIDE:

Option A - Quick Fix (Temporal Split):
---------------------------------------
In localization_pipeline.py, modify DataSplitter:

class DataSplitter:
    def __init__(self, test_ratio=0.2, random_seed=42, split_method='temporal'):
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.split_method = split_method
    
    def split_static(self, n_samples):
        if self.split_method == 'temporal':
            # Sequential split - train on early trajectory, test on later
            train_cutoff = int(n_samples * (1 - self.test_ratio))
            train_indices = np.arange(0, train_cutoff)
            test_indices = np.arange(train_cutoff, n_samples)
        else:
            # Original random split (for comparison)
            np.random.seed(self.random_seed)
            all_indices = np.arange(n_samples)
            np.random.shuffle(all_indices)
            n_test = int(n_samples * self.test_ratio)
            test_indices = all_indices[:n_test]
            train_indices = all_indices[n_test:]
        
        return train_indices, test_indices

Add command-line argument:
  parser.add_argument('--split-method', choices=['random', 'temporal'], 
                      default='temporal', help='Train/test split strategy')


Option B - Ideal Fix (Multiple Walks):
---------------------------------------
1. Modify generate_simulation_data.m:
   - Generate 5 separate random walks (2000 steps each = 10000 total)
   - Save walk_id for each sample
   
2. Modify DataSplitter to use walk_id:
   def split_by_walk(self, walk_ids, n_walks=5):
       np.random.seed(self.random_seed)
       all_walk_ids = np.arange(n_walks)
       np.random.shuffle(all_walk_ids)
       
       n_test_walks = max(1, int(n_walks * self.test_ratio))
       test_walk_ids = all_walk_ids[:n_test_walks]
       
       test_indices = np.where(np.isin(walk_ids, test_walk_ids))[0]
       train_indices = np.where(~np.isin(walk_ids, test_walk_ids))[0]
       
       return train_indices, test_indices


HOW TO VERIFY NO LEAKAGE:
================================================================================

After implementing the fix, verify with these checks:

1. Temporal Check:
   max_train_idx = max(train_indices)
   min_test_idx = min(test_indices)
   assert max_train_idx < min_test_idx, "Train/test overlap in time!"

2. Autocorrelation Check:
   # Check if nearby samples are in different sets
   for idx in test_indices:
       if (idx-1) in train_indices or (idx+1) in train_indices:
           print(f"WARNING: Test sample {idx} has neighbor in train set!")

3. Performance Comparison:
   # Temporal split should show LOWER accuracy than random split
   # If temporal split performs similarly → either:
   #   a) No leakage was present (good), or
   #   b) Model truly generalizes well (good)


EXPECTED IMPACT:
================================================================================

After fixing leakage, you should expect:
  - Static accuracy: SIMILAR or slightly lower (less memorization)
  - Transition accuracy: SIMILAR (relies on local deltas, less affected)
  - MAE: Might INCREASE slightly (harder test set)

If you see LARGE drops (>10% accuracy), it indicates:
  → Previous results had significant leakage
  → Real-world performance would be closer to new (lower) numbers


================================================================================
QUESTION 2: Ordered Walking vs Random Walking
================================================================================

Q: Maybe instead of random walking, we add some ordered walking 
   (scanning rows then scanning columns etc)

ANSWER: This is an excellent idea for COMPLEMENTING (not replacing) random walks!

BENEFITS OF ORDERED/STRUCTURED WALKING:
----------------------------------------

1. SYSTEMATIC COVERAGE:
   - Guarantees visiting all grid points
   - Ensures balanced data distribution
   - Easier to analyze and debug

2. REALISTIC SCENARIOS:
   - Simulates scanning/monitoring patterns
   - Models surveillance or inspection routes
   - Matches real IoT deployment patterns

3. CLEANER EVALUATION:
   - Can use leave-one-scan-out cross-validation
   - Each scan is independent → no leakage!
   - Better statistical properties


RECOMMENDED WALKING PATTERNS:
================================================================================

Pattern 1: ROW-BY-ROW SCANNING
-------------------------------
for row in range(grid_size):
    if row % 2 == 0:
        # Left to right
        for col in range(grid_size):
            visit(row, col)
    else:
        # Right to left (snake pattern)
        for col in range(grid_size-1, -1, -1):
            visit(row, col)

Benefits:
  ✓ Covers entire grid systematically
  ✓ Continuous path (valid transitions)
  ✓ Can repeat multiple times for more samples

Pattern 2: COLUMN-BY-COLUMN SCANNING
-------------------------------------
Similar to row scanning but vertical direction


Pattern 3: SPIRAL PATTERN
--------------------------
Start from center/corner, spiral outward
Benefits:
  ✓ Different transition patterns
  ✓ Tests edge vs center behavior


Pattern 4: LAWNMOWER PATTERN
-----------------------------
Like row scanning but with turns at ends


PROPOSED HYBRID APPROACH:
================================================================================

Generate BOTH random AND ordered walks:

Data Generation Strategy:
  1. Random Walks (50%): Current approach
     - Tests generalization to unpredictable movement
     - Models casual user movement
     
  2. Ordered Scans (50%): Multiple scanning patterns
     - Row scans (left-to-right, right-to-left)
     - Column scans (top-to-bottom, bottom-to-top)
     - Spiral scans
     - Diagonal scans

Implementation in MATLAB (generate_simulation_data.m):

% Generate multiple walking patterns
patterns = {};

% Random walk (existing)
patterns{1} = generate_random_walk(n_steps/4);

% Row scan (snake pattern)
patterns{2} = generate_row_scan(grid_size);

% Column scan
patterns{3} = generate_column_scan(grid_size);

% Spiral scan
patterns{4} = generate_spiral_scan(grid_size);

% Concatenate all patterns
walk_path = [patterns{:}];


EVALUATION STRATEGY WITH MULTIPLE PATTERNS:
--------------------------------------------

1. PATTERN-SPECIFIC EVALUATION:
   Test on same pattern as training
   → Measures how well model learns that specific pattern

2. CROSS-PATTERN EVALUATION:
   Train on ordered scans, test on random walks
   → Measures true generalization!

3. MIXED EVALUATION:
   Train/test on mixture of all patterns
   → Measures overall robustness


IMPLEMENTATION STEPS:
================================================================================

Step 1: Add pattern generation to MATLAB
-----------------------------------------
Add new functions to generate_simulation_data.m:

function path = generate_row_scan(grid_size)
    path = [];
    for row = 1:grid_size
        if mod(row, 2) == 1
            cols = 1:grid_size;
        else
            cols = grid_size:-1:1;
        end
        for col = cols
            path = [path; row, col];
        end
    end
end

Step 2: Update config.json
---------------------------
Add walk pattern specification:

{
  "walk_patterns": {
    "random": {"enabled": true, "weight": 0.5},
    "row_scan": {"enabled": true, "weight": 0.2},
    "col_scan": {"enabled": true, "weight": 0.2},
    "spiral": {"enabled": true, "weight": 0.1}
  }
}

Step 3: Save pattern labels
----------------------------
Save which pattern generated each sample:

save(output_file, 'metrics', 'walk_path', 'pattern_labels', 'config')

Step 4: Update Python pipeline
-------------------------------
Add pattern-aware splitting:

def split_by_pattern(self, pattern_labels, test_patterns):
    """Split by keeping certain patterns for testing"""
    test_mask = np.isin(pattern_labels, test_patterns)
    test_indices = np.where(test_mask)[0]
    train_indices = np.where(~test_mask)[0]
    return train_indices, test_indices


EXPECTED RESULTS:
================================================================================

With ordered patterns, you should see:

1. HIGHER ACCURACY on same-pattern evaluation
   - Ordered patterns are more predictable
   - Transition models can learn systematic movements

2. CLEARER PERFORMANCE TRENDS
   - Better understanding of when/why model fails
   - Can identify grid regions with poor coverage

3. MORE RELIABLE EVALUATION
   - No temporal leakage with proper pattern splitting
   - Statistical significance easier to assess


RECOMMENDATION:
================================================================================

Implement BOTH fixes together:

1. SHORT TERM (This week):
   - Switch to temporal splitting (Option A above)
   - Re-run all experiments to get realistic performance numbers
   - Document the difference in results

2. MEDIUM TERM (Next week):
   - Add ordered walking patterns to MATLAB generator
   - Generate new datasets with mixed patterns
   - Implement pattern-aware splitting

3. LONG TERM (For paper/thesis):
   - Compare performance across different patterns
   - Analyze which patterns help transition models most
   - Create comprehensive evaluation protocol

This gives you:
  ✓ Immediate fix for data leakage
  ✓ Better experimental design
  ✓ Stronger scientific conclusions
  ✓ More publishable results
