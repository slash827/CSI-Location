%% Run Fast Multi-User Diversity Simulation — 25x25 Voronoi Grid (5G NR 3.0 GHz)
% Generates 200 mobile users in shared QuaDRiGa multi-user layouts.
% Exports MAT files into output_dir/mat_files/ and writes simulation_config.json
% and simulation_summary.md for full experiment documentation.
%
% NETWORK SETUP:
%   5G Network: 3.0 GHz Carrier Frequency, 100 MHz Bandwidth, 256 Subcarriers
%   QuaDRiGa Model: 3GPP 38.901 UMi NLOS / Mixed Voronoi Cells
%   Grid: 25x25, spacing=4m, offset=[5,5]  =>  X,Y in [5,101]
%   Serving BS: [116, 116, 10]  (NE Corner)
%   IBS-1:      [-25, 53, 10]
%   IBS-2:      [53, -25, 10]
%
% DIVERSITY PROFILES (200 Users across 8 Batches of 25 UEs):
%   - Steps per user: N_steps ~ U(400, 600)
%   - Mobility Classes: Pedestrians (40%), Joggers (25%), Vehicles (25%), Static (10%)
%   - Trajectory Patterns: Billiards, Momentum Walk, Waypoint Tour, Straight Transit
%   - Hardware Profiles: 1, 2, 4 antennas, Gain [-4, +2] dB, Height [0.8, 1.8] m

clear; clc; close all;

%% Paths
script_dir      = fileparts(mfilename('fullpath'));
src_matlab_dir  = fileparts(script_dir);
experiment_root = fileparts(fileparts(src_matlab_dir));     % 09_grid_localization/
workspace_root  = fileparts(fileparts(experiment_root));    % CSI-Location/

addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
addpath(fullfile(workspace_root, 'utils'));

%% Setup Output Directory & Sub-directories
timestamp  = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
output_dir = fullfile(workspace_root, 'results', 'grid_localization', ...
                      'grid_25x25', sprintf('sim_data_200users_%s', timestamp));
mkdir(output_dir);

mat_dir = fullfile(output_dir, 'mat_files');
mkdir(mat_dir);

log_dir = fullfile(output_dir, 'logs');
mkdir(log_dir);
main_log = fullfile(log_dir, sprintf('main_%s.log', timestamp));
diary(main_log);
diary on;

fprintf('============================================================\n');
fprintf('=== Fast 5G NR (3.0 GHz) Multi-User Simulation (Shared Layout) ===\n');
fprintf('Start time:       %s\n', datestr(now));
fprintf('Output directory: %s\n', output_dir);
fprintf('MAT files dir:    %s\n', mat_dir);
fprintf('============================================================\n\n');

config_name = 'ne_bs_voronoi_25x25_config.jsonc';
config_file = fullfile(experiment_root, 'configs', config_name);
config_json = read_jsonc(config_file);

center_freq = config_json.channel.center_frequency;  % 3.0 GHz
bandwidth   = config_json.channel.bandwidth;         % 100 MHz
n_sc        = config_json.channel.n_subcarriers;     % 256

n_users = 200;                 % 200 Users total
batch_size = 25;               % 25 Users per QuaDRiGa layout
n_batches = ceil(n_users / batch_size);
rng(42);

