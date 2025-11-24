%% Experiment 12: CSI Distribution Study at Fixed Grid Locations
% Study the statistical distribution of CSI measurements at fixed UE positions
%
% Purpose:
%   - Understand CSI variability at each location
%   - Characterize statistical properties (mean, variance, distribution)
%   - Study spatial patterns of CSI across the environment
%   - Create a probabilistic map of CSI values
%
% Configuration:
%   - 200x200m plane with BS at center
%   - 20x20 grid (400 locations)
%   - 100 CSI samples per location
%   - 5G network at 3 GHz
%   - Heterogeneous environment (LOS and NLOS)
%
% Output:
%   - CSI statistics at each grid point (mean, std, percentiles)
%   - Spatial heatmaps of CSI metrics
%   - Distribution plots at sample locations
%   - Complete dataset for further analysis
%
% Expected runtime: 30-90 minutes

clear; close all; clc;

%% Setup
fprintf('========================================\n');
fprintf('EXP12: CSI DISTRIBUTION STUDY\n');
fprintf('========================================\n\n');

% Add utils to path
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);

% Load configuration
run('config_csi_distribution.m');

%% Check for Incomplete Previous Runs
results_root = fullfile(project_root, 'results');
exp12_dirs = dir(fullfile(results_root, 'exp12_*'));
incomplete_runs = {};
start_ix = 1;
start_iy = 1;
resume_mode = false;

% Find ALL incomplete exp12 runs (those with progress.mat)
for i = 1:length(exp12_dirs)
    check_dir = fullfile(results_root, exp12_dirs(i).name);
    check_progress = fullfile(check_dir, 'progress', 'progress.mat');
    
    if exist(check_progress, 'file')
        incomplete_runs{end+1} = check_dir;
    end
end

% Select the most recent incomplete run (if any)
incomplete_run = [];
if ~isempty(incomplete_runs)
    if length(incomplete_runs) == 1
        % Only one incomplete run - use it
        incomplete_run = incomplete_runs{1};
    else
        % Multiple incomplete runs - show options and ask user
        fprintf('========================================\n');
        fprintf('MULTIPLE INCOMPLETE RUNS FOUND\n');
        fprintf('========================================\n\n');
        
        % Sort by directory name (timestamp) descending
        run_names = cell(size(incomplete_runs));
        for j = 1:length(incomplete_runs)
            [~, run_names{j}] = fileparts(incomplete_runs{j});
        end
        [~, sort_idx] = sort(run_names);
        sort_idx = flipud(sort_idx(:));  % Reverse to get descending order
        sorted_runs = incomplete_runs(sort_idx);
        
        % Display options with details
        for i = 1:length(sorted_runs)
            [~, run_name] = fileparts(sorted_runs{i});
            progress_file_temp = fullfile(sorted_runs{i}, 'progress', 'progress.mat');
            progress_temp = load(progress_file_temp);
            
            fprintf('[%d] %s\n', i, run_name);
            fprintf('    Progress: %d/%d points (%.1f%%) | Time: %.1f min\n\n', ...
                progress_temp.progress_data.points_completed, ...
                progress_temp.progress_data.total_points, ...
                100 * progress_temp.progress_data.points_completed / progress_temp.progress_data.total_points, ...
                progress_temp.progress_data.elapsed_time / 60);
        end
        
        fprintf('[0] Start fresh experiment\n\n');
        
        % Ask user which one to resume
        choice = input(sprintf('Select run to resume [0-%d]: ', length(sorted_runs)));
        
        if choice >= 1 && choice <= length(sorted_runs)
            incomplete_run = sorted_runs{choice};
        else
            fprintf('\n✓ Starting fresh experiment\n\n');
            incomplete_run = [];
        end
    end
end

