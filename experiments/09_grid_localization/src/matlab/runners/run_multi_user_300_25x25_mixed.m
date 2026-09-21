%% Run Multi-User Diversity Simulation — 300 Users 25x25 Grid, MIXED LOS/NLOS
% Campaign B, corrected propagation.
%
% WHY THIS FILE EXISTS
% --------------------
% run_multi_user_300_25x25.m loads ne_bs_voronoi_25x25_config.jsonc, which
% declares channel.mixed_scenario.enabled = true with four Voronoi cells — two
% UMi_LOS (highway, park) and two UMi_NLOS (shopping_center, residential). That
% runner never reads the mixed_scenario block. It calls
%   l.set_scenario(config_json.channel.scenario)
% and assigns
%   trk.scenario = {config_json.channel.scenario}
% to every track, so every user in the original Campaign B ran under a single
% uniform 3GPP_38.901_UMi_NLOS profile. The LOS regions were configured and
% silently dropped.
%
% Downstream this mattered: environment_viz.py draws the four cells, and
% experiments_ablation/history_gain_by_zone.py labels samples LOS/NLOS by nearest
% Voronoi centre. Those labels were attached to a homogeneous NLOS map, so the
% "LOS vs NLOS" breakdown was really two arbitrary geometric region groups.
%
% A second defect, in core/generate_simulation_data.m, is also fixed here. That
% file builds one scenario string per *segment*, but never sets segment_index, so
% a qd_track carries its default single segment and the whole walk inherits the
% scenario of its first position. Per-position mixing needs explicit segments,
% which is what build_scenario_segments below creates.
%
% Serving BS: [116, 116, 10]   IBS-1: [-60, 53, 10]   IBS-2: [53, -60, 10]
%
% Requires quadriga_src on the MATLAB path (QuaDRiGa 2.8.1).

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
                      'grid_25x25', sprintf('sim_data_300users_mixed_%s', timestamp));
mkdir(output_dir);

mat_dir = fullfile(output_dir, 'mat_files');
mkdir(mat_dir);

log_dir = fullfile(output_dir, 'logs');
mkdir(log_dir);
main_log = fullfile(log_dir, sprintf('main_%s.log', timestamp));
diary(main_log);
diary on;

fprintf('============================================================\n');
fprintf('=== 300-User Simulation, MIXED LOS/NLOS Voronoi Scenarios ===\n');
fprintf('Start time:       %s\n', datestr(now));
fprintf('Output directory: %s\n', output_dir);
fprintf('============================================================\n\n');

config_name = 'ne_bs_voronoi_25x25_config.jsonc';
config_file = fullfile(experiment_root, 'configs', config_name);
config_json = read_jsonc(config_file);

center_freq = config_json.channel.center_frequency;  % 3.0 GHz
bandwidth   = config_json.channel.bandwidth;         % 100 MHz
n_sc        = config_json.channel.n_subcarriers;     % 256

%% Mixed-scenario setup — the part the original runner skipped
if ~isfield(config_json.channel, 'mixed_scenario') || ...
   ~config_json.channel.mixed_scenario.enabled
    error(['This runner requires channel.mixed_scenario.enabled = true in %s. ' ...
           'For the uniform-NLOS baseline use run_multi_user_300_25x25.m.'], config_name);
end

vcells = config_json.channel.mixed_scenario.voronoi_cells;
n_cells = length(vcells);
voronoi_centers   = zeros(n_cells, 2);
voronoi_scenarios = cell(n_cells, 1);
voronoi_names     = cell(n_cells, 1);
for i = 1:n_cells
    cd_i = vcells(i);
    voronoi_centers(i, :) = cd_i.center;
    voronoi_scenarios{i}  = cd_i.scenario;
    voronoi_names{i}      = cd_i.name;
end

fprintf('Mixed propagation map (%d Voronoi cells):\n', n_cells);
for i = 1:n_cells
    fprintf('  %-16s %-24s at [%5.1f, %5.1f]\n', ...
        voronoi_names{i}, voronoi_scenarios{i}, ...
        voronoi_centers(i, 1), voronoi_centers(i, 2));
end
fprintf('\n');

% Segments shorter than this are absorbed into the preceding segment. QuaDRiGa
% merges adjacent segments over an overlap region; one- or two-snapshot segments
% produced by a track grazing a cell boundary give the merger nothing to work
% with and inflate the segment count for no physical gain.
MIN_SEG_LEN = 4;

n_users = 300;                 % 300 Users total
batch_size = 25;               % 25 Users per QuaDRiGa layout
n_batches = ceil(n_users / batch_size);
rng(42);                       % same manifest as the uniform-NLOS run

%% 1. Generate Manifest for 300 Users
% Columns: [n_ant, gain_db, height_m, walk_seed, speed_ms, n_steps, pat_id]
% Identical draw order to run_multi_user_300_25x25.m, so the two runs differ only
% in propagation and remain directly comparable user by user.
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
zone_hist = zeros(n_cells, 1);   % global occupancy, for the run summary

