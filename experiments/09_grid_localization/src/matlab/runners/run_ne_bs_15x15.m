%% Run NE-BS Heterogeneous Simulation — 15x15 Voronoi Grid
% Generates 5 separate user simulation runs, each with a different device profile.
%
% RESEARCH HYPOTHESIS (comparison experiment):
%   In the center-BS experiment (multi_user_voronoi_15x15) the serving BS sat
%   at the grid center, covering ~360° of azimuth angles — giving AoA an almost
%   perfect discriminative role (+35pp over BASE_H).
%   Here the serving BS is placed 15m north and 15m east of the NE grid corner,
%   compressing all 225 grid points into a ~52° azimuth wedge.
%   Hypothesis: the AoA gain shrinks dramatically in this configuration.
%
% NETWORK SETUP:
%   Grid: 15x15, spacing=2m, offset=[5,5]  =>  X,Y in [5,33]
%   Serving BS: [48, 48, 10]  (15m north + 15m east of NE corner [33,33])
%   IBS-1:      [-11, 19, 10] (west of grid  — E-W SINR gradient)
%   IBS-2:      [19, -11, 10] (south of grid — N-S SINR gradient)
%   (positions are read from the config; the 2026-06-12 data was made with the
%    earlier [19,-10] / [-10,19] pair)
%   Features:   RSS and SINR from serving BS only
%
% DEVICE PROFILES (same as multi_user_voronoi_15x15 for clean comparison):
%   U1: 4 antennas, 0.0 dB, 1.5 m  (Flagship A,  seed=100)
%   U2: 2 antennas, -2.0 dB, 1.5 m (Mid-range,   seed=200)
%   U3: 1 antenna,  -4.0 dB, 1.5 m (Budget/Old,  seed=300)
%   U4: 4 antennas, 0.0 dB,  1.5 m (Flagship B,  seed=400)
%   U5: 2 antennas, -1.0 dB, 0.9 m (Tablet/IoT,  seed=500)
%
% PARALLELISM:
%   Uses parfor when the Parallel Computing Toolbox (PCT) is available.
%   Falls back to a regular for-loop without PCT.
%   Each worker calls run_single_user_sim(), which sets its own globals
%   and writes its own timestamped log to <output_dir>/logs/.
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_ne_bs_15x15
%
% Output:
%   results/grid_localization/grid_15x15/sim_data_ne_bs_<timestamp>/
%     user1_ne_bs_15x15.mat  ...  user5_ne_bs_15x15.mat
%     experiment_info.mat
%     logs/

%% Paths
script_dir      = fileparts(mfilename('fullpath'));
src_matlab_dir  = fileparts(script_dir);
experiment_root = fileparts(fileparts(src_matlab_dir));     % 09_grid_localization/
workspace_root  = fileparts(fileparts(experiment_root));    % CSI-Location/
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
ensure_quadriga();

%% Shared output directory
timestamp  = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
output_dir = fullfile(workspace_root, 'results', 'grid_localization', ...
                      'grid_15x15', sprintf('sim_data_ne_bs_%s', timestamp));
mkdir(output_dir);

%% Top-level log (diary before parfor — captures wrapper-level output only)
log_dir = fullfile(output_dir, 'logs');
mkdir(log_dir);
main_log = fullfile(log_dir, sprintf('main_%s.log', timestamp));
diary(main_log);
diary on;

fprintf('=== NE-BS Heterogeneous 15x15 Experiment ===\n');
fprintf('Start time:       %s\n', datestr(now));
fprintf('Output directory: %s\n\n', output_dir);

%% Config and device profiles
if evalin('base', 'exist(''RUNNER_CONFIG_NAME'', ''var'')') && ~isempty(evalin('base', 'RUNNER_CONFIG_NAME'))
    config_name = evalin('base', 'RUNNER_CONFIG_NAME');
else
    config_name = 'ne_bs_voronoi_15x15_config.jsonc';
end

% Each row: [n_antennas, antenna_gain_db, ue_height_m, walk_seed]
profiles = [
    4,  0.0, 1.5, 100;   % U1: Flagship A
    2, -2.0, 1.5, 200;   % U2: Mid-range
    1, -4.0, 1.5, 300;   % U3: Budget/Old
    4,  0.0, 1.5, 400;   % U4: Flagship B (same device as U1, different seed)
    2, -1.0, 0.9, 500;   % U5: Tablet/IoT
];
profile_names = {'Flagship_A', 'Mid-range', 'Budget_Old', 'Flagship_B', 'Tablet_IoT'};
n_users = size(profiles, 1);

