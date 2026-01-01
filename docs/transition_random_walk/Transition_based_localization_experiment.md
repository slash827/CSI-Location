# Action Plan: Transition-Based Localization Experiment

## Background & Motivation

The current approach uses **static RSS/SINR values** at each grid point for localization. However, this suffers from high variance (~4-5 dB) due to small-scale fading, causing significant overlap between distributions of different locations.

**New approach**: Use **RSS transitions (deltas)** between consecutive grid points instead of absolute values. The hypothesis is that transitions provide better separability because:
- When a UE moves from LOS to NLOS (or vice versa), all users experience similar effects (drop/rise)
- Transitions reduce the impact of small-scale fading variance
- The delta between two measurements may be more discriminative than the absolute values

## Research Question

Does using RSS **transitions (deltas)** provide better separability and classification accuracy compared to using **absolute RSS values**?

---

## Experiment Design: 3×3 Grid Proof-of-Concept

### Step 1: Generate Dataset (if not already available)
- Use QuaDRiGa to generate CSI data for a 3×3 grid
- Grid spacing: 2 meters between points
- Generate trajectories where UE moves between adjacent grid points
- Ensure temporal correlation in channel samples (use track-based generation)
- Target: ~2,500-5,000 samples per grid point

### Step 2: Extract Static RSS Distributions
For each of the 9 grid points:
- Extract all RSS measurements when UE is stationary at that point
- Calculate mean (μ) and standard deviation (σ) for each point
- Plot the 9 Gaussian distributions on the same graph
- **Visualize the overlap** between distributions

**Analysis questions:**
- What is the typical variance at each point?
- How much overlap exists between neighboring points?
- Can we reliably distinguish between points based on a single RSS measurement?

### Step 3: Extract Transition (Delta) Distributions
For each pair of **adjacent** grid points (i → j):
- Extract RSS measurements: RSS_before (at point i) and RSS_after (at point j)
- Calculate delta: Δ_RSS = RSS_after - RSS_before
- Calculate mean (μ_delta) and standard deviation (σ_delta) for each transition
- Note: In a 3×3 grid, there are:
  - 6 horizontal transitions (3 rows × 2 transitions per row)
  - 6 vertical transitions (3 columns × 2 transitions per column)
  - Total: 12 unique transition types

**Analysis questions:**
- Are delta distributions more separated than absolute RSS distributions?
- Do opposite transitions show clear negative correlation? (e.g., transition 1→2 vs 2→1)
- Is the variance in deltas smaller than variance in absolute values?

### Step 4: Statistical Analysis & Visualization

#### A. Static RSS Approach
- Plot all 9 distributions on one graph
- Mark areas of overlap
- For a test RSS value, show which distribution(s) it could plausibly belong to

#### B. Transition-Based Approach
- Plot all 12 transition distributions
- For a test transition (RSS_before, RSS_after), show which transition type it most likely represents
- Calculate the **separability metric** between distributions (e.g., Bhattacharyya distance, KL divergence)

#### C. Comparison
Create a table comparing:
| Metric | Static RSS | Transitions |
|--------|-----------|-------------|
| Average σ (std) | ? | ? |
| Average overlap between neighbors | ? | ? |
| Separability score | ? | ? |

### Step 5: Classification Method Investigation

**Consult AI tools (Gemini/ChatGPT) with this prompt:**

> "I have a classification problem. I am given:
> 1. A single measured value (or a pair of values)
> 2. Multiple known Gaussian distributions, each representing a different class
> 
> What are the 3 main statistical methods to determine which distribution most likely generated the observed value(s)?"

**Then ask the same for transitions:**

> "Now suppose instead of a single value, I have:
> 1. A starting value RSS_before
> 2. An ending value RSS_after  
> 3. Multiple known Gaussian distributions for deltas (RSS_after - RSS_before)
> 
> What are the main methods to classify which transition occurred?"

**Action**: Send the AI responses to Dudi via email for his feedback on which methods are most appropriate.

### Step 6: Implement & Compare Classification Methods

Implement the recommended methods for both approaches:
- **Method 1**: Nearest mean (simple baseline)
- **Method 2**: Maximum likelihood / probability density
- **Method 3**: Bayesian classification with priors
- **(Others as suggested by AI/Dudi)**

For each method, calculate:
- Classification accuracy on test set
- Confusion matrix
- Mean absolute error in meters

---

## Expected Outputs for Next Meeting

1. **Visualization of distributions**:
   - 9 static RSS distributions (one graph)
   - 12 transition delta distributions (one graph)
   - Clear marking of overlaps

2. **Statistical comparison table**:
   - Variance comparison
   - Separability metrics
   - Overlap analysis

3. **Classification results**:
   - Accuracy comparison: static RSS vs transitions
   - Which statistical method works best?

4. **AI consultation summary**:
   - Recommended statistical methods
   - Dudi's feedback on methods

5. **Preliminary conclusions**:
   - Does the transition approach provide better separability?
   - Is the improvement significant enough to pursue?

---

## Implementation Notes

### Data Structure Considerations

**For static approach:**
```python
# For each grid point i:
static_data[i] = {
    'rss_samples': [...],  # All RSS measurements at point i
    'mean': μ_i,
    'std': σ_i
}
```

**For transition approach:**
```python
# For each transition from point i to point j:
transition_data[(i,j)] = {
    'delta_samples': [...],  # All (RSS_j - RSS_i) measurements
    'mean_delta': μ_delta,
    'std_delta': σ_delta
}
```

### Complexity Considerations

- **Static approach**: O(n) - compare against n grid points
- **Single transition approach**: O(n²) - compare against all possible transitions
- **Multi-transition approach**: O(n^k) where k = number of transitions
  - This grows exponentially, so we'll need heuristics later
  - For POC, focus on single transition first

### Future Extensions (Beyond POC)

1. **Trajectory heuristics**: Assume UE continues in same direction
2. **Multiple transitions**: How many transitions needed for sufficient accuracy?
3. **Hybrid approach**: Combine current RSS + transition delta
4. **Scale to larger grids**: Test on 10×10, 20×20 grids
5. **Different scenarios**: Indoor vs outdoor, different frequencies (3 GHz vs 3.5 GHz)

---

## Timeline

- **Week 1**: Data generation + static distribution analysis
- **Week 2**: Transition extraction + comparison analysis  
- **Week 3**: Classification implementation + results
- **Week 4**: Prepare presentation for next meeting (Sunday or Wednesday)

---

## Questions to Explore

1. How does the separability scale with grid size?
2. What's the minimum number of transitions needed for accurate localization?
3. Can we develop heuristics to reduce computational complexity?
4. How does this approach compare to ML-based methods (CNN, XGBoost)?
5. Is there an optimal trade-off between number of transitions and accuracy?