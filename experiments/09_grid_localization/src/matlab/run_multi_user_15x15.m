%% Run Multi-User Heterogeneous Simulation — 15x15 Voronoi Grid
% Generates 5 separate user simulation runs, each with a different device profile.
%
% RESEARCH HYPOTHESIS:
%   Transition-based features (h>0) are robust to device heterogeneity,
%   while static features (h=0) degrade — because transitions capture
%   relative changes that are device-independent.
%
% NETWORK SETUP (single-BS scope — NOT triangulation):
%   - 1 serving BS at [19, 19, 10]  (grid center)  — ONLY features source
%   - 2 interfering BSs OUTSIDE grid, 30m ISD:
%       IBS-1: [-11, 19, 10]  (30m west,  creates E-W SINR gradient)
%       IBS-2: [19, -11, 10]  (30m south, creates N-S SINR gradient)
%   - Features: RSS and SINR from serving BS only
%
% DEVICE PROFILES:
%   U1: 4 antennas, 0.0 dB, 1.5 m  (Flagship A,  seed=100)
%   U2: 2 antennas, -2.0 dB, 1.5 m (Mid-range,   seed=200)
%   U3: 1 antenna,  -4.0 dB, 1.5 m (Budget/Old,  seed=300)
%   U4: 4 antennas, 0.0 dB,  1.5 m (Flagship B,  seed=400)  ← same device as U1
%   U5: 2 antennas, -1.0 dB, 0.9 m (Tablet/IoT,  seed=500)
%
% U1 and U4 share the same device parameters but different walk seeds,
% which isolates the device effect from trajectory randomness.
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_multi_user_15x15
%
% Output:
%   results/grid_localization/grid_15x15/sim_data_multi_user_<timestamp>/
%     user1_voronoi_15x15.mat
%     user2_voronoi_15x15.mat
%     ...
%     user5_voronoi_15x15.mat
%     experiment_info.mat

%% Declare all override globals
global OVERRIDE_CONFIG_NAME;
global OVERRIDE_WALK_SEED;
global OVERRIDE_N_RX_ANTENNAS;
global OVERRIDE_ANTENNA_GAIN_DB;
global OVERRIDE_UE_HEIGHT_M;
global OVERRIDE_OUTPUT_DIR;
global OVERRIDE_OUTPUT_FILENAME;
global OVERRIDE_USER_ID;

%% Setup paths and shared output directory
script_dir     = fileparts(mfilename('fullpath'));
experiment_root = fileparts(fileparts(script_dir));
workspace_root  = fileparts(fileparts(experiment_root));

timestamp  = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
output_dir = fullfile(workspace_root, 'results', 'grid_localization', ...
                      'grid_15x15', sprintf('sim_data_multi_user_%s', timestamp));
mkdir(output_dir);

fprintf('=== Multi-User Heterogeneous 15x15 Experiment ===\n');
fprintf('Output directory: %s\n\n', output_dir);

%% Device profiles
% Each row: [n_antennas, antenna_gain_db, ue_height_m, walk_seed]
profiles = [
    4,  0.0, 1.5, 100;   % U1: Flagship A
    2, -2.0, 1.5, 200;   % U2: Mid-range
    1, -4.0, 1.5, 300;   % U3: Budget/Old
    4,  0.0, 1.5, 400;   % U4: Flagship B (same device as U1, different seed)
    2, -1.0, 0.9, 500;   % U5: Tablet/IoT
];
profile_names = {'Flagship_A', 'Mid-range', 'Budget_Old', 'Flagship_B', 'Tablet_IoT'};

%% Run simulation per user
n_users = size(profiles, 1);

for u = 1:n_users
    fprintf('\n========== User %d / %d (%s) ==========\n', ...
            u, n_users, profile_names{u});
    fprintf('  n_antennas=%.0f, gain=%.1f dB, height=%.2f m, seed=%d\n', ...
            profiles(u, 1), profiles(u, 2), profiles(u, 3), profiles(u, 4));

    % Set override globals for this user
    OVERRIDE_CONFIG_NAME    = 'multi_user_voronoi_15x15_config.jsonc';
    OVERRIDE_WALK_SEED      = profiles(u, 4);
    OVERRIDE_N_RX_ANTENNAS  = profiles(u, 1);
    OVERRIDE_ANTENNA_GAIN_DB = profiles(u, 2);
    OVERRIDE_UE_HEIGHT_M    = profiles(u, 3);
    OVERRIDE_OUTPUT_DIR     = output_dir;
    OVERRIDE_OUTPUT_FILENAME = sprintf('user%d_voronoi_15x15.mat', u);
    OVERRIDE_USER_ID        = u;

    % Run data generation
    generate_simulation_data;

    % Clear globals after each run (generate_simulation_data does its own clear/clc)
    OVERRIDE_CONFIG_NAME    = [];
    OVERRIDE_WALK_SEED      = [];
    OVERRIDE_N_RX_ANTENNAS  = [];
    OVERRIDE_ANTENNA_GAIN_DB = [];
    OVERRIDE_UE_HEIGHT_M    = [];
    OVERRIDE_OUTPUT_DIR     = [];
    OVERRIDE_OUTPUT_FILENAME = [];
    OVERRIDE_USER_ID        = [];

    fprintf('[Done] User %d saved: user%d_voronoi_15x15.mat\n', u, u);
end

%% Summary
fprintf('\n=== Multi-User Simulation Complete ===\n');
fprintf('Output directory: %s\n', output_dir);
fprintf('Files generated:\n');
for u = 1:n_users
    f = fullfile(output_dir, sprintf('user%d_voronoi_15x15.mat', u));
    if exist(f, 'file')
        info = whos('-file', f);
        fprintf('  user%d_voronoi_15x15.mat  (%s, %.0f MB)\n', ...
                u, profile_names{u}, sum([info.bytes]) / 1e6);
    else
        fprintf('  user%d_voronoi_15x15.mat  [MISSING]\n', u);
    end
end

fprintf('\nNext step — run Python pipeline:\n');
fprintf('  python experiments/09_grid_localization/src/python/multi_user_pipeline.py \\\n');
fprintf('    --data-dir "%s"\n', output_dir);
