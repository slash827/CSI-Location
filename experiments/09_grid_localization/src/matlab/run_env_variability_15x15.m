%% Run Environmental Variability Experiment — 15x15 Voronoi Grid
% Generates 3 simulation runs for U1 (Flagship A) on the same 15x15 Voronoi grid,
% varying only the QuaDRiGa channel seed. Walk path (seed=100) is fixed across runs.
%
% PURPOSE:
%   Isolates environmental variability (day-to-day fading changes) from
%   position/trajectory effects. The three runs share the identical walk
%   trajectory but have different channel realizations.
%
%   Python analysis (multi_user_pipeline.py --env-dir <path>):
%     - Cross-env split:  train on run1 + run2, test on run3
%     - Reference split:  80/20 chronological on run1 only
%   Experiments: BASE (h=0), BASE_H (h=3, absolute), BASE_H_delta (h=3, delta)
%
% DEVICE PROFILE (U1 — Flagship A):
%   4 antennas, 0.0 dB gain, 1.5 m height, walk seed=100
%
% CHANNEL SEEDS:
%   Run 1: channel seed 101
%   Run 2: channel seed 102
%   Run 3: channel seed 103  ← held-out test environment
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_env_variability_15x15
%
% Output:
%   results/grid_localization/grid_15x15/sim_data_env_variability_<timestamp>/
%     run1_voronoi_15x15.mat
%     run2_voronoi_15x15.mat
%     run3_voronoi_15x15.mat

%% Declare all override globals
global OVERRIDE_CONFIG_NAME;
global OVERRIDE_WALK_SEED;
global OVERRIDE_N_RX_ANTENNAS;
global OVERRIDE_ANTENNA_GAIN_DB;
global OVERRIDE_UE_HEIGHT_M;
global OVERRIDE_OUTPUT_DIR;
global OVERRIDE_OUTPUT_FILENAME;
global OVERRIDE_USER_ID;
global OVERRIDE_CHANNEL_SEED;

%% Setup paths and output directory
script_dir      = fileparts(mfilename('fullpath'));
experiment_root = fileparts(fileparts(script_dir));
workspace_root  = fileparts(fileparts(experiment_root));

timestamp  = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
output_dir = fullfile(workspace_root, 'results', 'grid_localization', ...
                      'grid_15x15', sprintf('sim_data_env_variability_%s', timestamp));
mkdir(output_dir);

fprintf('=== Environmental Variability 15x15 Experiment ===\n');
fprintf('Device: U1 (4 ant, 0 dB, 1.5 m, walk_seed=100)\n');
fprintf('Output: %s\n\n', output_dir);

%% Fixed device profile (U1 — Flagship A)
DEVICE_N_ANTENNAS  = 4;
DEVICE_GAIN_DB     = 0.0;
DEVICE_HEIGHT_M    = 1.5;
WALK_SEED          = 100;   % Same walk for all 3 runs

%% Channel seeds (vary the QuaDRiGa channel realization only)
channel_seeds = [101, 102, 103];
n_runs = numel(channel_seeds);

%% Run simulation per environment
for r = 1:n_runs
    chan_seed = channel_seeds(r);
    fprintf('\n========== Run %d / %d (channel_seed=%d) ==========\n', ...
            r, n_runs, chan_seed);

    % Set override globals
    OVERRIDE_CONFIG_NAME    = 'multi_user_voronoi_15x15_config.jsonc';
    OVERRIDE_WALK_SEED      = WALK_SEED;
    OVERRIDE_N_RX_ANTENNAS  = DEVICE_N_ANTENNAS;
    OVERRIDE_ANTENNA_GAIN_DB = DEVICE_GAIN_DB;
    OVERRIDE_UE_HEIGHT_M    = DEVICE_HEIGHT_M;
    OVERRIDE_OUTPUT_DIR     = output_dir;
    OVERRIDE_OUTPUT_FILENAME = sprintf('run%d_voronoi_15x15.mat', r);
    OVERRIDE_USER_ID        = 1;         % Single-user, always user_id=1
    OVERRIDE_CHANNEL_SEED   = chan_seed; % Key: different channel per run

    % Run data generation
    generate_simulation_data;

    % Clear globals after each run
    OVERRIDE_CONFIG_NAME    = [];
    OVERRIDE_WALK_SEED      = [];
    OVERRIDE_N_RX_ANTENNAS  = [];
    OVERRIDE_ANTENNA_GAIN_DB = [];
    OVERRIDE_UE_HEIGHT_M    = [];
    OVERRIDE_OUTPUT_DIR     = [];
    OVERRIDE_OUTPUT_FILENAME = [];
    OVERRIDE_USER_ID        = [];
    OVERRIDE_CHANNEL_SEED   = [];

    fprintf('[Done] Run %d saved: run%d_voronoi_15x15.mat\n', r, r);
end

%% Summary
fprintf('\n=== Environmental Variability Simulation Complete ===\n');
fprintf('Output directory: %s\n', output_dir);
fprintf('Files generated:\n');
for r = 1:n_runs
    f = fullfile(output_dir, sprintf('run%d_voronoi_15x15.mat', r));
    if exist(f, 'file')
        info = whos('-file', f);
        fprintf('  run%d_voronoi_15x15.mat  (channel_seed=%d, %.0f MB)\n', ...
                r, channel_seeds(r), sum([info.bytes]) / 1e6);
    else
        fprintf('  run%d_voronoi_15x15.mat  [MISSING]\n', r);
    end
end

fprintf('\nNext step — run Python env variability analysis:\n');
fprintf('  python experiments/09_grid_localization/src/python/multi_user_pipeline.py \\\n');
fprintf('    --data-dir "<multi_user_data_dir>" \\\n');
fprintf('    --env-dir "%s"\n', output_dir);
