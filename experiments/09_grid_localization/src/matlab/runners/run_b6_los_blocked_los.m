%% Run B6 — LOS -> blocked (NLOS) -> LOS targeted scenario
% Straight-line trajectories at constant speed crossing a rectangular NLOS
% strip between two LOS regions. The case where history should be decisive:
% during the blocked interval a snapshot model has almost nothing, while a
% history model carries the pre-blockage heading through.
%
% WHY PER-SEGMENT INDEPENDENT CHANNELS (not a single merged multi-segment
% track)
% -----------------------------------------------------------------------------
% qd_channel/merge.m computes its path-index mapping once, from a track's
% FIRST segment, and reuses it unchanged for every later segment
% (init_path_indices.m). 3GPP_38.901_UMi_LOS has 12 clusters, _NLOS has 20 —
% a different no_path — so merge() crashes with a dimension mismatch the
% moment a merged track actually crosses an LOS/NLOS boundary. This was
% discovered and fixed in run_multi_user_300_25x25_mixed.m (Job 1); B6 *is*
% that boundary by construction, so the same fix is mandatory here, not
% optional. Each of the three segments (LOS-in, NLOS-strip, LOS-out) is
% generated as its own independent single-scenario, single-segment qd_track
% with its own get_channels() call.
%
% Track names must not contain an underscore: QuaDRiGa's own channel-naming
% convention (get_channels.m, merge.m) splits on the FIRST underscore
% expecting exactly "TxName_RxName"; an underscore inside the rx track name
% itself breaks that parsing (see Job 1's CONTINUE_HERE.md §3).

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
output_dir = fullfile(workspace_root, 'results', 'b6_los_blocked_los', ...
                      sprintf('sim_data_b6_%s', timestamp));
mkdir(output_dir);

mat_dir = fullfile(output_dir, 'mat_files');
mkdir(mat_dir);

log_dir = fullfile(output_dir, 'logs');
mkdir(log_dir);
main_log = fullfile(log_dir, sprintf('main_%s.log', timestamp));
diary(main_log);
diary on;

fprintf('============================================================\n');
fprintf('=== B6: LOS -> blocked (NLOS) -> LOS straight-line crossing ===\n');
fprintf('Start time:       %s\n', datestr(now));
fprintf('Output directory: %s\n', output_dir);
fprintf('============================================================\n\n');

config_name = 'b6_los_blocked_los_config.jsonc';
config_file = fullfile(experiment_root, 'configs', config_name);
config_json = read_jsonc(config_file);

center_freq = config_json.channel.center_frequency;
bandwidth   = config_json.channel.bandwidth;
n_sc        = config_json.channel.n_subcarriers;
los_scen    = config_json.channel.los_scenario;
nlos_scen   = config_json.channel.nlos_scenario;

corridor_len   = config_json.corridor.length_m;
y_pos_fixed    = config_json.corridor.y_pos_m;
strip_widths   = config_json.corridor.strip_widths_m;
speeds         = config_json.corridor.speeds_ms;
n_repeats      = config_json.corridor.repeats_per_combo;
dt_sample      = config_json.corridor.sample_interval_s;

bs_pos  = config_json.base_station.position(:);
ibs_pos = config_json.base_station.interferers.positions;  % 2x3, already numeric

fprintf('Corridor: length %.0f m, %d strip widths x %d speeds x %d repeats = %d users\n', ...
    corridor_len, numel(strip_widths), numel(speeds), n_repeats, ...
    numel(strip_widths) * numel(speeds) * n_repeats);
fprintf('Serving BS: [%.0f, %.0f, %.0f]\n\n', bs_pos(1), bs_pos(2), bs_pos(3));

%% 1. Build user manifest — every (strip_width, speed) combo x n_repeats
% Columns: [n_ant, gain_db, height_m, seed, speed_ms, strip_width_m]
rng(42);
manifest_rows = {};
uid = 0;
for wi = 1:numel(strip_widths)
    for si = 1:numel(speeds)
        for r = 1:n_repeats
            uid = uid + 1;
            ants = [1, 2, 4]; n_ant = ants(randi(3));
            gain = -4.0 + rand() * 6.0;
            height = 0.8 + rand() * 1.0;
            seed = 2000 + uid;
            manifest_rows{uid} = [n_ant, gain, height, seed, speeds(si), strip_widths(wi)]; %#ok<AGROW>
        end
    end
end
n_users = uid;
user_manifest = cell2mat(manifest_rows(:));

fprintf('Manifest generated for %d users.\n\n', n_users);

total_start = tic;
n_blocked_total = 0;
n_total_samples = 0;

%% 2. Process each user — 3 independent single-scenario segments
for uid = 1:n_users
    prof = user_manifest(uid, :);
    n_ant = prof(1); gain_db = prof(2); h_m = prof(3); seed = prof(4);
    speed = prof(5); width = prof(6);

    rng(seed);

    % Straight line x in [0, corridor_len] at fixed y, sampled at a fixed
    % rate (not grid-snapped) so distance-per-sample scales with speed.
    step_dist = speed * dt_sample;
    n_steps = floor(corridor_len / step_dist) + 1;
    x_pts = (0:n_steps-1)' * step_dist;
    x_pts = min(x_pts, corridor_len);
    y_pts = ones(n_steps, 1) * y_pos_fixed;
    positions = [x_pts, y_pts, ones(n_steps, 1) * h_m];

    % Blocking strip centred in x: [ (L-W)/2, (L+W)/2 ]
    strip_lo = (corridor_len - width) / 2;
    strip_hi = (corridor_len + width) / 2;
    in_strip = x_pts >= strip_lo & x_pts <= strip_hi;
    is_los = ~in_strip;

    % Three contiguous segments: LOS-in, NLOS-strip, LOS-out. A strip so
    % narrow it fits inside one sample still gets its own (short) segment —
    % unlike Job 1's Voronoi crossings there is no MIN_SEG_LEN absorption
    % here, because the blocked interval IS the measurement of interest,
    % never a boundary artefact to be smoothed away.
    seg_bounds = [1; find(diff(in_strip) ~= 0) + 1; n_steps + 1];
    seg_bounds = unique(seg_bounds);
    n_segments = numel(seg_bounds) - 1;

    rss    = zeros(n_steps, 1);
    sinr   = zeros(n_steps, 1);
    aoa_az = zeros(n_steps, 1);
    aoa_el = zeros(n_steps, 1);

    for k = 1:n_segments
        lo = seg_bounds(k);
        hi = seg_bounds(k+1) - 1;
        seg_len = hi - lo + 1;
        scen = los_scen;
        if in_strip(lo)
            scen = nlos_scen;
        end

        l_seg = qd_layout;
        l_seg.simpar.center_frequency = center_freq;
        l_seg.no_tx = 3;
        l_seg.tx_position(:, 1) = bs_pos;
        l_seg.tx_array(1) = qd_arrayant('omni');
        for i = 1:2
            l_seg.tx_position(:, i+1) = ibs_pos(i, :)';
            l_seg.tx_array(i+1) = qd_arrayant('omni');
        end
        l_seg.no_rx = 1;
        l_seg.rx_array(1) = qd_arrayant('omni');
        if n_ant > 1
            l_seg.rx_array(1).no_elements = n_ant;
        end

        trk = qd_track('linear', 0, 0);
        trk.name = sprintf('B6U%dS%d', uid, k);   % no underscore — see header note
        trk.positions = positions(lo:hi, :)';
        trk.scenario = {scen};
        l_seg.rx_track(1) = trk;

        ch = l_seg.get_channels();
        if iscell(ch)
            ch_u = ch{1, 1}; ch_i1 = ch{1, 2}; ch_i2 = ch{1, 3};
        else
            ch_u = ch(1, 1); ch_i1 = ch(1, 2); ch_i2 = ch(1, 3);
        end

        n_avail = min([ch_u.no_snap, ch_i1.no_snap, ch_i2.no_snap]);
        if n_avail < seg_len
            fprintf('    user %d segment %d: channel has %d snapshots for %d positions, truncating\n', ...
                uid, k, n_avail, seg_len);
            seg_len = n_avail;
        end

        for t = 1:seg_len
            H_t = ch_u.fr(bandwidth, n_sc, t);
            if n_ant > 1
                H_t = reshape(H_t, n_ant, n_sc);
            end
            p_sig = mean(abs(H_t(:)).^2);

            H_i1 = ch_i1.fr(bandwidth, n_sc, t);
            H_i2 = ch_i2.fr(bandwidth, n_sc, t);
            p_int = mean(abs(H_i1(:)).^2) + mean(abs(H_i2(:)).^2);
            p_noise = 10^(-104/10) * 0.001;

            gidx = lo + t - 1;
            rss(gidx)  = 10 * log10(max(p_sig, 1e-15) / 0.001) + gain_db;
            sinr(gidx) = 10 * log10(max(p_sig, 1e-15) / (p_int + p_noise));

            dx = bs_pos(1) - x_pts(gidx);
            dy = bs_pos(2) - y_pts(gidx);
            dz = bs_pos(3) - h_m;
            d_2d = sqrt(dx^2 + dy^2);

            if n_ant > 1
                aoa_az(gidx) = atan2d(dx, dy);
                aoa_el(gidx) = atan2d(dz, max(d_2d, 0.1));
            else
                aoa_az(gidx) = 0.0;
                aoa_el(gidx) = 0.0;
            end
        end
    end

    step_index    = (1:n_steps)';
    user_id_val   = uid;
    speed_ms      = speed;
    x_pos         = x_pts;
    y_pos         = y_pts;
    delta_t       = dt_sample * ones(n_steps, 1);
    timestamp_sec = cumsum(delta_t) - delta_t(1);
    strip_width_m = width;
    in_blocked_segment = in_strip;

    n_blocked_total = n_blocked_total + sum(in_strip);
    n_total_samples = n_total_samples + n_steps;

    device_profile = struct('n_antennas', n_ant, ...
                            'antenna_gain_db', gain_db, ...
                            'ue_height', h_m);

    user_file = fullfile(mat_dir, sprintf('user%d_b6.mat', uid));
    save(user_file, 'rss', 'sinr', 'aoa_az', 'aoa_el', 'delta_t', ...
         'timestamp_sec', 'step_index', 'user_id_val', 'speed_ms', ...
         'x_pos', 'y_pos', 'is_los', 'strip_width_m', 'in_blocked_segment', ...
         'device_profile', 'user_manifest');

    if mod(uid, 10) == 0
        fprintf('  ... %d/%d users done (%.1f min elapsed)\n', uid, n_users, toc(total_start)/60);
    end
end

%% 3. Save Experiment Info & Json Config
fprintf('\nBlocked-interval samples: %d / %d (%.1f%%)\n', ...
    n_blocked_total, n_total_samples, 100 * n_blocked_total / n_total_samples);

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
experiment_info.strip_widths_m = strip_widths;
experiment_info.speeds_ms      = speeds;
experiment_info.total_time_s   = toc(total_start);

save(fullfile(output_dir, 'experiment_info.mat'), 'experiment_info');

sim_config = struct();
sim_config.network_type          = '5G NR Sub-6 GHz';
sim_config.center_frequency_ghz  = center_freq / 1e9;
sim_config.bandwidth_mhz         = bandwidth / 1e6;
sim_config.n_subcarriers         = n_sc;
sim_config.quadriga_scenario     = 'b6_los_blocked_los';
sim_config.channel_generation    = 'per_segment_independent';
sim_config.corridor_length_m     = corridor_len;
sim_config.strip_widths_m        = strip_widths;
sim_config.speeds_ms             = speeds;
sim_config.sample_interval_s     = dt_sample;
sim_config.serving_bs_position_m = bs_pos';
sim_config.n_users               = n_users;
sim_config.mat_files_directory   = 'mat_files';
sim_config.timestamp             = timestamp;

fid = fopen(fullfile(output_dir, 'simulation_config.json'), 'w');
fprintf(fid, '%s', jsonencode(sim_config));
fclose(fid);

fprintf('\n============================================================\n');
fprintf('=== B6 Simulation Completed! ===\n');
fprintf('Total time elapsed: %.2f minutes\n', toc(total_start)/60);
fprintf('Output: %s\n', output_dir);
fprintf('============================================================\n');

diary off;