if ~isempty(incomplete_run)
    fprintf('========================================\n');
    fprintf('INCOMPLETE RUN FOUND\n');
    fprintf('========================================\n\n');
    
    % Load progress from the incomplete run
    resume_file = fullfile(incomplete_run, 'progress', 'progress.mat');
    progress_data = load(resume_file);
    
    [~, run_name] = fileparts(incomplete_run);
    fprintf('Found incomplete run: %s\n', run_name);
    fprintf('  Last completed: Grid point [%d, %d]\n', ...
        progress_data.progress_data.last_ix, progress_data.progress_data.last_iy);
    fprintf('  Points completed: %d/%d (%.1f%%)\n', ...
        progress_data.progress_data.points_completed, ...
        progress_data.progress_data.total_points, ...
        100 * progress_data.progress_data.points_completed / progress_data.progress_data.total_points);
    fprintf('  Time elapsed: %.1f minutes\n\n', progress_data.progress_data.elapsed_time / 60);
    
    % Automatically resume (no prompt needed)
    fprintf('▶ Auto-resuming from last checkpoint...\n\n');
    resume_mode = true;
    
    % Use the existing output directory
    output_dir = incomplete_run;
    
    % Calculate next point to process
    last_ix = progress_data.progress_data.last_ix;
    last_iy = progress_data.progress_data.last_iy;
    
    % Move to next point
    if last_ix < progress_data.progress_data.n_x
        start_ix = last_ix + 1;
        start_iy = last_iy;
    else
        start_ix = 1;
        start_iy = last_iy + 1;
    end
    
    fprintf('✓ Resuming from grid point [%d, %d]\n', start_ix, start_iy);
else
    % Create new output directory for fresh run
    fprintf('Starting fresh experiment...\n');
    output_dir = ExperimentUtils.createResultsDir('exp12');
end

% Setup directory structure
data_dir = fullfile(output_dir, 'data');
plots_dir = fullfile(output_dir, 'plots');
stats_dir = fullfile(output_dir, 'statistics');
progress_dir = fullfile(output_dir, 'progress');

% Create directories if they don't exist (for fresh runs)
if ~exist(data_dir, 'dir'), mkdir(data_dir); end
if ~exist(plots_dir, 'dir'), mkdir(plots_dir); end
if ~exist(stats_dir, 'dir'), mkdir(stats_dir); end
if ~exist(progress_dir, 'dir'), mkdir(progress_dir); end

fprintf('Output directory: %s\n\n', output_dir);

% Save configuration (for fresh runs only)
if ~resume_mode
    config_file = fullfile(progress_dir, 'experiment_config.mat');
    save(config_file, 'config', '-v7.3');
    fprintf('✓ Configuration saved for crash recovery\n\n');
end

% Set resume_file path for later use
resume_file = fullfile(progress_dir, 'progress.mat');

%% Initialize QuaDRiGa
fprintf('Initializing QuaDRiGa...\n');

% Create simulation parameters
s = qd_simulation_parameters;
s.center_frequency = config.scenario.frequency;
s.use_absolute_delays = config.quadriga.use_absolute_delays;
s.show_progress_bars = config.quadriga.show_progress_bars;
s.sample_density = 2;

% Create layout
l = qd_layout(s);

% Configure base station (single BS at center)
l.no_tx = 1;
l.tx_position(:, 1) = config.bs.position;
l.tx_array(1) = qd_arrayant('omni');

% Set scenario
l.set_scenario(config.scenario.type);

fprintf('✓ QuaDRiGa initialized\n');
fprintf('  BS position: [%.1f, %.1f, %.1f] m\n', ...
    config.bs.position(1), config.bs.position(2), config.bs.position(3));
fprintf('  Scenario: %s\n', config.scenario.type);
fprintf('  Frequency: %.2f GHz\n\n', s.center_frequency / 1e9);

%% Initialize Storage Arrays
fprintf('Allocating storage arrays...\n');

% Get grid dimensions
n_x = config.grid.grid_points(1);
n_y = config.grid.grid_points(2);
n_samples = config.grid.n_samples_per_point;

% Load existing data if resuming
if resume_mode && exist(fullfile(stats_dir, 'csi_statistics.mat'), 'file')
    fprintf('Loading existing statistics...\n');
    stats_temp = load(fullfile(stats_dir, 'csi_statistics.mat'));
    stats = stats_temp.stats;
    
    if config.output.save_raw_samples && exist(fullfile(data_dir, 'all_samples.mat'), 'file')
        fprintf('Loading existing samples...\n');
        samples_temp = load(fullfile(data_dir, 'all_samples.mat'));
        all_samples = samples_temp.all_samples;
    end
    fprintf('✓ Existing data loaded\n');
