"""
Inventory of the top-level directories under results/: size, dates, and, for
pipeline output folders, the provenance that is recorded inside them (data
directory, command line, noise mode, subsample, tuning, number of experiments,
plots present).

It reads only what is already on disk and changes nothing. Folders that
record nothing show "not recorded".

Usage (from the repository root):
    .venv/Scripts/python experiments/09_grid_localization/src/python/utils/results_inventory.py
    .venv/Scripts/python experiments/09_grid_localization/src/python/utils/results_inventory.py --markdown
"""
import argparse
import csv
import re
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
RESULTS = PROJECT_ROOT / 'results'


def human(n):
    for u in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or u == 'GB':
            return f'{n:.0f} {u}' if u in ('B', 'KB') else f'{n:.1f} {u}'
        n /= 1024


def walk_stats(d):
    size, files, newest, oldest = 0, 0, 0.0, float('inf')
    for p in d.rglob('*'):
        if p.is_file():
            st = p.stat()
            size += st.st_size
            files += 1
            newest = max(newest, st.st_mtime)
            oldest = min(oldest, st.st_mtime)
    fmt = lambda t: time.strftime('%Y-%m-%d', time.localtime(t)) if files else '-'
    return size, files, fmt(oldest), fmt(newest)


def read_report(d):
    """Provenance recorded in PIPELINE_REPORT.md: data dir, flags, sample count."""
    rep = d / 'PIPELINE_REPORT.md'
    if not rep.exists():
        return {}
    text = rep.read_text(encoding='utf-8', errors='replace')
    out = {}
    m = re.search(r'```bash\s*\n(.*?)\n```', text, re.S)
    cmd = m.group(1) if m else ''
    dm = re.search(r'--data-dir\s+(\S+)', cmd)
    out['data'] = Path(dm.group(1).replace('\\', '/')).name if dm else None
    out['sinr_aoa'] = '--sinr-dependent-aoa' in cmd
    sm = re.search(r'--subsample\s+(\S+)', cmd)
    out['subsample'] = sm.group(1) if sm else None
    rm = re.search(r'--run-only\s+(.*?)(?:\s--|$)', cmd)
    out['run_only'] = len(rm.group(1).split()) if rm else None
    gm = re.search(r'Generated:\*\*\s*([0-9-]+ [0-9:]+)', text)
    out['generated'] = gm.group(1) if gm else None
    tm = re.search(r'Total samples \| ([\d,]+)', text)
    out['samples'] = tm.group(1) if tm else None
    return out


def summary_rows(d):
    f = d / 'csvs' / 'results_summary.csv'
    if not f.exists():
        return None
    with open(f, newline='', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    return len({r['experiment'] for r in rows}), len({r['model'] for r in rows})


def inventory():
    rows = []
    for d in sorted(p for p in RESULTS.iterdir() if p.is_dir()):
        size, files, first, last = walk_stats(d)
        rec = {'dir': d.name, 'size': size, 'files': files, 'first': first, 'last': last}
        rec.update(read_report(d))
        sr = summary_rows(d)
        rec['experiments'] = sr[0] if sr else None
        rec['plots'] = len(list((d / 'images').rglob('*.png'))) if (d / 'images').exists() else None
        rec['checkpoints'] = len(list((d / 'csvs' / 'checkpoint').glob('*.json'))) if (d / 'csvs' / 'checkpoint').exists() else None
        rows.append(rec)
    return rows


def main():
    ap = argparse.ArgumentParser(
        description='Inventory of results/ with the provenance recorded inside each folder.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python results_inventory.py
  python results_inventory.py --markdown > inventory.md
""")
    ap.add_argument('--markdown', action='store_true')
    args = ap.parse_args()
    rows = inventory()
    cols = ['dir', 'size', 'files', 'first', 'last', 'generated', 'data', 'samples', 'sinr_aoa', 'subsample',
            'run_only', 'experiments', 'checkpoints', 'plots']
    show = lambda r, c: (human(r[c]) if c == 'size' else ('not recorded' if r.get(c) is None else str(r[c])))
    if args.markdown:
        print('| ' + ' | '.join(cols) + ' |')
        print('|' + '---|' * len(cols))
        for r in rows:
            print('| ' + ' | '.join(show(r, c) for c in cols) + ' |')
    else:
        for r in rows:
            print(f'{r["dir"]:<58}{human(r["size"]):>10} {r["files"]:>6} files  {r["first"]} .. {r["last"]}')
            extras = {c: r[c] for c in cols[5:] if r.get(c) is not None}
            if extras:
                print('    ' + '  '.join(f'{k}={v}' for k, v in extras.items()))


if __name__ == '__main__':
    main()
