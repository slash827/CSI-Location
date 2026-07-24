function run_single_user_sim(user_idx, profile, output_dir, config_name, workspace_root)
%RUN_SINGLE_USER_SIM  Run one user's simulation — designed to be called from parfor.
%
%   run_single_user_sim(USER_IDX, PROFILE, OUTPUT_DIR, CONFIG_NAME, WORKSPACE_ROOT)
%
%   Inputs:
%     user_idx       - integer user ID (1-based)
%     profile        - [n_antennas, antenna_gain_db, ue_height_m, walk_seed]
%     output_dir     - absolute path to the shared output directory (must exist)
%     config_name    - filename of the JSONC config (e.g. 'ne_bs_voronoi_15x15_config.jsonc')
%     workspace_root - absolute path to CSI-Location root
%
%   Output:
%     Writes <output_dir>/user<N>_<stem>.mat  where stem is derived from config_name.
%
%   Notes:
%     * This function sets override globals, calls generate_simulation_data,
%       then clears them.  Each parfor worker has its own workspace so globals
%       set here do not bleed into sibling workers.
%     * The diary (log file) for this worker is written to
%       <output_dir>/logs/user<N>_<timestamp>.log

%% Derive output filename stem from config name
% 'ne_bs_voronoi_15x15_config.jsonc' -> 'ne_bs_15x15'
stem = regexprep(config_name, '_config\.jsonc$', '');
stem = regexprep(stem, '^voronoi_', '');
out_filename = sprintf('user%d_%s.mat', user_idx, stem);

%% Timestamped log file per worker
log_dir = fullfile(output_dir, 'logs');
if ~exist(log_dir, 'dir')
    mkdir(log_dir);
end
ts = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
log_file = fullfile(log_dir, sprintf('user%d_%s.log', user_idx, ts));
diary(log_file);
diary on;

fprintf('=== User %d simulation started [%s] ===\n', user_idx, datestr(now));
fprintf('  config:   %s\n', config_name);
fprintf('  output:   %s\n', out_filename);
fprintf('  n_ant=%d  gain=%.1f dB  height=%.2f m  walk_seed=%d\n', ...
        profile(1), profile(2), profile(3), profile(4));

%% Add paths needed by generate_simulation_data
script_dir     = fileparts(mfilename('fullpath'));   % core/
src_matlab_dir = fileparts(script_dir);              % src/matlab/
utils_path = fullfile(workspace_root, 'utils');
addpath(script_dir);                                 % core/ — so generate_simulation_data is findable
addpath(fullfile(src_matlab_dir, 'lib'));             % AreaGenerator, GeometryUtils, TrafficUtils, read_jsonc
addpath(utils_path);                                 % CSI-Location/utils/ — QuaDRiGa

%% Set override globals
global OVERRIDE_CONFIG_NAME OVERRIDE_WALK_SEED OVERRIDE_N_RX_ANTENNAS ...
       OVERRIDE_ANTENNA_GAIN_DB OVERRIDE_UE_HEIGHT_M OVERRIDE_OUTPUT_DIR ...
       OVERRIDE_OUTPUT_FILENAME OVERRIDE_USER_ID OVERRIDE_CHANNEL_SEED;

OVERRIDE_CONFIG_NAME     = config_name;
OVERRIDE_WALK_SEED       = profile(4);
OVERRIDE_N_RX_ANTENNAS   = profile(1);
OVERRIDE_ANTENNA_GAIN_DB  = profile(2);
OVERRIDE_UE_HEIGHT_M     = profile(3);
OVERRIDE_OUTPUT_DIR      = output_dir;
OVERRIDE_OUTPUT_FILENAME  = out_filename;
OVERRIDE_USER_ID         = user_idx;
OVERRIDE_CHANNEL_SEED    = [];  % not used in normal multi-user runs

%% Run simulation
run_start = tic;
generate_simulation_data;
elapsed = toc(run_start);

fprintf('=== User %d complete in %.1fs [%s] ===\n', user_idx, elapsed, datestr(now));

%% Clear globals and force memory cleanup
OVERRIDE_CONFIG_NAME     = [];
OVERRIDE_WALK_SEED       = [];
OVERRIDE_N_RX_ANTENNAS   = [];
OVERRIDE_ANTENNA_GAIN_DB  = [];
OVERRIDE_UE_HEIGHT_M     = [];
OVERRIDE_OUTPUT_DIR      = [];
OVERRIDE_OUTPUT_FILENAME  = [];
OVERRIDE_USER_ID         = [];
OVERRIDE_CHANNEL_SEED    = [];

% Force garbage collection of QuaDRiGa handle objects
clearvars -except user_idx profile output_dir config_name workspace_root;
java.lang.System.gc();

diary off;
end