else
    % Initialize new storage
    stats = struct();
    
    % Mean values (spatial maps)
    stats.mean_RSS = zeros(n_y, n_x);
    stats.mean_SINR = zeros(n_y, n_x);
    stats.mean_CQI = zeros(n_y, n_x);
    stats.mean_path_loss = zeros(n_y, n_x);
    
    % Standard deviation (spatial maps)
    stats.std_RSS = zeros(n_y, n_x);
    stats.std_SINR = zeros(n_y, n_x);
    stats.std_CQI = zeros(n_y, n_x);
    
    % Distance from BS
    stats.distance = zeros(n_y, n_x);
    
    % All samples (for detailed analysis)
    if config.output.save_raw_samples
        all_samples = struct();
        all_samples.RSS = zeros(n_y, n_x, n_samples);
        all_samples.SINR = zeros(n_y, n_x, n_samples);
        all_samples.CQI = zeros(n_y, n_x, n_samples);
        all_samples.H_mag_wb = zeros(n_y, n_x, n_samples);
        all_samples.H_freq = zeros(n_y, n_x, config.scenario.n_subcarriers, n_samples);
    end
end

% CSI metrics calculator
m = CSIMetrics('SubcarrierSpacing', config.scenario.bandwidth / config.scenario.n_subcarriers, ...
               'TxPowerPerSC_dBm', config.bs.tx_power_dbm - 10*log10(config.scenario.n_subcarriers), ...
               'NoiseFigure_dB', config.ue.noise_figure_db);

fprintf('✓ Storage allocated\n');
fprintf('  Grid points: %d x %d = %d\n', n_x, n_y, n_x * n_y);
fprintf('  Samples per point: %d\n', n_samples);
fprintf('  Total simulations: %d\n', n_x * n_y * n_samples);
if resume_mode
    completed_points = (start_iy - 1) * n_x + (start_ix - 1);
    fprintf('  Already completed: %d points\n', completed_points);
    fprintf('  Remaining: %d points\n', n_x * n_y - completed_points);
end
fprintf('\n');

%% Main Simulation Loop
fprintf('========================================\n');
fprintf('SIMULATING CSI AT GRID POINTS\n');
fprintf('========================================\n\n');

total_start_time = tic;
simulation_start_time = datetime('now');
fprintf('Simulation started at: %s\n\n', datestr(simulation_start_time));

% Progress tracking
total_points = n_x * n_y;
if resume_mode
    point_counter = (start_iy - 1) * n_x + (start_ix - 1);
else
    point_counter = 0;
end
update_interval = max(1, round(total_points / 20));  % Update every 5%

% Frequency vector for channel computation
fvec = linspace(-config.scenario.bandwidth/2, config.scenario.bandwidth/2, config.scenario.n_subcarriers);

