%% Run Voronoi 10x10 Simulation (BS Inside Grid)
% Wrapper that runs generate_simulation_data.m with the voronoi_10x10_config.
%
% SCENARIO:
%   - 10x10 grid, 2m spacing (18m x 18m)
%   - Serving BS at grid center [14, 14, 10] — UMi small cell
%   - 4 Voronoi areas: shopping_center, residential, highway, park
%     → Scenarios: UMi_NLOS / 50-50 UMi / RMa_LOS / UMi_LOS (fully distinct)
%   - 400 steps/point = 40,000 total samples
%   - No interfering base stations
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_voronoi_10x10
%
% Output:
%   results/grid_localization/grid_10x10/sim_data_voronoi_<timestamp>/
%     - simulation_data.mat
%     - data_generation_config.jsonc (copy of config used)

% Set config name globally so generate_simulation_data can access it
global OVERRIDE_CONFIG_NAME;
OVERRIDE_CONFIG_NAME = 'voronoi_10x10_config.jsonc';

fprintf('=== Voronoi 10x10 with BS Inside Grid ===\n');
fprintf('Config: %s\n\n', OVERRIDE_CONFIG_NAME);

% Run the generation script
generate_simulation_data;

% Clean up
clear global OVERRIDE_CONFIG_NAME;

fprintf('\n=== Voronoi 10x10 Complete ===\n');
fprintf('Next steps:\n');
fprintf('  1. Check the output folder in results/grid_localization/grid_10x10/\n');
fprintf('  2. Run the ML pipeline:\n');
fprintf('     python localization_pipeline.py --data-dir <output_folder>\n');
fprintf('  3. Or run the full experiment matrix:\n');
fprintf('     python run_experiment_matrix.py --data-dirs voronoi10=<output_folder>\n');