%% 2. Process Users — one independent single-scenario channel per Voronoi segment
%
% WHY NOT A SINGLE MERGED MULTI-SEGMENT TRACK (as Job 1 originally attempted)
% -----------------------------------------------------------------------------
% qd_channel/merge.m computes its path-index mapping once, from a track's FIRST
% segment (see init_path_indices.m), and reuses it unchanged for every later
% segment. 3GPP_38.901_UMi_LOS has 12 clusters, _NLOS has 20 — a different
% no_path — so merge() crashes with a dimension mismatch at the first snapshot
% where a user's walk actually crosses an LOS/NLOS boundary. This is
% deterministic, not seed- or tuning-dependent: it hit every user whose walk
% left its starting propagation regime.
%
% Generating each segment as its own single-scenario, single-segment track
% sidesteps merge() entirely. The cost is losing QuaDRiGa's spatial-consistency
% correlation of large-scale parameters *across* a segment boundary; checked
% against the scenario configs, SC_lambda (7-15 m for both scenarios) is far
% shorter than a typical segment (28-128 m for MIN_SEG_LEN=4 at 2 m spacing),
% so this discards at most one correlation-length's worth of continuity at each
% boundary, out of a segment far longer than that. The ML pipeline downstream
% only consumes scalar rss/sinr/aoa per snapshot, never raw channel
% coefficients, so coefficient-level phase continuity across the boundary was
% never something this project measures.

bs_pos = [116; 116; 10];
ibs_pos = [-60, 53, 10; 53, -60, 10];  % Pushed SW & South towers

for b = 1:n_batches
    u_start = (b-1)*batch_size + 1;
    u_end   = min(b*batch_size, n_users);
    batch_u_ids = u_start:u_end;
    n_batch_u = length(batch_u_ids);

    fprintf('>>> Processing Batch %d/%d (Users %d to %d)...\n', b, n_batches, u_start, u_end);
    batch_tic = tic;
    seg_counts_batch = zeros(n_batch_u, 1);

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

        % ── assign every snapshot to its Voronoi cell ────────────────────────
        d2 = (x_pts - voronoi_centers(:, 1)').^2 + (y_pts - voronoi_centers(:, 2)').^2;
        [~, cell_idx_per_step] = min(d2, [], 2);          % n_steps x 1
        for c = 1:n_cells
            zone_hist(c) = zone_hist(c) + sum(cell_idx_per_step == c);
        end

        [seg_start, seg_cell] = build_scenario_segments(cell_idx_per_step, MIN_SEG_LEN);
        n_segments = numel(seg_start);
        seg_counts_batch(idx) = n_segments;
        seg_end = [seg_start(2:end) - 1, n_steps];

        rss    = zeros(n_steps, 1);
        sinr   = zeros(n_steps, 1);
        aoa_az = zeros(n_steps, 1);
        aoa_el = zeros(n_steps, 1);
        n_valid = 0;   % contiguous count actually filled; a mid-walk clamp stops here

        for k = 1:n_segments
            lo = seg_start(k);
            hi = seg_end(k);
            seg_len = hi - lo + 1;
            scen = voronoi_scenarios{seg_cell(k)};

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
            % No underscore in the name: QuaDRiGa's internal channel naming
            % (get_channels.m, merge.m) splits track names on the FIRST
            % underscore expecting exactly "TxName_RxName" — an underscore
            % inside the rx track name itself breaks that parsing.
            trk.name = sprintf('UE%dS%d', uid, k);
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
            truncated = n_avail < seg_len;
            if truncated
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

            n_valid = lo + seg_len - 1;
            if truncated
                break;   % keep the filled prefix contiguous; do not fill past a clamp
            end
        end

        n_steps = n_valid;
        if n_steps < prof(6)
            fprintf('    user %d: %d/%d snapshots valid after per-segment clamping\n', uid, n_steps, prof(6));
        end

        step_index    = (1:n_steps)';
        grid_point_id = w_idx(1:n_steps);
        user_id_val   = uid;
        speed_ms      = speed;
        x_pos         = x_pts(1:n_steps);
        y_pos         = y_pts(1:n_steps);
        rss           = rss(1:n_steps);
        sinr          = sinr(1:n_steps);
        aoa_az        = aoa_az(1:n_steps);
        aoa_el        = aoa_el(1:n_steps);

        delta_t = (spacing_m / speed) * ones(n_steps, 1);
        timestamp_sec = cumsum(delta_t) - delta_t(1);

        % Real Voronoi cell membership per snapshot. The uniform-NLOS runner
        % saved grid_point_id under this name, which is why the Python side had
        % to re-derive zones from coordinates.
        voronoi_cell_id   = cell_idx_per_step(1:n_steps);
        voronoi_scenario  = voronoi_scenarios(voronoi_cell_id);
        voronoi_zone_name = voronoi_names(voronoi_cell_id);
        is_los = ~cellfun(@isempty, strfind(voronoi_scenario, '_LOS'));  %#ok<STRCL1>

        device_profile = struct('n_antennas', n_ant, ...
                                'antenna_gain_db', gain_db, ...
                                'ue_height', h_m);

        user_file = fullfile(mat_dir, sprintf('user%d_ne_bs_25x25.mat', uid));
        save(user_file, 'rss', 'sinr', 'aoa_az', 'aoa_el', 'delta_t', ...
             'timestamp_sec', 'step_index', 'grid_point_id', 'user_id_val', ...
             'speed_ms', 'x_pos', 'y_pos', 'voronoi_cell_id', 'voronoi_scenario', ...
             'voronoi_zone_name', 'is_los', 'device_profile', 'user_manifest');
    end

    fprintf('  Propagation segments per user: min %d, median %d, max %d\n', ...
        min(seg_counts_batch), round(median(seg_counts_batch)), max(seg_counts_batch));
    fprintf('  Batch %d completed in %.1f seconds.\n', b, toc(batch_tic));