% Loop over grid points - start from resume point
for iy = start_iy:n_y
    % Determine starting ix for this row
    if iy == start_iy && resume_mode
        ix_start = start_ix;
    else
        ix_start = 1;
    end
    
    for ix = ix_start:n_x
        point_start_time = tic;
        point_counter = point_counter + 1;
        
        fprintf('\n[%d/%d] Processing grid point [%d, %d] at (%.1fm, %.1fm)...\n', ...
                point_counter, total_points, ix, iy, ...
                config.grid.x_coords(iy, ix), config.grid.y_coords(iy, ix));
        
        % Get UE position for this grid point
        ue_x = config.grid.x_coords(iy, ix);
        ue_y = config.grid.y_coords(iy, ix);
        ue_z = config.grid.z_height;
        ue_position = [ue_x; ue_y; ue_z];
        
        % Calculate distance to BS
        distance = norm(ue_position - config.bs.position);
        stats.distance(iy, ix) = distance;
        fprintf('  Distance to BS: %.1f m\n', distance);
        
        % Arrays to store samples at this point
        RSS_samples = zeros(n_samples, 1);
        SINR_samples = zeros(n_samples, 1);
        CQI_samples = zeros(n_samples, 1);
        H_mag_wb_samples = zeros(n_samples, 1);
        
        fprintf('  Simulating %d CSI samples...', n_samples);
        sample_start_time = tic;
        
        % Simulate n_samples CSI observations at this fixed location
        for sample_idx = 1:n_samples
            % Create fresh layout for each sample to avoid builder warning
            l_temp = qd_layout(s);
            l_temp.no_tx = 1;
            l_temp.tx_position(:, 1) = config.bs.position;
            l_temp.tx_array(1) = qd_arrayant('omni');
            
            % Create a single-point track at this location
            track = qd_track('linear', 0);
            track.initial_position = ue_position;
            track.positions = ue_position;
            track.no_snapshots = 1;
            track.scenario = config.scenario.type;
            
            % Randomly assign LOS or NLOS based on probability
            if rand < config.scenario.los_probability
                track.scenario = strrep(config.scenario.type, 'UMi', 'UMi_LOS');
            else
                track.scenario = strrep(config.scenario.type, 'UMi', 'UMi_NLOS');
            end
            
            % Add track to layout
            l_temp.track(1, 1) = track;
            l_temp.rx_array = qd_arrayant('omni');
            
            % Generate channel
            c = l_temp.get_channels();
            
            % Extract channel coefficients and delays
            h_t = squeeze(c.coeff(:, :, :, 1));
            tau = squeeze(c.delay(:, :, 1));
            
            % Convert to column vectors
            h_t = h_t(:);
            tau = tau(:);
            
            % Ensure same length
            n_taps = min(length(h_t), length(tau));
            h_t = h_t(1:n_taps);
            tau = tau(1:n_taps);
            
            % Remove zero-power taps
            valid_idx = abs(h_t) > 1e-10;
            h_t = h_t(valid_idx);
            tau = tau(valid_idx);
            
            % Handle empty case
            if isempty(h_t)
                h_t = 1e-10;
                tau = 0;
            end
            
            % Convert to frequency domain
            H_freq = zeros(config.scenario.n_subcarriers, 1);
            for k = 1:config.scenario.n_subcarriers
                H_freq(k) = sum(h_t .* exp(-1j * 2*pi * fvec(k) .* tau));
            end
            
            % Reshape for CSIMetrics
            H_freq_3d = reshape(H_freq, 1, 1, config.scenario.n_subcarriers);
            
            % Compute CSI metrics
            metrics = m.compute(H_freq_3d);
            
            % Store samples
            RSS_samples(sample_idx) = metrics.RSS_dBm_wb;
            SINR_samples(sample_idx) = metrics.SINR_dB_wb;
            CQI_samples(sample_idx) = metrics.CQI_wb;
            H_mag_wb_samples(sample_idx) = 10*log10(mean(abs(H_freq).^2));
            
            % Store frequency response if saving raw samples
            if config.output.save_raw_samples
                all_samples.H_freq(iy, ix, :, sample_idx) = H_freq;
            end
        end
        
        sample_time = toc(sample_start_time);
        fprintf(' Done (%.2f sec)\n', sample_time);
        
        % Compute statistics for this grid point
        stats.mean_RSS(iy, ix) = mean(RSS_samples);
        stats.mean_SINR(iy, ix) = mean(SINR_samples);
        stats.mean_CQI(iy, ix) = mean(CQI_samples);
        
        stats.std_RSS(iy, ix) = std(RSS_samples);
        stats.std_SINR(iy, ix) = std(SINR_samples);
        stats.std_CQI(iy, ix) = std(CQI_samples);
        
        % Path loss (average over samples)
        stats.mean_path_loss(iy, ix) = config.bs.tx_power_dbm - stats.mean_RSS(iy, ix);
        
        % Display statistics for this point
        fprintf('  Statistics computed:\n');
        fprintf('    RSS:  mu=%.2f dBm, sigma=%.2f dB\n', stats.mean_RSS(iy, ix), stats.std_RSS(iy, ix));
        fprintf('    SINR: mu=%.2f dB,   sigma=%.2f dB\n', stats.mean_SINR(iy, ix), stats.std_SINR(iy, ix));
        fprintf('    CQI:  mu=%.2f,      sigma=%.2f\n', stats.mean_CQI(iy, ix), stats.std_CQI(iy, ix));
        
        % Store all samples if requested
        if config.output.save_raw_samples
            all_samples.RSS(iy, ix, :) = RSS_samples;
            all_samples.SINR(iy, ix, :) = SINR_samples;
            all_samples.CQI(iy, ix, :) = CQI_samples;
            all_samples.H_mag_wb(iy, ix, :) = H_mag_wb_samples;
        end
        
        % Save progress after each grid point (for crash recovery)
        elapsed = toc(total_start_time);
        point_total_time = toc(point_start_time);
        progress_data = struct();
        progress_data.last_ix = ix;
        progress_data.last_iy = iy;
        progress_data.points_completed = point_counter;
        progress_data.total_points = total_points;
        progress_data.elapsed_time = elapsed;
        progress_data.n_x = n_x;
        progress_data.n_y = n_y;
        save(resume_file, 'progress_data', '-v7.3');
        
        % Also save current statistics to disk
        save(fullfile(stats_dir, 'csi_statistics.mat'), 'stats', '-v7.3');
        if config.output.save_raw_samples
            save(fullfile(data_dir, 'all_samples.mat'), 'all_samples', '-v7.3');
        end
        fprintf('  checkmark Progress saved to disk\n');
        
        % Display timing information for this point
        fprintf('  Point timing: %.2f sec total (%.3f sec/sample)\n', ...
            point_total_time, point_total_time / n_samples);
        
        % Overall progress update
        est_total = elapsed / point_counter * total_points;
        est_remaining = est_total - elapsed;
        
        fprintf('  Overall Progress: %d/%d points (%.1f%%) | Elapsed: %.1f min | ETA: %.1f min\n', ...
            point_counter, total_points, 100 * point_counter / total_points, ...
            elapsed / 60, est_remaining / 60);
    end
