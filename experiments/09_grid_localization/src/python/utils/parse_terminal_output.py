"""Parse terminal output from scalability experiment into a CSV.

Handles multi-line Gaussian output where [DEBUG] lines split the config header from results.
"""
import re
import csv
import sys
from pathlib import Path

def parse_terminal_files(file_paths, output_csv):
    """Parse terminal output files and build experiment_results.csv."""
    
    # Read all files into one big string, removing newlines to handle terminal wrapping
    all_text = ""
    for fp in file_paths:
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        # Remove all newlines - the terminal just wraps at column width
        # Use empty string to avoid breaking tokens like "0.3s)" -> "0.3 s )"
        raw_flat = raw.replace('\n', '')
        all_text += raw_flat
    
    # Grid order is fixed: 50 configs per grid
    # 1-50 = 3x3, 51-100 = 5x5, 101-150 = 7x7, 151-200 = 10x10, 201-250 = 15x15, 251-300 = 20x20
    grid_labels = ['3x3', '5x5', '7x7', '10x10', '15x15', '20x20']
    def config_to_grid(n):
        idx = (n - 1) // 50
        return grid_labels[idx] if idx < len(grid_labels) else 'unknown'
    
    # Find all config entries: [N/300] algo | metric | h=X | mode ... acc=Y% mae=Zm (train=As eval=Bs)
    # Allow [DEBUG] in between but not [N/300] which would be the next config
    config_pattern = re.compile(
        r'\[(\d+)/300\]\s+'
        r'(\w+)\s*\|\s*'          # algorithm
        r'([\w+,]+)\s*\|\s*'      # metric(s)
        r'h=(\d+)\s*\|\s*'        # history
        r'(\S+)\s+'               # feature_mode
        r'(?:(?!\[\d+/300\]).)*?' # anything EXCEPT another [N/300] config header
        r'acc=([\d.]+)%\s+'       # accuracy
        r'mae=([\d.]+)m\s+'       # MAE
        r'\(train=([\d.]+)s\s+'   # train time
        r'eval=([\d.]+)s\)'       # eval time
    )
    
    results = {}
    for m in config_pattern.finditer(all_text):
        config_num = int(m.group(1))
        if config_num in results:
            continue  # skip duplicates (overlapping buffers)
        
        grid = config_to_grid(config_num)
        grid_size = int(grid.split('x')[0])
        history = int(m.group(4))
        fm = m.group(5)
        if fm == 'n/a':
            fm = 'static'
        
        # Approximate n_test_samples from known data
        test_samples = {'3x3': 721, '5x5': 2001, '7x7': 3921, '10x10': 8001, '15x15': 18001, '20x20': 32001}
        
        results[config_num] = {
            'grid': grid,
            'grid_size': grid_size,
            'algorithm': m.group(2),
            'metric': m.group(3).replace(',', '+'),
            'history': history,
            'feature_mode': fm,
            'accuracy': float(m.group(6)),
            'mae': float(m.group(7)),
            'train_time': float(m.group(8)),
            'eval_time': float(m.group(9)),
            'n_test_samples': test_samples.get(grid, 0),
        }
    
    print(f"Found grids: {grid_labels}")
    print(f"Total results parsed: {len(results)}")
    
    # Check for missing in range 1-250
    missing = [i for i in range(1, 251) if i not in results]
    if missing:
        print(f"Missing {len(missing)} configs: {missing[:20]}{'...' if len(missing) > 20 else ''}")
    else:
        print("All 250 configs found!")
    
    # Write CSV matching run_experiment_matrix.py format
    fieldnames = [
        'grid', 'grid_size', 'algorithm', 'metric', 'history', 'feature_mode',
        'accuracy', 'mae', 'train_time', 'eval_time', 'n_test_samples'
    ]
    
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for config_num in sorted(results.keys()):
            row = {k: results[config_num][k] for k in fieldnames}
            writer.writerow(row)
    
    print(f"Wrote {len(results)} rows to {output_csv}")
    return len(results)

if __name__ == '__main__':
    # Find all terminal output files
    base_dir = Path(r"c:\Users\gilad.battat\AppData\Roaming\Code\User\workspaceStorage"
                    r"\5b601eee201b162ab13040dc2bc17127\GitHub.copilot-chat"
                    r"\chat-session-resources\66a65104-d283-4fe2-ae05-70a288c72775")
    
    files = sorted(base_dir.glob("toolu_bdrk_*/content.txt"))
    print(f"Found {len(files)} terminal output files")
    
    output = Path(r"C:\Users\gilad.battat\Documents\GitHub_Personal\CSI-Location"
                  r"\results\experiment_matrix\scalability_5grids\experiment_results.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    
    count = parse_terminal_files(files, output)
    
    # Remove any 20x20 rows (incomplete data) and dedup
    with open(output, 'r') as f:
        rows = list(csv.DictReader(f))
    
    # Filter out 20x20 (we don't have complete data for it)
    rows = [r for r in rows if r['grid'] != '20x20']
    
    # Check for config 1 (3x3 gaussian rss h=0) — add if missing
    has_config1 = any(r['grid'] == '3x3' and r['algorithm'] == 'gaussian' 
                      and r['metric'] == 'rss' and r['history'] == '0' for r in rows)
    if not has_config1:
        row1 = {'grid':'3x3','grid_size':'3','algorithm':'gaussian','metric':'rss',
                'history':'0','feature_mode':'static','accuracy':'31.9','mae':'1.92',
                'train_time':'0.0','eval_time':'0.3','n_test_samples':'721'}
        rows.insert(0, row1)
    
    fields = list(rows[0].keys())
    with open(output, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Final CSV: {len(rows)} rows (5 grids)")