%% Print plan
fprintf('Device profiles:\n');
for u = 1:n_users
    fprintf('  U%d (%s): n_ant=%d  gain=%.1f dB  height=%.2f m  seed=%d\n', ...
            u, profile_names{u}, profiles(u,1), profiles(u,2), profiles(u,3), profiles(u,4));
end
fprintf('\n');

%% Run simulations (parfor if PCT available, else sequential for-loop)
has_pct = license('test', 'Distrib_Computing_Toolbox');
if has_pct
    fprintf('Parallel Computing Toolbox detected — running parfor (up to %d workers)\n\n', n_users);
else
    fprintf('No PCT licence — running sequentially\n\n');
end

total_tic = tic;

% Convert profiles matrix to cell array of row vectors so parfor can slice it
profiles_cell = cell(n_users, 1);
for u = 1:n_users
    profiles_cell{u} = profiles(u, :);
end

if has_pct
    parfor u = 1:n_users
        run_single_user_sim(u, profiles_cell{u}, output_dir, config_name, workspace_root);
    end
else
    for u = 1:n_users
        fprintf('\n========== User %d / %d (%s) ==========\n', u, n_users, profile_names{u});
        run_single_user_sim(u, profiles_cell{u}, output_dir, config_name, workspace_root);
        fprintf('[Done] User %d\n', u);
    end
end

total_elapsed = toc(total_tic);
fprintf('\n=== All users complete in %.1f min ===\n', total_elapsed/60);

%% Summary
fprintf('\n=== Simulation Summary ===\n');
fprintf('Output directory: %s\n', output_dir);
fprintf('Files generated:\n');
total_mb = 0;
for u = 1:n_users
    stem = regexprep(config_name, '_config\.jsonc$', '');
    stem = regexprep(stem, '^voronoi_', '');
    f = fullfile(output_dir, sprintf('user%d_%s.mat', u, stem));
    if exist(f, 'file')
        info = whos('-file', f);
        mb = sum([info.bytes]) / 1e6;
        total_mb = total_mb + mb;
        fprintf('  user%d_%s.mat  (%s, %.0f MB)\n', u, stem, profile_names{u}, mb);
    else
        fprintf('  user%d_%s.mat  [MISSING]\n', u, stem);
    end
end
fprintf('Total data: %.0f MB\n', total_mb);

%% Save a copy of the config used and the provenance of this run
config_path = fullfile(experiment_root, 'configs', config_name);
copyfile(config_path, fullfile(output_dir, 'data_generation_config.jsonc'));
[~, git_commit] = system(sprintf('git -C "%s" rev-parse HEAD', workspace_root));
[~, git_dirty]  = system(sprintf('git -C "%s" status --porcelain -- experiments/09_grid_localization/configs experiments/09_grid_localization/src/matlab', workspace_root));
cfg_used = read_jsonc(config_path);

%% Save experiment metadata
experiment_info = struct();
experiment_info.git_commit        = strtrim(git_commit);
experiment_info.git_dirty_matlab  = ~isempty(strtrim(git_dirty));
experiment_info.center_frequency  = cfg_used.channel.center_frequency;
experiment_info.bandwidth         = cfg_used.channel.bandwidth;
experiment_info.scenario          = cfg_used.channel.scenario;
experiment_info.uniform_scenario  = cfg_used.channel.mixed_scenario.uniform_scenario;
experiment_info.tx_power_dbm      = cfg_used.base_station.tx_power_dbm;
experiment_info.interferers       = cfg_used.base_station.interferers.positions;
experiment_info.config_name     = config_name;
experiment_info.profiles        = profiles;
experiment_info.profile_names   = profile_names;
experiment_info.output_dir      = output_dir;
experiment_info.timestamp       = timestamp;
experiment_info.bs_position     = [48, 48, 10];
experiment_info.bs_note         = '15m north + 15m east of NE grid corner (33,33)';
experiment_info.total_time_s    = total_elapsed;
save(fullfile(output_dir, 'experiment_info.mat'), 'experiment_info');

fprintf('\nNext step — run Python pipeline:\n');
fprintf('  python experiments/09_grid_localization/src/python/multi_user_pipeline.py \\\n');
fprintf('    --data-dir "%s" \\\n', output_dir);
fprintf('    --out-dir results/ne_bs_voronoi_15x15 \\\n');
fprintf('    --models xgboost rf --history 3\n');

diary off;