end

total_time = toc(total_start_time);
simulation_end_time = datetime('now');
total_duration = simulation_end_time - simulation_start_time;

% Delete progress file on successful completion
if exist(resume_file, 'file')
    delete(resume_file);
end

fprintf('\n========================================\n');
fprintf('SIMULATION COMPLETE!\n');
fprintf('========================================\n\n');
fprintf('Timing Summary:\n');
fprintf('  Start time:    %s\n', datestr(simulation_start_time));
fprintf('  End time:      %s\n', datestr(simulation_end_time));
fprintf('  Total duration: %s\n', char(total_duration));
fprintf('  Total time:    %.1f minutes (%.2f hours)\n', total_time / 60, total_time / 3600);
fprintf('  Time per point: %.2f seconds\n', total_time / total_points);
fprintf('  Time per sample: %.3f seconds\n', total_time / (total_points * n_samples));
fprintf('  Total samples simulated: %d\n\n', total_points * n_samples);

%% Save Final Results
fprintf('Saving final results...\n');

%% Save Final Results
fprintf('Saving final results...\n');

% Save statistics (already saved during loop, but final save for confirmation)
save(fullfile(stats_dir, 'csi_statistics.mat'), 'stats', '-v7.3');
fprintf('  ✓ Statistics saved\n');

% Save raw samples if requested (already saved during loop)
if config.output.save_raw_samples
    save(fullfile(data_dir, 'all_samples.mat'), 'all_samples', '-v7.3');
    fprintf('  ✓ Raw samples saved\n');
end

% Save grid configuration
grid_info = struct();
grid_info.x_coords = config.grid.x_coords;
grid_info.y_coords = config.grid.y_coords;
grid_info.bs_position = config.bs.position;
grid_info.n_samples_per_point = n_samples;
save(fullfile(data_dir, 'grid_info.mat'), 'grid_info');
fprintf('  ✓ Grid info saved\n\n');

