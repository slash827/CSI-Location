%% Run Voronoi Heterogeneous Simulation
% Wrapper that configures generate_simulation_data.m to use voronoi_config.jsonc
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_voronoi

% Set config name globally so generate_simulation_data can access it
src_matlab_dir = fileparts(fileparts(mfilename('fullpath')));  % runners/../ = src/matlab
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
global OVERRIDE_CONFIG_NAME;
OVERRIDE_CONFIG_NAME = 'voronoi_config.jsonc';

% Run the generation script
generate_simulation_data;

% Clean up
clear src_matlab_dir = fileparts(fileparts(mfilename('fullpath')));  % runners/../ = src/matlab
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
global OVERRIDE_CONFIG_NAME;