%% 1. Generate Manifest for 200 Users
% Columns: [n_ant, gain_db, height_m, walk_seed, speed_ms, n_steps, pat_id]
user_manifest = zeros(n_users, 7);
for u = 1:n_users
    roll = rand();
    if roll <= 0.40,     speed = 1.0 + rand() * 0.5;   % Pedestrian 1.0-1.5 m/s
    elseif roll <= 0.65, speed = 2.5 + rand() * 2.0;   % Jogger 2.5-4.5 m/s
    elseif roll <= 0.90, speed = 8.0 + rand() * 7.0;   % Vehicle 8.0-15.0 m/s
    else,                speed = 0.1 + rand() * 0.4;   % Static 0.1-0.5 m/s
    end
    
    p_roll = rand();
    if p_roll <= 0.35, pat_id = 1;        % Billiards
    elseif p_roll <= 0.70, pat_id = 2;    % Momentum Walk
    elseif p_roll <= 0.90, pat_id = 3;    % Waypoint Tour
    else, pat_id = 4;                     % Straight Transit
    end
    
    ants = [1, 2, 4]; n_ant = ants(randi(3));
    gain = -4.0 + rand() * 6.0;
    height = 0.8 + rand() * 1.0;
    n_steps = randi([400, 600]);         % U(400, 600) steps
    walk_seed = 1000 + u;
    
    user_manifest(u, :) = [n_ant, gain, height, walk_seed, speed, n_steps, pat_id];
end

fprintf('Manifest generated for %d users (%d batches of %d users):\n', n_users, n_batches, batch_size);
fprintf('  Carrier Frequency: %.2f GHz (5G NR Band n78)\n', center_freq / 1e9);
fprintf('  Bandwidth:         %.1f MHz (%d Subcarriers)\n', bandwidth / 1e6, n_sc);
fprintf('  Total trajectory steps: %d\n\n', sum(user_manifest(:, 6)));

total_start = tic;