%% Generate Visualizations
if config.output.generate_plots
    fprintf('========================================\n');
    fprintf('GENERATING VISUALIZATIONS\n');
    fprintf('========================================\n\n');
    
    %% Plot 1: Mean RSS Heatmap
    fprintf('Creating RSS heatmap...\n');
    fig1 = ExperimentUtils.createFigure('Exp12 - Mean RSS Heatmap', 'square');
    
    imagesc(config.grid.x_coords(1, :), config.grid.y_coords(:, 1), stats.mean_RSS);
    hold on;
    plot(config.bs.position(1), config.bs.position(2), 'w^', ...
        'MarkerSize', 20, 'MarkerFaceColor', 'r', 'LineWidth', 2);
    hold off;
    
    colorbar;
    xlabel('X Position (m)');
    ylabel('Y Position (m)');
    title('Mean RSS (dBm) - 100 samples per location');
    set(gca, 'YDir', 'normal');
    colormap(jet);
    axis equal tight;
    
    ExperimentUtils.saveFigures(fig1, 'mean_rss_heatmap', plots_dir);
    
    %% Plot 2: Mean SINR Heatmap
    fprintf('Creating SINR heatmap...\n');
    fig2 = ExperimentUtils.createFigure('Exp12 - Mean SINR Heatmap', 'square');
    
    imagesc(config.grid.x_coords(1, :), config.grid.y_coords(:, 1), stats.mean_SINR);
    hold on;
    plot(config.bs.position(1), config.bs.position(2), 'w^', ...
        'MarkerSize', 20, 'MarkerFaceColor', 'r', 'LineWidth', 2);
    hold off;
    
    colorbar;
    xlabel('X Position (m)');
    ylabel('Y Position (m)');
    title('Mean SINR (dB) - 100 samples per location');
    set(gca, 'YDir', 'normal');
    colormap(jet);
    axis equal tight;
    
    ExperimentUtils.saveFigures(fig2, 'mean_sinr_heatmap', plots_dir);
    
    %% Plot 3: Standard Deviation of RSS
    fprintf('Creating RSS variability heatmap...\n');
    fig3 = ExperimentUtils.createFigure('Exp12 - RSS Std Deviation', 'square');
    
    imagesc(config.grid.x_coords(1, :), config.grid.y_coords(:, 1), stats.std_RSS);
    hold on;
    plot(config.bs.position(1), config.bs.position(2), 'w^', ...
        'MarkerSize', 20, 'MarkerFaceColor', 'r', 'LineWidth', 2);
    hold off;
    
    colorbar;
    xlabel('X Position (m)');
    ylabel('Y Position (m)');
    title('RSS Standard Deviation (dB) - Variability at each location');
    set(gca, 'YDir', 'normal');
    colormap(hot);
    axis equal tight;
    
    ExperimentUtils.saveFigures(fig3, 'rss_std_heatmap', plots_dir);
    
    %% Plot 4: Mean CQI Heatmap
    fprintf('Creating CQI heatmap...\n');
    fig4 = ExperimentUtils.createFigure('Exp12 - Mean CQI', 'square');
    
    imagesc(config.grid.x_coords(1, :), config.grid.y_coords(:, 1), stats.mean_CQI);
    hold on;
    plot(config.bs.position(1), config.bs.position(2), 'w^', ...
        'MarkerSize', 20, 'MarkerFaceColor', 'r', 'LineWidth', 2);
    hold off;
    
    colorbar;
    caxis([0 15]);
    xlabel('X Position (m)');
    ylabel('Y Position (m)');
    title('Mean CQI (0-15) - 100 samples per location');
    set(gca, 'YDir', 'normal');
    colormap(jet);
    axis equal tight;
    
    ExperimentUtils.saveFigures(fig4, 'mean_cqi_heatmap', plots_dir);
    
    %% Plot 5: Path Loss vs Distance
    fprintf('Creating path loss analysis...\n');
    fig5 = ExperimentUtils.createFigure('Exp12 - Path Loss vs Distance', 'wide');
    
    subplot(1, 2, 1);
    scatter(stats.distance(:), stats.mean_path_loss(:), 50, stats.mean_RSS(:), 'filled');
    colorbar;
    xlabel('Distance from BS (m)');
    ylabel('Mean Path Loss (dB)');
    title('Path Loss vs Distance');
    grid on;
    
    subplot(1, 2, 2);
    scatter(stats.distance(:), stats.std_RSS(:), 50, stats.mean_RSS(:), 'filled');
    colorbar;
    xlabel('Distance from BS (m)');
    ylabel('RSS Std Deviation (dB)');
    title('RSS Variability vs Distance');
    grid on;
    
    ExperimentUtils.saveFigures(fig5, 'pathloss_analysis', plots_dir);
    
    %% Plot 6: Distribution at Sample Points
    if config.output.save_raw_samples && config.output.plot_distributions
        fprintf('Creating distribution plots...\n');
        
        % Select sample points (corners and center)
        sample_points = [
            1, 1;           % Bottom-left corner
            n_x, 1;         % Bottom-right corner
            1, n_y;         % Top-left corner
            n_x, n_y;       % Top-right corner
            round(n_x/2), round(n_y/2)  % Center
        ];
        
        fig6 = ExperimentUtils.createFigure('Exp12 - CSI Distributions', 'wide');
        
        for i = 1:size(sample_points, 1)
            ix = sample_points(i, 1);
            iy = sample_points(i, 2);
            
            subplot(2, 3, i);
            
            RSS_vals = squeeze(all_samples.RSS(iy, ix, :));
            histogram(RSS_vals, 20, 'FaceColor', [0.3 0.6 0.9], 'EdgeAlpha', 0.5);
            
            xlabel('RSS (dBm)');
            ylabel('Frequency');
            title(sprintf('Point [%.0f, %.0f]m - d=%.1fm', ...
                config.grid.x_coords(iy, ix), ...
                config.grid.y_coords(iy, ix), ...
                stats.distance(iy, ix)));
            grid on;
            
            % Add statistics
            text(0.05, 0.95, sprintf('μ=%.1f\nσ=%.1f', ...
                stats.mean_RSS(iy, ix), stats.std_RSS(iy, ix)), ...
                'Units', 'normalized', 'VerticalAlignment', 'top', ...
                'BackgroundColor', 'white', 'EdgeColor', 'black');
        end
        
        ExperimentUtils.saveFigures(fig6, 'csi_distributions', plots_dir);
    end
    
    %% Plot 7: 3D Surface Plot
    if config.output.plot_3d
        fprintf('Creating 3D visualization...\n');
        fig7 = ExperimentUtils.createFigure('Exp12 - 3D RSS Surface', 'wide');
        
        surf(config.grid.x_coords, config.grid.y_coords, stats.mean_RSS);
        hold on;
        plot3(config.bs.position(1), config.bs.position(2), ...
            max(stats.mean_RSS(:)), 'r^', 'MarkerSize', 20, 'MarkerFaceColor', 'r');
        hold off;
        
        xlabel('X Position (m)');
        ylabel('Y Position (m)');
        zlabel('Mean RSS (dBm)');
        title('3D View: Mean RSS across the plane');
        colorbar;
        colormap(jet);
        shading interp;
        view(-45, 30);
        
        ExperimentUtils.saveFigures(fig7, 'rss_3d_surface', plots_dir);
    end
    
    fprintf('\n✓ All visualizations generated\n\n');
