# Claude Code Prompt: Project Audit & Next Steps

## 🎯 MISSION

You are working on a **5G CSI-based localization research project** for a Master's student. Your tasks:

1. **AUDIT** the existing codebase to understand what's implemented
2. **IDENTIFY GAPS** between what exists and what's needed
3. **CREATE A ROADMAP** with concrete tasks
4. **IMPLEMENT** missing components systematically

---

## 📊 PROJECT CONTEXT

### Research Goal:
**Improve indoor localization using transition-based CSI fingerprinting**

### Key Insight:
- **Static approach**: Look at RSS/CSI at each location → overlapping distributions → poor accuracy
- **Transition approach**: Look at changes in RSS/CSI between locations → more unique → better accuracy

### The Contribution:
> "Transitions improve localization **regardless of which prediction method** you use"

**NOT:** "Algorithm X achieves Y% accuracy"  
**YES:** "Using transitions improves ANY algorithm"

---

## ✅ WHAT'S BEEN DONE (Student's Progress)

### 1. Heterogeneous Environment - DONE ✅
```
- AreaGenerator.m: Voronoi-based area generation
- GeometryUtils.m: Helper for Voronoi cell assignment
- Heterogeneous QuaDRiGa simulation working
- Multiple scenarios (shopping, residential, office, park)
```

### 2. Transition-Based Models - DONE ✅
```
- Implemented history tracking (0, 1, 2, 3 steps back)
- Tested with multiple metrics: RSS, SINR, Time Advance
- Confirmed: More history → better results (gradual improvement)
```

### 3. Experiments Run - DONE ✅
```
- Tested on multiple grid sizes (3×3, 7×7, 15×15)
- Compared: Static vs Transition (1-step, 2-step, 3-step)
- Multiple ML algorithms tested
```

---

## ⚠️ CURRENT PROBLEMS

### Problem 1: Curse of Dimensionality 🔥
```
Scenario: 15×15 grid = 225 locations
Task: Classification (predict which of 225 classes)
Result: OUT OF MEMORY crash

Why:
- With 3-step history: 225^3 = 11,390,625 possible states!
- Feature explosion with multiple metrics
- ML models can't handle this
```

### Problem 2: Regression Works but Not Preferred
```
Student tried: Regression (distance + angle from BS)
Result: Works, doesn't crash
Advisor (Dudi): "Less interested in this solution"

Why advisor doesn't like it:
- Less aligned with transition-based methodology
- Harder to interpret
- Not the main contribution
```

---

## 🎯 ADVISOR FEEDBACK (Feb 8 Meeting)

### Critical Points from Advisors:

**1. Focus = Methodology, NOT algorithm** (Sarit)
> "What matters is that transitions help, not which ML algorithm you use"

**2. Heterogeneous environment is key** (Dudi)
> "More heterogeneous → more unique transitions → better results"

**3. Scalability matters** (Dudi)
> "Good: Your approach is polynomial, not exponential"

**4. Target accuracy** (Dudi)
> "Industry standard: 20-30 cm outdoor. You're at ~3m. Need to improve."

**5. Upcoming presentation to CEVA**
> "Need to show system demo soon"

---

## 🔍 YOUR TASKS

### TASK 1: PROJECT AUDIT (Critical!)

**Scan the entire project and create a detailed inventory:**

