"""Analyze scalability and core results for presentation findings."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCALE_CSV = ROOT / "results" / "experiment_matrix" / "scalability_5grids" / "experiment_results.csv"
CORE_CSV = ROOT / "results" / "experiment_matrix" / "core_7x7" / "experiment_results.csv"


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def analyze_scalability(rows):
    grids = sorted(set(r['grid'] for r in rows), key=lambda x: int(x.split('x')[0]))
    algos = sorted(set(r['algorithm'] for r in rows))
    metrics_list = sorted(set(r['metric'] for r in rows))

    print("=" * 70)
    print("SCALABILITY RESULTS (5 grids, 3 algorithms)")
    print("=" * 70)
    print(f"Grids: {grids}")
    print(f"Algorithms: {algos}")
    print(f"Metrics: {metrics_list}")
    print(f"Total configs: {len(rows)}")

    # Table 1: Best config per grid+algo (RSS+SINR, raw, h=3)
    print("\n--- Table 1: Best Accuracy (RSS+SINR, raw, h=3) ---")
    header = f"{'Grid':<8}"
    for a in algos:
        header += f" {a:<16}"
    print(header)
    print("-" * (8 + 17 * len(algos)))
    for g in grids:
        line = f"{g:<8}"
        for a in algos:
            match = [r for r in rows if r['grid'] == g and r['algorithm'] == a
                     and r['metric'] == 'RSS+SINR' and r['feature_mode'] == 'raw'
                     and r['history'] == '3']
            if match:
                line += f" {float(match[0]['accuracy']):>6.1f}% {float(match[0]['mae']):>5.2f}m"
            else:
                line += f" {'N/A':>15}"
        print(line)

    # Table 2: Transition impact h=0 vs h=3
    print("\n--- Table 2: Transition Impact (RSS+SINR, h=0 -> h=3) ---")
    hdr = f"{'Grid':<8} {'Algorithm':<15} {'h=0 Acc':>8} {'h=3 Acc':>8} {'Gain':>8} {'h=0 MAE':>8} {'h=3 MAE':>8} {'MAE Impr':>9}"
    print(hdr)
    print("-" * 80)
    for g in grids:
        for a in algos:
            h0 = [r for r in rows if r['grid'] == g and r['algorithm'] == a
                  and r['metric'] == 'RSS+SINR' and r['history'] == '0']
            h3 = [r for r in rows if r['grid'] == g and r['algorithm'] == a
                  and r['metric'] == 'RSS+SINR' and r['feature_mode'] == 'raw'
                  and r['history'] == '3']
            if h0 and h3:
                a0 = float(h0[0]['accuracy'])
                a3 = float(h3[0]['accuracy'])
                m0 = float(h0[0]['mae'])
                m3 = float(h3[0]['mae'])
                mae_impr = (m0 - m3) / m0 * 100
                print(f"{g:<8} {a:<15} {a0:>7.1f}% {a3:>7.1f}% {a3 - a0:>+7.1f}% {m0:>7.2f}m {m3:>7.2f}m {mae_impr:>+7.1f}%")

    # Table 3: Metric comparison (h=3, raw, best algo per grid)
    print("\n--- Table 3: Metric Comparison (h=3, raw, best algo per grid) ---")
    print(f"{'Grid':<8} {'Metric':<12} {'Best Algo':<15} {'Accuracy':>9} {'MAE':>8}")
    print("-" * 55)
    for g in grids:
        for met in ['rss', 'sinr', 'RSS+SINR']:
            candidates = [r for r in rows if r['grid'] == g and r['metric'] == met
                          and r['history'] == '3' and r['feature_mode'] == 'raw']
            if not candidates:
                candidates = [r for r in rows if r['grid'] == g and r['metric'] == met
                              and r['history'] == '3']
            if candidates:
                best = max(candidates, key=lambda r: float(r['accuracy']))
                print(f"{g:<8} {met:<12} {best['algorithm']:<15} {float(best['accuracy']):>8.1f}% {float(best['mae']):>7.2f}m")

    # Table 4: Raw vs Smart comparison
    print("\n--- Table 4: Raw vs Smart Features (h=3, RSS+SINR) ---")
    print(f"{'Grid':<8} {'Algorithm':<15} {'Raw Acc':>8} {'Smart Acc':>10} {'Delta':>8}")
    print("-" * 55)
    for g in grids:
        for a in [aa for aa in algos if aa != 'gaussian']:
            raw = [r for r in rows if r['grid'] == g and r['algorithm'] == a
                   and r['metric'] == 'RSS+SINR' and r['feature_mode'] == 'raw'
                   and r['history'] == '3']
            smart = [r for r in rows if r['grid'] == g and r['algorithm'] == a
                     and r['metric'] == 'RSS+SINR' and r['feature_mode'] == 'smart'
                     and r['history'] == '3']
            if raw and smart:
                ar = float(raw[0]['accuracy'])
                asmart = float(smart[0]['accuracy'])
                print(f"{g:<8} {a:<15} {ar:>7.1f}% {asmart:>9.1f}% {asmart - ar:>+7.1f}%")

    # Table 5: Scalability trend
    print("\n--- Table 5: Scalability Trend (RSS+SINR, raw, h=3) ---")
    grid_points = {'3x3': 9, '5x5': 25, '7x7': 49, '10x10': 100, '15x15': 225}
    print(f"{'Grid':<8} {'N Points':>9} {'Gaussian':>10} {'RF':>10} {'XGBoost':>10}")
    print("-" * 50)
    for g in grids:
        npts = grid_points.get(g, '?')
        line = f"{g:<8} {npts:>9}"
        for a in ['gaussian', 'random_forest', 'xgboost']:
            match = [r for r in rows if r['grid'] == g and r['algorithm'] == a
                     and r['metric'] == 'RSS+SINR' and r['history'] == '3'
                     and (r['feature_mode'] == 'raw' or a == 'gaussian')]
            if match:
                line += f" {float(match[0]['accuracy']):>9.1f}%"
            else:
                line += f" {'N/A':>9}"
        print(line)


def analyze_core_7x7(rows):
    print("\n" + "=" * 70)
    print("CORE 7x7 RESULTS (4 algorithms including MLP)")
    print("=" * 70)

    algos = sorted(set(r['algorithm'] for r in rows))
    print(f"Algorithms: {algos}")

    print("\n--- Full History Progression (RSS+SINR, raw) ---")
    print(f"{'Algorithm':<15} {'h=0':>8} {'h=1':>8} {'h=2':>8} {'h=3':>8} {'Total Gain':>11}")
    print("-" * 55)
    for a in algos:
        vals = {}
        for h in range(4):
            if h == 0:
                match = [r for r in rows if r['algorithm'] == a
                         and r['metric'] == 'RSS+SINR' and r['history'] == str(h)]
            else:
                match = [r for r in rows if r['algorithm'] == a
                         and r['metric'] == 'RSS+SINR' and r['feature_mode'] == 'raw'
                         and r['history'] == str(h)]
            if match:
                vals[h] = float(match[0]['accuracy'])
        if vals:
            parts = [f"{vals.get(h, 0):>7.1f}%" for h in range(4)]
            gain = vals.get(3, 0) - vals.get(0, 0)
            print(f"{a:<15} {' '.join(parts)} {gain:>+10.1f}%")

    print("\n--- Full History Progression MAE (RSS+SINR, raw) ---")
    print(f"{'Algorithm':<15} {'h=0':>8} {'h=1':>8} {'h=2':>8} {'h=3':>8} {'Improvement':>12}")
    print("-" * 60)
    for a in algos:
        vals = {}
        for h in range(4):
            if h == 0:
                match = [r for r in rows if r['algorithm'] == a
                         and r['metric'] == 'RSS+SINR' and r['history'] == str(h)]
            else:
                match = [r for r in rows if r['algorithm'] == a
                         and r['metric'] == 'RSS+SINR' and r['feature_mode'] == 'raw'
                         and r['history'] == str(h)]
            if match:
                vals[h] = float(match[0]['mae'])
        if vals:
            parts = [f"{vals.get(h, 99):>7.2f}m" for h in range(4)]
            impr = (vals.get(0, 99) - vals.get(3, 99)) / vals.get(0, 99) * 100 if vals.get(0) else 0
            print(f"{a:<15} {' '.join(parts)} {impr:>+10.1f}%")


if __name__ == '__main__':
    print("Loading scalability results...")
    scale_rows = load_csv(SCALE_CSV)
    analyze_scalability(scale_rows)

    if CORE_CSV.exists():
        print("\nLoading core 7x7 results...")
        core_rows = load_csv(CORE_CSV)
        analyze_core_7x7(core_rows)
    else:
        print(f"\nCore 7x7 CSV not found at {CORE_CSV}")