end

%% Generate Report
fprintf('Generating experiment report...\n');

fid = ExperimentUtils.createReportHeader(output_dir, 'EXPERIMENT 12: CSI DISTRIBUTION STUDY');

fprintf(fid, '--- EXPERIMENT OVERVIEW ---\n');
fprintf(fid, 'Purpose: Study statistical distribution of CSI at fixed grid locations\n');
fprintf(fid, 'Approach: Simulate 100 CSI samples at each of 400 grid points\n\n');

fprintf(fid, '--- CONFIGURATION ---\n');
fprintf(fid, 'Plane size: %.0f x %.0f meters\n', ...
    config.grid.plane_size(1), config.grid.plane_size(2));
fprintf(fid, 'Grid resolution: %d x %d = %d points\n', ...
    n_x, n_y, n_x * n_y);
fprintf(fid, 'Grid spacing: %.2f x %.2f meters\n', ...
    config.grid.spacing_x, config.grid.spacing_y);
fprintf(fid, 'Samples per point: %d\n', n_samples);
fprintf(fid, 'Total simulations: %d\n\n', n_x * n_y * n_samples);

fprintf(fid, '--- NETWORK PARAMETERS ---\n');
fprintf(fid, 'Technology: 5G\n');
fprintf(fid, 'Frequency: %.1f GHz\n', config.scenario.frequency / 1e9);
fprintf(fid, 'Bandwidth: %.0f MHz\n', config.scenario.bandwidth / 1e6);
fprintf(fid, 'Subcarriers: %d\n', config.scenario.n_subcarriers);
fprintf(fid, 'Scenario: %s\n', config.scenario.type);
fprintf(fid, 'LOS Probability: %.0f%%\n\n', config.scenario.los_probability * 100);

fprintf(fid, '--- BASE STATION ---\n');
fprintf(fid, 'Position: [%.1f, %.1f, %.1f] m (center of plane)\n', ...
    config.bs.position(1), config.bs.position(2), config.bs.position(3));
fprintf(fid, 'TX Power: %d dBm\n', config.bs.tx_power_dbm);
fprintf(fid, 'Antennas: %d\n\n', config.bs.n_antennas);

fprintf(fid, '--- STATISTICS SUMMARY ---\n');
fprintf(fid, 'Mean RSS: %.2f ± %.2f dBm\n', ...
    mean(stats.mean_RSS(:)), std(stats.mean_RSS(:)));
fprintf(fid, 'RSS range: [%.2f, %.2f] dBm\n', ...
    min(stats.mean_RSS(:)), max(stats.mean_RSS(:)));