```markdown
# Project Inventory Template

## 1. Data Generation (MATLAB)
- [ ] File: experiments/heterogeneous_simulation.m
  - Status: EXISTS / MISSING / PARTIAL
  - What it does: ...
  - Issues: ...

- [ ] File: utils/AreaGenerator.m
  - Status: ...
  - What it does: ...

- [ ] File: utils/GeometryUtils.m
  - Status: ...
  - What it does: ...

- [ ] QuaDRiGa integration
  - Voronoi scenarios: YES/NO
  - Multiple BS support: YES/NO
  - Metrics extracted: [list]

## 2. ML Pipeline (Python)
- [ ] File: ml_training/localization_pipeline.py
  - Status: ...
  - Models implemented: [list]
  - Transition support: YES/NO/PARTIAL

- [ ] File: ml_training/transition_models.py
  - Status: ...
  - History length support: [0, 1, 2, 3, ...]
  - Memory optimization: YES/NO

- [ ] Data loading
  - Heterogeneous data support: YES/NO
  - Efficient loading: YES/NO

## 3. Experiments & Results
- [ ] Grid sizes tested: [3×3, 7×7, 15×15, ...]
- [ ] Algorithms tested: [list]
- [ ] Metrics used: [RSS, SINR, TA, CQI, ...]
- [ ] Best results achieved:
  - Grid: ...
  - Algorithm: ...
  - History: ...
  - Accuracy/MAE: ...

## 4. Visualization
- [ ] Voronoi area plots: YES/NO
- [ ] Results comparison plots: YES/NO
- [ ] Confusion matrices: YES/NO

## 5. Documentation
- [ ] README.md: YES/NO
- [ ] Experiment logs: YES/NO
- [ ] Code comments: GOOD/PARTIAL/MISSING
```

**INSTRUCTIONS:**
1. Scan ALL files in the project
2. Fill out this inventory completely
3. Note what exists, what's partial, what's missing
4. Identify code quality issues
5. Flag potential bugs or inefficiencies

---

### TASK 2: SOLVE DIMENSIONALITY PROBLEM 🔥

**The Challenge:**
```
15×15 grid with 3-step history = memory explosion
Need: Scalable solution that maintains transition-based approach
```

**Proposed Solutions (evaluate & implement best):**

#### Option A: Smart State Aggregation ⭐⭐⭐⭐⭐
```python
# Instead of tracking exact 3-step history:
# Track FEATURES of the history

class TransitionFeatureExtractor:
    """
    Instead of: [loc_t-3, loc_t-2, loc_t-1, loc_t]
    Use: Transition features from history
    """
    
    def extract_features(self, rss_history, sinr_history, location_history):
        """
        From 3-step history, extract:
        - RSS deltas: [Δ1, Δ2, Δ3]
        - SINR deltas: [Δ1, Δ2, Δ3]
        - Movement direction (if locations known)
        - Cumulative change
        - Trend (increasing/decreasing)
        
        Result: Fixed-size feature vector (e.g., 20 features)
        instead of exponential state space!
        """
        features = []
        
        # RSS changes
        rss_deltas = np.diff(rss_history)
        features.extend(rss_deltas)
        
        # SINR changes
        sinr_deltas = np.diff(sinr_history)
        features.extend(sinr_deltas)
        
        # Cumulative change
        features.append(rss_history[-1] - rss_history[0])
        
        # Trend (linear fit slope)
        trend = np.polyfit(range(len(rss_history)), rss_history, 1)[0]
        features.append(trend)
        
        return np.array(features)

# Now classification is: features → location
# NOT: (loc1, loc2, loc3, rss) → location
```

**Why this works:**
- Fixed feature size regardless of grid size!
- Still captures transition information
- Scalable to any grid size
- Aligns with "transitions matter" philosophy

---

#### Option B: Hierarchical Classification ⭐⭐⭐⭐
```python
class HierarchicalLocalization:
    """
    Instead of predicting 1 of 225 locations directly:
    1. Predict rough area (e.g., 5×5 regions) → 9 classes
    2. Within that area, predict fine location → 5×5 classes
    
    Result: 9 + 25 = 34 classes instead of 225!
    """
    
    def __init__(self, grid_size=15, region_size=5):
        self.coarse_model = RandomForest()  # 9 regions
        self.fine_models = {}  # One model per region (25 locs each)
    
    def predict(self, features, history):
        # Step 1: Coarse prediction
        region = self.coarse_model.predict(features)
        
        # Step 2: Fine prediction within region
        fine_model = self.fine_models[region]
        local_location = fine_model.predict(features)
        
        # Combine
        global_location = self.region_to_global(region, local_location)
        return global_location
```

**Why this works:**
- Divide and conquer
- Each classifier has manageable number of classes
- Can still use transitions at both levels

---

