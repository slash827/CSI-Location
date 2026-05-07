"""
Generate per-cell Voronoi accuracy maps for the multi-user 15x15 experiment.
Produces 4 images: RF E2, RF E5, XGBoost E2, XGBoost E5.
"""
import sys
import numpy as np
import scipy.io as sio
from pathlib import Path

# Resolve paths
SCRIPT_DIR   = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
DATA_DIR     = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_15x15' \
               / 'sim_data_multi_user_2026-03-02_19-41-39'
REF_SIM_MAT  = PROJECT_ROOT / 'results' / 'grid_localization' / 'grid_15x15' \
               / 'sim_data_voronoi_2026-03-02_08-12-13' / 'simulation_data.mat'
OUT_DIR      = PROJECT_ROOT / 'results' / 'multi_user_voronoi_15x15'

sys.path.insert(0, str(SCRIPT_DIR))
from pipelines.multi_user_pipeline import (
    load_all_users, make_split, build_grid_lookup,
    build_history_features, get_feature_cols, run_one_experiment,
    plot_voronoi_accuracy_map, HISTORY_PRIMARY
)

print(f"Data dir : {DATA_DIR}")
print(f"Output   : {OUT_DIR}")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -- Load Voronoi cell names and centers from the reference simulation ------
voronoi_names   = None
voronoi_centers = None
if REF_SIM_MAT.exists():
    ref = sio.loadmat(str(REF_SIM_MAT), squeeze_me=True, struct_as_record=False)
    wp  = ref['walk_path']
    voronoi_names   = list(wp.voronoi_names)
    voronoi_centers = np.array(wp.voronoi_centers, dtype=float)
    print(f"Loaded cell names from reference sim: {voronoi_names}")
else:
    print("WARNING: reference simulation_data.mat not found -- will use C1..C4 labels")

# -- Load and prepare data --------------------------------------------------
print("\nLoading data...")
df = load_all_users(DATA_DIR)
df = make_split(df, test_ratio=0.2)
grid_lookup = build_grid_lookup(df)
print(f"  {len(df):,} samples, {df['grid_point_id'].nunique()} classes")

# -- Build feature sets (build once each, reuse across models) --------------
print("\nBuilding feature sets...")
feat_df_e2 = build_history_features(df, h=HISTORY_PRIMARY, extra_cols=None)
fcols_e2   = get_feature_cols(h=HISTORY_PRIMARY, extra_cols=None)

feat_df_e5 = build_history_features(df, h=0, include_aoa=True)
fcols_e5   = get_feature_cols(h=0, include_aoa=True)

# -- Run all 4 combinations -------------------------------------------------
combos = [
    ('rf',      'E2', feat_df_e2, fcols_e2, HISTORY_PRIMARY, f'E2 h={HISTORY_PRIMARY} rf'),
    ('rf',      'E5', feat_df_e5, fcols_e5, 0,               'E5 h=0+AoA rf'),
    ('xgboost', 'E2', feat_df_e2, fcols_e2, HISTORY_PRIMARY, f'E2 h={HISTORY_PRIMARY} xgboost'),
    ('xgboost', 'E5', feat_df_e5, fcols_e5, 0,               'E5 h=0+AoA xgboost'),
]

all_results = {}
for model, exp, fdf, fcols, h_val, label in combos:
    print(f"\nRunning {model.upper()} {exp}...")
    res = run_one_experiment(fdf, fcols, grid_lookup, model, f"  {label}")
    print(f"  {model.upper()} {exp}: acc={res['overall']['accuracy']:.1f}%  MAE={res['overall']['mae']:.3f} m")
    all_results[(model, exp)] = (res, h_val)

# -- Generate 4 plots -------------------------------------------------------
PLOT_KWARGS = dict(data_dir=DATA_DIR, voronoi_names=voronoi_names,
                   voronoi_centers_override=voronoi_centers)

for model, exp, _, _, h_val, _ in combos:
    res, h_val = all_results[(model, exp)]
    fname = f'voronoi_accuracy_map_{model}_{exp}.png'
    print(f"\nGenerating {fname} ...")
    plot_voronoi_accuracy_map(
        {model: {exp: res}}, df, [model], OUT_DIR,
        h_primary=h_val, exp_key=exp, out_filename=fname,
        **PLOT_KWARGS
    )

print(f"\nDone -- 4 plots saved to {OUT_DIR}")
