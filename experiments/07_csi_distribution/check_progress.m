%% Check Progress of Experiment 12
% Quick script to inspect the progress of exp12 run

clear; clc;

% Find the most recent exp12 results folder
results_root = '../../results';
exp12_dirs = dir(fullfile(results_root, 'exp12_*'));
[~, idx] = sort([exp12_dirs.datenum], 'descend');
latest_dir = fullfile(results_root, exp12_dirs(idx(1)).name);

fprintf('========================================\n');
fprintf('EXP12 PROGRESS CHECK\n');
fprintf('========================================\n\n');
fprintf('Checking: %s\n\n', exp12_dirs(idx(1)).name);

% Check if progress file exists
progress_file = fullfile(latest_dir, 'progress', 'progress.mat');
config_file = fullfile(latest_dir, 'progress', 'experiment_config.mat');

if ~exist(progress_file, 'file')
    fprintf('✓ EXPERIMENT COMPLETED SUCCESSFULLY!\n');
    fprintf('  (Progress file deleted upon completion)\n\n');
    
    % Try to load final statistics
    stats_file = fullfile(latest_dir, 'statistics', 'csi_statistics.mat');
    if exist(stats_file, 'file')
        stats_data = load(stats_file);
        fprintf('Final statistics available:\n');
        fprintf('  Grid size: %d x %d\n', size(stats_data.stats.mean_RSS));
        fprintf('  Total points: %d\n\n', numel(stats_data.stats.mean_RSS));
    end
    
    fprintf('========================================\n');
    fprintf('Results directory: %s\n', exp12_dirs(idx(1)).name);
    fprintf('========================================\n\n');
    return;
end

% Load progress data
fprintf('⚠ EXPERIMENT INCOMPLETE\n\n');
progress_data = load(progress_file);
config_data = load(config_file);

fprintf('Configuration:\n');
fprintf('  Grid size: %d x %d (%d points)\n', ...
    config_data.config.grid.grid_points(1), config_data.config.grid.grid_points(2), ...
    config_data.config.grid.grid_points(1) * config_data.config.grid.grid_points(2));
fprintf('  Samples per point: %d\n', config_data.config.grid.n_samples_per_point);
fprintf('  Total samples: %d\n\n', ...
    config_data.config.grid.grid_points(1) * config_data.config.grid.grid_points(2) * ...
    config_data.config.grid.n_samples_per_point);

fprintf('Progress:\n');
fprintf('  Last completed: Grid point [%d, %d]\n', ...
    progress_data.progress_data.last_ix, progress_data.progress_data.last_iy);
fprintf('  Points completed: %d/%d (%.1f%%)\n', ...
    progress_data.progress_data.points_completed, ...
    progress_data.progress_data.total_points, ...
    100 * progress_data.progress_data.points_completed / progress_data.progress_data.total_points);
fprintf('  Time elapsed: %.1f minutes (%.2f hours)\n', ...
    progress_data.progress_data.elapsed_time / 60, ...
    progress_data.progress_data.elapsed_time / 3600);

% Calculate next point
last_ix = progress_data.progress_data.last_ix;
last_iy = progress_data.progress_data.last_iy;
n_x = progress_data.progress_data.n_x;

if last_ix < n_x
    next_ix = last_ix + 1;
    next_iy = last_iy;
else
    next_ix = 1;
    next_iy = last_iy + 1;
end

fprintf('\nNext point to process: [%d, %d]\n', next_ix, next_iy);

% Estimate remaining time
avg_time_per_point = progress_data.progress_data.elapsed_time / progress_data.progress_data.points_completed;
remaining_points = progress_data.progress_data.total_points - progress_data.progress_data.points_completed;
est_remaining = avg_time_per_point * remaining_points;

fprintf('\nEstimated time remaining: %.1f minutes (%.2f hours)\n', ...
    est_remaining / 60, est_remaining / 3600);

fprintf('\n========================================\n');
fprintf('TO RESUME: Simply run exp12_csi_distribution.m\n');
fprintf('  It will automatically resume from last checkpoint\n');
fprintf('========================================\n\n');
