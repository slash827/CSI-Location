%% Run Voronoi Heterogeneous Simulation
% Wrapper that configures generate_simulation_data.m to use voronoi_config.jsonc
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_voronoi

% Set config name globally so generate_simulation_data can access it
global OVERRIDE_CONFIG_NAME;
OVERRIDE_CONFIG_NAME = 'voronoi_config.jsonc';

% Run the generation script
generate_simulation_data;

% Clean up
clear global OVERRIDE_CONFIG_NAME;
