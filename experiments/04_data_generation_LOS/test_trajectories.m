%% Test Script for Trajectory Generators
% Quick verification that all trajectory generation functions work
% Runtime: < 1 minute

clear; close all; clc;

fprintf('========================================\n');
fprintf('TESTING TRAJECTORY GENERATORS\n');
fprintf('========================================\n\n');

% Test configuration
n_samples = 80;
bounds = [10, 90, 10, 90];  % [xmin, xmax, ymin, ymax]

% Add utils to path (correct relative path from experiments/04_data_generation/)
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);

% Setup output directory using ExperimentUtils
results_dir = ExperimentUtils.createResultsDir('test_trajectories');

% Create figure for all trajectories
fig = figure('Name', 'Trajectory Generator Test', 'Position', [100, 100, 1200, 600]);

%% Test 1: Linear trajectory
fprintf('Testing linear trajectory... ');
subplot(2, 4, 1);
start_pos = [20, 20];
end_pos = [80, 70];
traj = generate_linear_trajectory(start_pos, end_pos, n_samples, 'randomize', false);
plot(traj(:,1), traj(:,2), 'b-', 'LineWidth', 2);
hold on;
plot(start_pos(1), start_pos(2), 'go', 'MarkerSize', 10, 'MarkerFaceColor', 'g');
plot(end_pos(1), end_pos(2), 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
xlabel('X (m)'); ylabel('Y (m)'); title('Linear'); grid on; axis equal;
xlim([0, 100]); ylim([0, 100]);
fprintf('✓\n');

%% Test 2: Circular trajectory
fprintf('Testing circular trajectory... ');
subplot(2, 4, 2);
center = [50, 50];
radius = 25;
traj = generate_circular_trajectory(center, radius, n_samples);
plot(traj(:,1), traj(:,2), 'b-', 'LineWidth', 2);
hold on;
plot(center(1), center(2), 'k+', 'MarkerSize', 15, 'LineWidth', 2);
xlabel('X (m)'); ylabel('Y (m)'); title('Circular'); grid on; axis equal;
xlim([0, 100]); ylim([0, 100]);
fprintf('✓\n');

%% Test 3: Zigzag trajectory
fprintf('Testing zigzag trajectory... ');
subplot(2, 4, 3);
start_pos = [15, 30];
end_pos = [85, 70];
traj = generate_zigzag_trajectory(start_pos, end_pos, n_samples, 'amplitude', 8, 'frequency', 4);
plot(traj(:,1), traj(:,2), 'b-', 'LineWidth', 2);
hold on;
plot(start_pos(1), start_pos(2), 'go', 'MarkerSize', 10, 'MarkerFaceColor', 'g');
plot(end_pos(1), end_pos(2), 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
xlabel('X (m)'); ylabel('Y (m)'); title('Zigzag'); grid on; axis equal;
xlim([0, 100]); ylim([0, 100]);
fprintf('✓\n');

%% Test 4: Random walk
fprintf('Testing random walk trajectory... ');
subplot(2, 4, 4);
start_pos = [50, 50];
traj = generate_random_walk(start_pos, n_samples, 'step_size', 2.5, 'bounds', bounds);
plot(traj(:,1), traj(:,2), 'b-', 'LineWidth', 2);
hold on;
plot(start_pos(1), start_pos(2), 'go', 'MarkerSize', 10, 'MarkerFaceColor', 'g');
xlabel('X (m)'); ylabel('Y (m)'); title('Random Walk'); grid on; axis equal;
xlim([0, 100]); ylim([0, 100]);
fprintf('✓\n');

%% Test 5: Grid trajectory
fprintf('Testing grid trajectory... ');
subplot(2, 4, 5);
traj = generate_grid_trajectory(bounds, 10, n_samples);
plot(traj(:,1), traj(:,2), 'b-', 'LineWidth', 2);
hold on;
plot(traj(:,1), traj(:,2), 'b.', 'MarkerSize', 8);
xlabel('X (m)'); ylabel('Y (m)'); title('Grid Pattern'); grid on; axis equal;
xlim([0, 100]); ylim([0, 100]);
fprintf('✓\n');

%% Test 6: Spiral trajectory (outward)
fprintf('Testing spiral trajectory (outward)... ');
subplot(2, 4, 6);
center = [50, 50];
traj = generate_spiral_trajectory(center, n_samples, 'radius_start', 5, ...
                                  'radius_end', 30, 'revolutions', 3, 'direction', 'out');
plot(traj(:,1), traj(:,2), 'b-', 'LineWidth', 2);
hold on;
plot(center(1), center(2), 'k+', 'MarkerSize', 15, 'LineWidth', 2);
xlabel('X (m)'); ylabel('Y (m)'); title('Spiral (Outward)'); grid on; axis equal;
xlim([0, 100]); ylim([0, 100]);
fprintf('✓\n');

%% Test 7: Spiral trajectory (inward)
fprintf('Testing spiral trajectory (inward)... ');
subplot(2, 4, 7);
center = [50, 50];
traj = generate_spiral_trajectory(center, n_samples, 'radius_start', 5, ...
                                  'radius_end', 30, 'revolutions', 3, 'direction', 'in');
plot(traj(:,1), traj(:,2), 'b-', 'LineWidth', 2);
hold on;
plot(center(1), center(2), 'k+', 'MarkerSize', 15, 'LineWidth', 2);
xlabel('X (m)'); ylabel('Y (m)'); title('Spiral (Inward)'); grid on; axis equal;
xlim([0, 100]); ylim([0, 100]);
fprintf('✓\n');

%% Test 8: Figure-8 trajectory
fprintf('Testing figure-8 trajectory... ');
subplot(2, 4, 8);
center = [50, 50];
traj = generate_figure8_trajectory(center, 20, n_samples);
plot(traj(:,1), traj(:,2), 'b-', 'LineWidth', 2);
hold on;
plot(center(1), center(2), 'k+', 'MarkerSize', 15, 'LineWidth', 2);
xlabel('X (m)'); ylabel('Y (m)'); title('Figure-8'); grid on; axis equal;
xlim([0, 100]); ylim([0, 100]);
fprintf('✓\n');

%% Overall title
sgtitle('Trajectory Generator Test - All Types', 'FontSize', 16, 'FontWeight', 'bold');

fprintf('\n========================================\n');
fprintf('ALL TESTS PASSED! ✓\n');
fprintf('========================================\n\n');
fprintf('Next step: Run exp10_large_dataset to generate full dataset\n');
fprintf('Command: exp10_large_dataset\n\n');

% Save figure using ExperimentUtils
ExperimentUtils.saveFigures(fig, 'trajectory_test', results_dir);

fprintf('✓ Test results saved to: %s\n', results_dir);
fprintf('   - trajectory_test.png\n');
fprintf('   - trajectory_test.fig\n\n');
