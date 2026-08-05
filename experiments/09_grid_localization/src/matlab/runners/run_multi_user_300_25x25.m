%% Run Fast Multi-User Diversity Simulation — 300 Users 25x25 Grid (5G NR 3.0 GHz)
% Generates 300 mobile users in shared QuaDRiGa multi-user layouts.
% Pushed interferer positions for realistic cell inter-site topology:
%   Serving BS: [116, 116, 10]
%   IBS-1:      [-60,  53, 10] (Pushed West)
%   IBS-2:      [ 53, -60, 10] (Pushed South)

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
                      'grid_25x25', sprintf('sim_data_300users_%s', timestamp));
mkdir(output_dir);

mat_dir = fullfile(output_dir, 'mat_files');
mkdir(mat_dir);

log_dir = fullfile(output_dir, 'logs');
mkdir(log_dir);
main_log = fullfile(log_dir, sprintf('main_%s.log', timestamp));
diary(main_log);
diary on;

fprintf('============================================================\n');
fprintf('=== Fast 5G NR (3.0 GHz) 300-User Simulation (Pushed Cell Towers) ===\n');
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

n_users = 300;                 % 300 Users total
batch_size = 25;               % 25 Users per QuaDRiGa layout
n_batches = ceil(n_users / batch_size);
rng(42);

%% 1. Generate Manifest for 300 Users
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
    n_steps = randi([500, 750]);         % U(500, 750) steps per user
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
    
    % Configure BSs (Serving + 2 Pushed Interferers)
    bs_pos = [116; 116; 10];
    ibs_pos = [-60, 53, 10; 53, -60, 10];  % Pushed SW & South towers
    
    l.no_tx = 3;
    l.tx_position(:, 1) = bs_pos;
    l.tx_array(1) = qd_arrayant('omni');
    for i = 1:2
        l.tx_position(:, i+1) = ibs_pos(i, :)';
        l.tx_array(i+1) = qd_arrayant('omni');
    end
    
    l.no_rx = n_batch_u;
    
    % Build trajectories for all users in batch
    user_paths = cell(n_batch_u, 1);
    for idx = 1:n_batch_u
        uid = batch_u_ids(idx);
        prof = user_manifest(uid, :);
        n_ant = prof(1); gain_db = prof(2); h_m = prof(3); seed = prof(4);
        speed = prof(5); n_steps = prof(6); pat_id = prof(7);
        
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
    
    % Generate Channels
    fprintf('  Generating 5G QuaDRiGa multi-user channel coefficients...\n');
    ch = l.get_channels();
    
    % Save Per-User MAT Files
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
                H_t = reshape(H_t, up.n_ant, n_sc);
            end
            p_sig = mean(abs(H_t(:)).^2);
            
            H_i1 = ch_i1.fr(bandwidth, n_sc, t);
            H_i2 = ch_i2.fr(bandwidth, n_sc, t);
            p_int = mean(abs(H_i1(:)).^2) + mean(abs(H_i2(:)).^2);
            p_noise = 10^(-104/10) * 0.001;
            
            rss(t)  = 10 * log10(max(p_sig, 1e-15) / 0.001) + up.gain_db;
            sinr(t) = 10 * log10(max(p_sig, 1e-15) / (p_int + p_noise));
            
            dx = bs_pos(1) - up.x(t);
            dy = bs_pos(2) - up.y(t);
            dz = bs_pos(3) - up.h_m;
            d_2d = sqrt(dx^2 + dy^2);
            
            if up.n_ant > 1
                aoa_az(t) = atan2d(dx, dy);
                aoa_el(t) = atan2d(dz, max(d_2d, 0.1));
            else
                aoa_az(t) = 0.0;
                aoa_el(t) = 0.0;
            end
        end
        
        step_index    = (1:n_steps)';
        grid_point_id = up.grid_id;
        user_id_val   = uid;
        speed_ms      = up.speed;
        x_pos         = up.x;
        y_pos         = up.y;
        voronoi_cell_id = up.grid_id;
        
        device_profile = struct('n_antennas', up.n_ant, ...
                                'antenna_gain_db', up.gain_db, ...
                                'ue_height', up.h_m);
                            
        user_file = fullfile(mat_dir, sprintf('user%d_ne_bs_25x25.mat', uid));
        save(user_file, 'rss', 'sinr', 'aoa_az', 'aoa_el', 'delta_t', ...
             'timestamp_sec', 'step_index', 'grid_point_id', 'user_id_val', ...
             'speed_ms', 'x_pos', 'y_pos', 'voronoi_cell_id', 'device_profile', ...
             'user_manifest');
    end
    fprintf('  Batch %d completed in %.1f seconds.\n', b, toc(batch_tic));
end

%% 3. Save Experiment Info & Json Config
experiment_info = struct();
experiment_info.config_name    = config_name;
experiment_info.n_users        = n_users;
experiment_info.user_manifest  = user_manifest;
experiment_info.output_dir     = output_dir;
experiment_info.mat_dir        = mat_dir;
experiment_info.timestamp      = timestamp;
experiment_info.bs_position    = bs_pos;
experiment_info.center_freq_hz = center_freq;
experiment_info.bandwidth_hz   = bandwidth;
experiment_info.total_time_s   = toc(total_start);

save(fullfile(output_dir, 'experiment_info.mat'), 'experiment_info');

sim_config = struct();
sim_config.network_type           = '5G NR Sub-6 GHz';
sim_config.center_frequency_ghz   = center_freq / 1e9;
sim_config.bandwidth_mhz          = bandwidth / 1e6;
sim_config.n_subcarriers          = n_sc;
sim_config.quadriga_scenario      = config_json.channel.scenario;
sim_config.serving_bs_position_m  = bs_pos';
sim_config.sw_interferer_position_m = [-60, 53, 10];
sim_config.s_interferer_position_m  = [53, -60, 10];
sim_config.n_users                = n_users;
sim_config.total_trajectory_steps = sum(user_manifest(:, 6));
sim_config.mat_files_directory    = 'mat_files';
sim_config.timestamp              = timestamp;

fid = fopen(fullfile(output_dir, 'simulation_config.json'), 'w');
fprintf(fid, '%s', jsonencode(sim_config));
fclose(fid);

fprintf('\n============================================================\n');
fprintf('=== 300-User Simulation Completed Successfully! ===\n');
fprintf('Total time elapsed: %.2f minutes\n', toc(total_start)/60);
fprintf('============================================================\n');

diary off;