end

%% 3. Save Experiment Info & Json Config
fprintf('\nGlobal zone occupancy:\n');
tot = sum(zone_hist);
for i = 1:n_cells
    fprintf('  %-16s %-24s %8d samples (%.1f%%)\n', voronoi_names{i}, ...
        voronoi_scenarios{i}, zone_hist(i), 100 * zone_hist(i) / tot);
end

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
experiment_info.mixed_scenario = true;
experiment_info.voronoi_centers   = voronoi_centers;
experiment_info.voronoi_scenarios = voronoi_scenarios;
experiment_info.voronoi_names     = voronoi_names;
experiment_info.zone_sample_counts = zone_hist;
experiment_info.total_time_s   = toc(total_start);

save(fullfile(output_dir, 'experiment_info.mat'), 'experiment_info');

sim_config = struct();
sim_config.network_type           = '5G NR Sub-6 GHz';
sim_config.center_frequency_ghz   = center_freq / 1e9;
sim_config.bandwidth_mhz          = bandwidth / 1e6;
sim_config.n_subcarriers          = n_sc;
sim_config.quadriga_scenario      = 'mixed_voronoi';
sim_config.mixed_scenario         = true;
sim_config.voronoi_cells          = vcells;
sim_config.min_segment_length     = MIN_SEG_LEN;
% Each Voronoi segment is its own independent single-scenario QuaDRiGa channel
% (no qd_channel/merge across segments) — see the note above the batch loop.
% Large-scale parameters are not spatially correlated across a segment
% boundary; within a segment they are, exactly as in the uniform-NLOS baseline.
sim_config.channel_generation      = 'per_segment_independent';
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
fprintf('=== Mixed LOS/NLOS 300-User Simulation Completed! ===\n');
fprintf('Total time elapsed: %.2f minutes\n', toc(total_start)/60);
fprintf('Output: %s\n', output_dir);
fprintf('============================================================\n');

diary off;


%% ── helpers ──────────────────────────────────────────────────────────────────
function [seg_start, seg_cell] = build_scenario_segments(cell_idx, min_len)
% BUILD_SCENARIO_SEGMENTS Contiguous runs of a single Voronoi cell.
%
% QuaDRiGa takes one scenario per track segment, and derives no_segments from
% segment_index. Without an explicit segment_index a track has exactly one
% segment, so the whole walk silently inherits its first position's scenario —
% the defect in core/generate_simulation_data.m.
%
% Runs shorter than min_len are folded into the preceding segment: QuaDRiGa
% merges neighbouring segments across an overlap region, and a two-snapshot
% segment gives that merge nothing to work with.
%
% Input:
%   cell_idx - n x 1 Voronoi cell index per snapshot
%   min_len  - minimum snapshots per segment
%
% Output:
%   seg_start - 1 x k start indices, strictly increasing, seg_start(1) == 1
%   seg_cell  - 1 x k cell index for each segment

    n = numel(cell_idx);
    if n == 0
        seg_start = 1; seg_cell = 1; return;
    end

    % raw run boundaries
    starts = [1; find(diff(cell_idx(:)) ~= 0) + 1];
    cells  = cell_idx(starts);

    % absorb short runs into the previous segment
    keep_start = starts(1);
    keep_cell  = cells(1);
    for i = 2:numel(starts)
        run_end = (i < numel(starts)) * (starts(min(i + 1, numel(starts))) - 1) ...
                  + (i == numel(starts)) * n;
        if run_end - starts(i) + 1 >= min_len
            keep_start(end + 1, 1) = starts(i);  %#ok<AGROW>
            keep_cell(end + 1, 1)  = cells(i);   %#ok<AGROW>
        end
    end

    seg_start = keep_start(:)';
    seg_cell  = keep_cell(:)';
end