%% 2. Process Batches in Shared QuaDRiGa Multi-User Layouts
for b = 1:n_batches
    u_start = (b-1)*batch_size + 1;
    u_end   = min(b*batch_size, n_users);
    batch_u_ids = u_start:u_end;
    n_batch_u = length(batch_u_ids);
    
    fprintf('>>> Processing Batch %d/%d (Users %d to %d)...\n', b, n_batches, u_start, u_end);
    batch_tic = tic;
    
    % Initialize Shared QuaDRiGa Layout
    l = qd_layout;
    l.set_scenario(config_json.channel.scenario);
    l.simpar.center_frequency = center_freq;  % 3.0 GHz 5G Frequency
    
    % Configure BSs (Serving + 2 Interferers)
    bs_pos = reshape(config_json.base_station.position, 3, 1);
    ibs_pos = config_json.base_station.interferers.positions;
    if iscell(ibs_pos)
        ibs_pos = cell2mat(cellfun(@(x) x(:)', ibs_pos, 'UniformOutput', false));
    end
    
    l.no_tx = 3;
    l.tx_position(:, 1) = bs_pos;
    l.tx_array(1) = qd_arrayant('omni');
    for i = 1:2
        l.tx_position(:, i+1) = ibs_pos(i, :)';
        l.tx_array(i+1) = qd_arrayant('omni');
    end
    
    l.no_rx = n_batch_u;
    
    % Build trajectories and rx_tracks for all users in this batch
    user_paths = cell(n_batch_u, 1);
    for idx = 1:n_batch_u
        uid = batch_u_ids(idx);
        prof = user_manifest(uid, :);
        n_ant = prof(1); gain_db = prof(2); h_m = prof(3); seed = prof(4);
        speed = prof(5); n_steps = prof(6); pat_id = prof(7);
        
        % Generate Trajectory
        pattern_names = {'billiards', 'momentum_walk', 'waypoint_tour', 'straight_transit'};
        pat_name = pattern_names{pat_id};
        grid_sz = config_json.grid.size(1);
        spacing_m = config_json.grid.spacing;
        grid_offset = config_json.grid.grid_offset;
        
        [walk_indices, ~] = generate_diverse_trajectories(grid_sz, n_steps, pat_name, speed, spacing_m, seed);
        
        w_idx = walk_indices(1:n_steps);
        rows = ceil(w_idx / grid_sz);
        cols = mod(w_idx - 1, grid_sz) + 1;
        x_pts = (cols - 1) * spacing_m + grid_offset(1);
        y_pts = (rows - 1) * spacing_m + grid_offset(2);
        
        positions = [x_pts, y_pts, ones(n_steps, 1) * h_m];
        user_paths{idx} = struct('x', x_pts, 'y', y_pts, 'grid_id', w_idx, ...
                                 'positions', positions, 'speed', speed, 'n_steps', n_steps, ...
                                 'n_ant', n_ant, 'gain_db', gain_db, 'h_m', h_m);
        
        % Attach Track to Layout with Unique Name
        l.rx_array(idx) = qd_arrayant('omni');
        if n_ant > 1
            l.rx_array(idx).no_elements = n_ant;
        end
        trk = qd_track('linear', 0, 0);
        trk.name = sprintf('UE%d', uid);
        trk.positions = positions';
        trk.scenario = {config_json.channel.scenario};
        l.rx_track(idx) = trk;
    end
    
    % Generate Channels for ALL Users simultaneously in vectorized call
    fprintf('  Generating 5G QuaDRiGa multi-user channel coefficients (%.2f GHz)...\n', center_freq/1e9);
    ch = l.get_channels();
    
    % Extract & Save Per-User Data into mat_files/
    fprintf('  Extracting CSI metrics and saving per-user MAT files to mat_files/...\n');
    for idx = 1:n_batch_u
        uid = batch_u_ids(idx);
        up  = user_paths{idx};
        n_steps = up.n_steps;
        
        if iscell(ch)
            ch_u = ch{idx, 1}; ch_i1 = ch{idx, 2}; ch_i2 = ch{idx, 3};
        else
            ch_u = ch(idx, 1); ch_i1 = ch(idx, 2); ch_i2 = ch(idx, 3);
        end
        
        rss  = zeros(n_steps, 1);
        sinr = zeros(n_steps, 1);
        aoa_az = zeros(n_steps, 1);
        aoa_el = zeros(n_steps, 1);
        
        delta_t = (config_json.grid.spacing / up.speed) * ones(n_steps, 1);
        timestamp_sec = cumsum(delta_t) - delta_t(1);
        
        for t = 1:n_steps
            H_t = ch_u.fr(bandwidth, n_sc, t);
            if up.n_ant > 1
                H_eff = sqrt(sum(abs(H_t).^2, 1));
            else
                H_eff = H_t;
            end
            
            p_serving = mean(abs(H_eff(:)).^2) * 1e-3;
            
            H_i1 = ch_i1.fr(bandwidth, n_sc, t);
            H_i2 = ch_i2.fr(bandwidth, n_sc, t);
            
            p_i1 = mean(abs(H_i1(:)).^2) * 1e-3;
            p_i2 = mean(abs(H_i2(:)).^2) * 1e-3;
            p_interf = p_i1 + p_i2;
            
            p_noise = 10^((-174 + 10*log10(bandwidth/n_sc) + 7 - 30)/10);
            
            rss(t)  = 10 * log10(p_serving * 1000) + up.gain_db;
            sinr(t) = 10 * log10(p_serving / (p_interf + p_noise));
            
            dx = up.x(t) - bs_pos(1);
            dy = up.y(t) - bs_pos(2);
            dz = up.h_m - bs_pos(3);
            aoa_az(t) = atan2d(dx, dy);
            aoa_el(t) = -atan2d(dz, sqrt(dx^2 + dy^2));
        end
        
        % Save MAT file in mat_files/ sub-directory
        mat_filename = sprintf('user%d_ne_bs_25x25.mat', uid);
        out_filepath = fullfile(mat_dir, mat_filename);
        
        device_profile = struct('n_antennas', up.n_ant, 'antenna_gain_db', up.gain_db, 'ue_height_m', up.h_m);
        
        save(out_filepath, 'rss', 'sinr', 'aoa_az', 'aoa_el', 'delta_t', 'timestamp_sec', ...
             'device_profile', 'user_manifest');
        
        x_pos = up.x; y_pos = up.y; grid_point_id = up.grid_id; voronoi_cell_id = ones(n_steps, 1);
        step_index = (1:n_steps)'; user_id_val = uid; speed_ms = up.speed;
        save(out_filepath, 'x_pos', 'y_pos', 'grid_point_id', 'voronoi_cell_id', ...
             'step_index', 'user_id_val', 'speed_ms', '-append');
    end
    
    b_time = toc(batch_tic);
    elapsed_total = toc(total_start);
    eta_min = (elapsed_total / b) * (n_batches - b) / 60;
    fprintf('[PROGRESS] Batch %d/%d Complete in %.1fs | Total Elapsed: %.1f min | ETA: %.1f min\n\n', ...
        b, n_batches, b_time, elapsed_total/60, eta_min);
    
    clear l ch;
    java.lang.System.gc();
end

total_time = toc(total_start);
fprintf('============================================================\n');
fprintf('ALL %d USERS SIMULATED SUCCESSFULLY in %.2f minutes (%.1f seconds)!\n', n_users, total_time/60, total_time);
fprintf('Average time per user: %.2f seconds\n', total_time/n_users);
fprintf('============================================================\n\n');

%% Save Manifest Metadata & JSON/MD Document Reports
experiment_info = struct();
experiment_info.config_name   = config_name;
experiment_info.n_users       = n_users;
experiment_info.user_manifest = user_manifest;
experiment_info.output_dir    = output_dir;
experiment_info.mat_dir       = mat_dir;
experiment_info.timestamp     = timestamp;
experiment_info.bs_position   = bs_pos;
experiment_info.center_freq_hz= center_freq;
experiment_info.bandwidth_hz  = bandwidth;
experiment_info.total_time_s  = total_time;
save(fullfile(output_dir, 'experiment_info.mat'), 'experiment_info');

% Write simulation_config.json
cfg_out = struct();
cfg_out.network_type = '5G NR Sub-6 GHz';
cfg_out.center_frequency_ghz = center_freq / 1e9;
cfg_out.bandwidth_mhz = bandwidth / 1e6;
cfg_out.n_subcarriers = n_sc;
cfg_out.quadriga_scenario = config_json.channel.scenario;
cfg_out.serving_bs_position_m = bs_pos';
cfg_out.n_users = n_users;
cfg_out.total_trajectory_steps = sum(user_manifest(:, 6));
cfg_out.mat_files_directory = 'mat_files';
cfg_out.timestamp = timestamp;

fid = fopen(fullfile(output_dir, 'simulation_config.json'), 'w');
if fid ~= -1
    fwrite(fid, jsonencode(cfg_out, 'PrettyPrint', true));
    fclose(fid);
end

% Write simulation_summary.md
summary_md = sprintf([ ...
'# 5G NR Simulation Experiment Report\n\n' ...
'## 1. Network & Hardware Configuration\n' ...
'- **Network Standard:** 5G NR (Sub-6 GHz Band n78)\n' ...
'- **Carrier Frequency:** %.2f GHz\n' ...
'- **Channel Bandwidth:** %.1f MHz\n' ...
'- **Subcarriers:** %d\n' ...
'- **QuaDRiGa Channel Model:** %s\n' ...
'- **Serving BS Position:** [%.1f, %.1f, %.1f] m\n\n' ...
'## 2. Multi-User Mobility & Diversity Profile\n' ...
'- **Total Mobile Users:** %d users\n' ...
'- **Total Trajectory Steps:** %d samples\n' ...
'- **Steps Per User:** U(400, 600) steps\n' ...
'- **Sub-directory for MAT files:** `mat_files/`\n' ...
'- **Simulation Timestamp:** %s\n' ...
'- **Total Simulation Runtime:** %.2f minutes (%.1f s)\n' ...
], center_freq/1e9, bandwidth/1e6, n_sc, config_json.channel.scenario, ...
bs_pos(1), bs_pos(2), bs_pos(3), n_users, sum(user_manifest(:, 6)), timestamp, total_time/60, total_time);

fid_md = fopen(fullfile(output_dir, 'simulation_summary.md'), 'w');
if fid_md ~= -1
    fwrite(fid_md, summary_md);
    fclose(fid_md);
end

diary off;
