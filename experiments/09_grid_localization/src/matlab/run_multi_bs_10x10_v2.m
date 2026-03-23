%% Run Multi-BS 10x10 v2 — Realistic Interferer Placement Outside Grid
% Tests whether co-channel interference with realistic BS placement creates
% useful SINR spatial variation for single-BS fingerprinting.
%
% SCENARIO (v2 — realistic placement):
%   - 10x10 grid, 2m spacing, Voronoi 4-cell environment
%   - Serving BS at grid center [14, 14, 10]
%   - 2 interfering BSs OUTSIDE the grid, ~30m from serving BS:
%       IBS-1: [-16, 14, 10]  — 30m west  (creates E-W SINR gradient)
%       IBS-2: [14, -16, 10]  — 30m south (creates N-S SINR gradient)
%   - Serving BS always dominant: min UE-IBS distance ~21m vs ~8.5m to serving BS
%   - Expected SINR: +5 to +15 dB (realistic, positive, spatially varied)
%
% DIFFERENCE FROM v1:
%   v1 had IBS at [5,5] and [23,23] — inside the grid footprint.
%   SINR was -47 to -23 dB throughout (interferers overwhelmed serving BS).
%   v2 places IBS outside the cell to match real deployment assumptions.
%
% RESEARCH QUESTION:
%   Does a realistic SINR gradient improve rss+sinr accuracy vs single-BS?
%   Features compared: {rss+sinr} (valid) vs {rss+sinr+aoa} (AoA baseline)
%   Note: rss_ibs_* saved to .mat for reference but NOT used as ML features
%         (per-interferer RSS = triangulation = different problem scope)
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_multi_bs_10x10_v2
%
% Output:
%   results/grid_localization/grid_10x10/sim_data_voronoi_<timestamp>/

global OVERRIDE_CONFIG_NAME;
OVERRIDE_CONFIG_NAME = 'multi_bs_10x10_v2_config.jsonc';

fprintf('=== Multi-BS 10x10 v2 (Realistic Placement) ===\n');
fprintf('Config: %s\n', OVERRIDE_CONFIG_NAME);
fprintf('  Serving BS: [14, 14, 10]\n');
fprintf('  IBS-1:      [-16, 14, 10]  (30m west,  outside grid)\n');
fprintf('  IBS-2:      [14, -16, 10]  (30m south, outside grid)\n');
fprintf('  Expected SINR: +5 to +15 dB\n\n');

generate_simulation_data;

clear global OVERRIDE_CONFIG_NAME;

fprintf('\n=== Multi-BS v2 Complete ===\n');
fprintf('Compare (single-BS scope only — no triangulation):\n');
fprintf('  rss+sinr (single-BS)   vs\n');
fprintf('  rss+sinr (multi-BS v2) vs\n');
fprintf('  rss+sinr+aoa_azimuth+aoa_elevation\n');
fprintf('\nKey question: does realistic SINR gradient improve over single-BS?\n');