#### Option C: Embedding-Based Approach ⭐⭐⭐
```python
class TransitionEmbedding:
    """
    Learn a low-dimensional embedding of transitions
    Then classify in embedding space
    """
    
    def __init__(self, embedding_dim=32):
        self.encoder = nn.Sequential(
            nn.Linear(history_features, 128),
            nn.ReLU(),
            nn.Linear(128, embedding_dim)
        )
        self.classifier = nn.Linear(embedding_dim, num_locations)
    
    def forward(self, transition_features):
        # Compress to low-dim space
        embedding = self.encoder(transition_features)
        # Classify from embedding
        logits = self.classifier(embedding)
        return logits
```

---

#### Option D: Sequence Modeling (LSTM/Transformer) ⭐⭐⭐⭐
```python
class TransitionLSTM:
    """
    Treat history as a sequence
    Use LSTM to process it
    """
    
    def __init__(self):
        self.lstm = nn.LSTM(input_size=num_metrics, 
                           hidden_size=128, 
                           num_layers=2)
        self.classifier = nn.Linear(128, num_locations)
    
    def forward(self, sequence):
        # sequence: [seq_len, batch, features]
        # e.g., [4, 32, 3] for 3-step history, batch=32, 3 metrics
        
        output, (h_n, c_n) = self.lstm(sequence)
        # Use final hidden state
        logits = self.classifier(h_n[-1])
        return logits
```

**Why this works:**
- Designed for sequences
- Captures temporal patterns
- Scalable

---

**YOUR JOB:**
1. Evaluate which approach fits best
2. Implement it
3. Test on 15×15 grid
4. Compare to regression baseline
5. Show it scales without memory issues

---

### TASK 3: CREATE COMPREHENSIVE COMPARISON

**The Goal:**
> Prove that transitions help regardless of algorithm

**Experiment Design:**
```python
# Test matrix:
grid_sizes = [3, 7, 15]
metrics = ['rss', 'sinr', 'time_advance', 'rss+sinr', 'rss+sinr+ta']
history_lengths = [0, 1, 2, 3]  # 0 = static
algorithms = ['gaussian', 'random_forest', 'xgboost', 'neural_net']

# For EACH combination, record:
results = {
    'accuracy': ...,
    'mae': ...,
    'training_time': ...,
    'memory_usage': ...
}
```

**Expected Output:**
```
Table: Impact of Transition History

Algorithm    | Grid | Metric     | H=0  | H=1  | H=2  | H=3  | Improvement
-------------|------|------------|------|------|------|------|------------
Gaussian     | 7×7  | RSS        | 65%  | 71%  | 75%  | 78%  | +20%
Gaussian     | 7×7  | RSS+SINR   | 73%  | 79%  | 82%  | 84%  | +15%
RandomForest | 7×7  | RSS        | 71%  | 77%  | 81%  | 83%  | +17%
RandomForest | 7×7  | RSS+SINR   | 78%  | 84%  | 87%  | 89%  | +14%
...

Key Finding: ALL algorithms improve with history!
```

---

### TASK 4: OPTIMIZE FOR SCALABILITY

**Implement memory-efficient data structures:**

```python
class EfficientTransitionDataset:
    """
    Memory-efficient storage for transition data
    
    Problem: Storing all possible transitions = huge memory
    Solution: Generate on-the-fly during training
    """
    
    def __init__(self, trajectories, history_length=3):
        """
        trajectories: List of sequences
          Each sequence: [(location, rss, sinr, ta), ...]
        """
        self.trajectories = trajectories
        self.history_length = history_length
    
    def __getitem__(self, idx):
        """
        Generate transition sample on-demand
        Don't store all combinations!
        """
        # Pick random trajectory
        traj = random.choice(self.trajectories)
        
        # Pick random position with enough history
        if len(traj) <= self.history_length:
            return None
        
        t = random.randint(self.history_length, len(traj) - 1)
        
        # Extract history window
        history = traj[t - self.history_length : t + 1]
        
        # Convert to features
        features = self.history_to_features(history)
        label = history[-1]['location']
        
        return features, label
    
    def history_to_features(self, history):
        """
        Convert history to fixed-size feature vector
        This is key to avoiding dimensionality explosion!
        """
        # Extract metrics
        rss = [h['rss'] for h in history]
        sinr = [h['sinr'] for h in history]
        
        # Compute transitions
        features = []
        features.extend(np.diff(rss))  # RSS changes
        features.extend(np.diff(sinr))  # SINR changes
        features.append(rss[-1])  # Current RSS
        features.append(sinr[-1])  # Current SINR
        
        return np.array(features)
```

