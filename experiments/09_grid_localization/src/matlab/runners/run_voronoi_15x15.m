%% Run Voronoi 15x15 Simulation (BS Inside Grid — Controlled Scalability)
% Mirrors run_voronoi_10x10.m for a direct scalability comparison.
%
% SCENARIO:
%   - 15x15 grid, 2m spacing (28m x 28m)
%   - Serving BS at grid center [19, 19, 10] — same UMi small cell as 10x10
%   - 4 Voronoi areas: shopping_center, residential, highway, park
%     → Scenarios: UMi_NLOS / 50-50 UMi / RMa_LOS / UMi_LOS (fully distinct)
%   - 400 steps/point = 90,000 total samples
%   - No interfering base stations
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_voronoi_15x15
%
% Output:
%   results/grid_localization/grid_15x15/sim_data_voronoi_<timestamp>/
%     - simulation_data.mat
%     - data_generation_config.jsonc (copy of config used)

% Set config name globally so generate_simulation_data can access it
src_matlab_dir = fileparts(fileparts(mfilename('fullpath')));  % runners/../ = src/matlab
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
global OVERRIDE_CONFIG_NAME;
OVERRIDE_CONFIG_NAME = 'voronoi_15x15_config.jsonc';

fprintf('=== Voronoi 15x15 with BS Inside Grid ===\n');
fprintf('Config: %s\n\n', OVERRIDE_CONFIG_NAME);

% Run the generation script
generate_simulation_data;

% Clean up
clear src_matlab_dir = fileparts(fileparts(mfilename('fullpath')));  % runners/../ = src/matlab
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
global OVERRIDE_CONFIG_NAME;

fprintf('\n=== Voronoi 15x15 Complete ===\n');
fprintf('Next steps:\n');
fprintf('  1. Check the output folder in results/grid_localization/grid_15x15/\n');
fprintf('  2. Run the experiment matrix (same combos as 10x10 for comparison):\n');
fprintf('     python run_experiment_matrix.py \\\n');
fprintf('       --data-dir <output_folder> \\\n');
fprintf('       --algorithms xgboost random_forest \\\n');
fprintf('       --metrics rss sinr "rss,sinr" "rss,sinr,aoa_azimuth" "rss,sinr,aoa_azimuth,aoa_elevation" \\\n');
fprintf('       --max-history 3 --feature-modes raw\n');