fprintf(fid, '\nMean SINR: %.2f ± %.2f dB\n', ...
    mean(stats.mean_SINR(:)), std(stats.mean_SINR(:)));
fprintf(fid, 'SINR range: [%.2f, %.2f] dB\n', ...
    min(stats.mean_SINR(:)), max(stats.mean_SINR(:)));
fprintf(fid, '\nMean CQI: %.2f ± %.2f\n', ...
    mean(stats.mean_CQI(:)), std(stats.mean_CQI(:)));
fprintf(fid, 'CQI range: [%.0f, %.0f]\n\n', ...
    min(stats.mean_CQI(:)), max(stats.mean_CQI(:)));

fprintf(fid, '--- VARIABILITY ANALYSIS ---\n');
fprintf(fid, 'Average RSS std dev: %.2f dB\n', mean(stats.std_RSS(:)));
fprintf(fid, 'RSS std dev range: [%.2f, %.2f] dB\n', ...
    min(stats.std_RSS(:)), max(stats.std_RSS(:)));
fprintf(fid, '\nAverage SINR std dev: %.2f dB\n', mean(stats.std_SINR(:)));
fprintf(fid, 'SINR std dev range: [%.2f, %.2f] dB\n', ...
    min(stats.std_SINR(:)), max(stats.std_SINR(:)));
fprintf(fid, '\nAverage CQI std dev: %.2f\n', mean(stats.std_CQI(:)));
fprintf(fid, 'CQI std dev range: [%.2f, %.2f]\n\n', ...
    min(stats.std_CQI(:)), max(stats.std_CQI(:)));

fprintf(fid, '--- DISTANCE ANALYSIS ---\n');
fprintf(fid, 'Distance range: %.1f to %.1f meters\n', ...
    min(stats.distance(:)), max(stats.distance(:)));
fprintf(fid, 'Mean distance: %.1f ± %.1f meters\n\n', ...
    mean(stats.distance(:)), std(stats.distance(:)));

fprintf(fid, '--- RUNTIME ---\n');
fprintf(fid, 'Total time: %.1f minutes\n', total_time / 60);
fprintf(fid, 'Time per grid point: %.2f seconds\n', total_time / total_points);
fprintf(fid, 'Time per sample: %.3f seconds\n\n', total_time / (total_points * n_samples));

files_generated = {
    'statistics/csi_statistics.mat',
    'data/grid_info.mat',
    'plots/mean_rss_heatmap.png',
    'plots/mean_sinr_heatmap.png',
    'plots/rss_std_heatmap.png',
    'plots/mean_cqi_heatmap.png',
    'plots/pathloss_analysis.png'
};

if config.output.save_raw_samples
    files_generated{end+1} = 'data/all_samples.mat';
    if config.output.plot_distributions
        files_generated{end+1} = 'plots/csi_distributions.png';
    end
end

if config.output.plot_3d
    files_generated{end+1} = 'plots/rss_3d_surface.png';
end

ExperimentUtils.closeReport(fid, files_generated);
fprintf('✓ Report saved\n\n');

%% Summary
fprintf('========================================\n');
fprintf('EXPERIMENT 12 COMPLETE!\n');
fprintf('========================================\n\n');

fprintf('📊 Simulated: %d grid points × %d samples = %d total\n', ...
    total_points, n_samples, total_points * n_samples);
fprintf('📁 Output: %s\n', output_dir);
fprintf('⏱️  Runtime: %.1f minutes\n\n', total_time / 60);

fprintf('Key Findings:\n');
fprintf('  • Mean RSS: %.2f ± %.2f dBm\n', ...
    mean(stats.mean_RSS(:)), std(stats.mean_RSS(:)));
fprintf('  • Average variability: %.2f dB std\n', mean(stats.std_RSS(:)));
fprintf('  • Distance range: %.1f - %.1f m\n\n', ...
    min(stats.distance(:)), max(stats.distance(:)));

fprintf('🎯 Next Steps:\n');
fprintf('  1. Analyze CSI distribution patterns\n');
fprintf('  2. Fit statistical models (Gaussian, Rayleigh, etc.)\n');
fprintf('  3. Study correlation between nearby points\n');
fprintf('  4. Use for probabilistic localization\n\n');

fprintf('========================================\n');