---

### TASK 5: VISUALIZATION & ANALYSIS

**Create comprehensive visualizations:**

```python
# 1. Transition Impact Plot
def plot_history_impact(results):
    """
    Show how accuracy improves with history length
    For multiple algorithms
    """
    fig, ax = plt.subplots()
    for algo in algorithms:
        history_lens = [0, 1, 2, 3]
        accs = [results[algo][h]['accuracy'] for h in history_lens]
        ax.plot(history_lens, accs, marker='o', label=algo)
    
    ax.set_xlabel('History Length')
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Impact of Transition History')
    ax.legend()
    ax.grid(True)

# 2. Scalability Plot
def plot_scalability(results):
    """
    Show how approach scales with grid size
    Memory usage, time, accuracy
    """
    pass

# 3. Confusion Matrix with Transitions
def plot_transition_confusion(predictions, labels, grid_size):
    """
    Show where transitions help most
    """
    pass

# 4. Feature Importance
def plot_transition_feature_importance(model):
    """
    Which transition features matter most?
    """
    pass
```

---

### TASK 6: CREATE TASK TRACKER

**Generate a `TASKS.md` file:**

```markdown
# Project Task Tracker

## Phase 1: Project Audit ✅/❌/🔄
- [ ] Scan all MATLAB files
- [ ] Scan all Python files  
- [ ] Document existing functionality
- [ ] Identify gaps
- [ ] Create inventory report

## Phase 2: Solve Dimensionality Problem 🔥
- [ ] Implement transition feature extraction
- [ ] Test on 15×15 grid
- [ ] Compare memory usage (old vs new)
- [ ] Verify accuracy maintained/improved
- [ ] Document approach

### Subtasks:
- [ ] Option A: Smart state aggregation
  - [ ] TransitionFeatureExtractor class
  - [ ] Unit tests
  - [ ] Benchmark on 7×7
  - [ ] Benchmark on 15×15
  
- [ ] Option B: Hierarchical classification
  - [ ] HierarchicalLocalization class
  - [ ] Coarse-level training
  - [ ] Fine-level training
  - [ ] Integration tests

- [ ] Option C: Embedding approach
  - [ ] Neural network architecture
  - [ ] Training pipeline
  - [ ] Evaluation

- [ ] Option D: LSTM/sequence model
  - [ ] Model architecture
  - [ ] Training pipeline
  - [ ] Evaluation

- [ ] Final decision: Which approach to use
- [ ] Implementation of chosen approach
- [ ] Full evaluation

## Phase 3: Comprehensive Comparison
- [ ] Design experiment matrix
- [ ] Implement all algorithm variations
  - [ ] Gaussian (static + transitions)
  - [ ] Random Forest (static + transitions)
  - [ ] XGBoost (static + transitions)
  - [ ] Neural Net (static + transitions)
- [ ] Run on multiple grid sizes
- [ ] Run on multiple metrics
- [ ] Collect results
- [ ] Statistical analysis
- [ ] Generate comparison tables

## Phase 4: Optimization
- [ ] Memory-efficient data loader
- [ ] Batch processing
- [ ] GPU acceleration (if applicable)
- [ ] Code profiling
- [ ] Performance tuning

## Phase 5: Visualization & Documentation
- [ ] History impact plots
- [ ] Scalability analysis
- [ ] Confusion matrices
- [ ] Feature importance
- [ ] Write methodology section
- [ ] Write results section
- [ ] Create presentation slides

## Phase 6: CEVA Presentation Prep
- [ ] Demo script
- [ ] Visualization dashboard
- [ ] Presentation slides
- [ ] Practice run
```

---

## 📝 DELIVERABLES

After completing your analysis, provide:

1. **PROJECT_AUDIT.md** - Complete inventory of what exists
2. **GAPS_ANALYSIS.md** - What's missing, what needs fixing
3. **TASKS.md** - Detailed task breakdown with checkboxes
4. **SOLUTION_PROPOSAL.md** - Recommended approach for dimensionality problem
5. **Implementation of chosen solution**
6. **Comprehensive experiments & results**

---

## 🚨 CRITICAL GUIDELINES

### 1. Don't Make Assumptions
```
❌ DON'T: "I assume the code does X"
✅ DO: Read the actual code, confirm what it does
```

### 2. Check Everything
```
❌ DON'T: Skip files that look unimportant
✅ DO: Scan every .m, .py, .md file in the project
```

### 3. Be Specific
```
❌ DON'T: "Some ML models are implemented"
✅ DO: "Random Forest implemented in ml_training/models.py lines 45-120.
       Supports history_length parameter. Missing: XGBoost, Neural Net."
```

### 4. Flag Issues
```
If you find:
- Dead code → mention it
- Bugs → flag them
- Inefficiencies → note them
- Missing error handling → point it out
```

### 5. Prioritize
```
Mark tasks as:
🔥 CRITICAL - Blocks progress (e.g., memory issue)
⚠️ IMPORTANT - Needed soon (e.g., additional algorithms)
💡 NICE TO HAVE - Can wait (e.g., advanced visualizations)
```

---

## 🎯 SUCCESS CRITERIA

You succeed when:

✅ **Complete audit** - Every file documented  
✅ **Dimensionality solved** - 15×15 grid works without crash  
✅ **Generality proven** - Multiple algorithms all improve with transitions  
✅ **Scalable** - Clear path to larger grids (20×20, 30×30)  
✅ **Documented** - Clear what exists, what's missing, what's next  
✅ **Ready for CEVA** - Can demo the system confidently

---

## 💬 EXAMPLE INTERACTION

**You:** "I've completed the project audit. Here's what I found:

**Data Generation (MATLAB):**
- ✅ `AreaGenerator.m` exists (utils/) - fully functional
- ✅ `GeometryUtils.m` exists (utils/) - fully functional  
- ✅ Heterogeneous simulation working
- ❌ No systematic way to vary BS positions
- ⚠️ Data export format inconsistent

**ML Pipeline (Python):**
- ✅ `localization_pipeline.py` exists
  - Gaussian model: supports history ✅
  - Random Forest: supports history ✅
  - XGBoost: NOT implemented ❌
- ⚠️ Memory issue on 15×15 grid with history
- ❌ No batch processing for large datasets

**Experiments:**
- ✅ Tested: 3×3, 7×7
- ⚠️ Tested: 15×15 (crashes with history)
- ✅ Clear improvement with history (all cases)

**Key Gap:** 
Need memory-efficient transition feature extraction for large grids.

**Recommendation:**
Implement Option A (Smart State Aggregation) because:
1. Simplest to implement
2. Aligns with research contribution
3. Provably scalable
4. Preserves transition information

Shall I proceed with implementation?"

---

## 🔄 ITERATIVE PROCESS

1. **Audit** → Report findings
2. **Discuss** → Agree on priorities with student
3. **Implement** → One task at a time
4. **Test** → Verify it works
5. **Document** → Update task tracker
6. **Repeat** → Next task

---

## 📚 ADDITIONAL CONTEXT

### File Structure (Expected):
```
project/
├── experiments/
│   ├── heterogeneous_simulation.m
│   └── ...
├── utils/
│   ├── AreaGenerator.m
│   ├── GeometryUtils.m
│   └── ...
├── ml_training/
│   ├── localization_pipeline.py
│   ├── data_loader.py
│   ├── models.py
│   └── ...
├── results/
│   ├── heterogeneous_data.mat
│   └── ...
└── docs/
    └── ...
```

### Technologies:
- MATLAB R2023+ (QuaDRiGa)
- Python 3.11+
- PyTorch / scikit-learn / XGBoost
- NumPy, Pandas, Matplotlib

---

## 🎓 REMEMBER

**The Research Contribution:**
> "Transitions improve localization regardless of the prediction algorithm"

**Not:**
> "Our specific algorithm achieves X% accuracy"

**Your job:**
Help prove this by implementing scalable, comprehensive experiments that show the generality of the transition-based approach.

---

END OF PROMPT

**Now: Start with the project audit. Report what you find.**
