%% Visualize Base Station Placement for Urban Scenario
% =====================================================
% 
% This script generates a visualization of the BS placement
% for the 300m × 300m urban scenario

clear; close all; clc;

%% Load configuration
run('config_urban_dataset.m');

%% Create figure
fig = figure('Position', [100, 100, 1400, 1000]);

%% Plot area
hold on; grid on; axis equal;

% Draw scenario bounds
rectangle('Position', [config.scenario.bounds.x_min, config.scenario.bounds.y_min, ...
    config.scenario.bounds.x_max - config.scenario.bounds.x_min, ...
    config.scenario.bounds.y_max - config.scenario.bounds.y_min], ...
    'EdgeColor', 'k', 'LineWidth', 2);

% Define zone colors (for illustration - actual zones assigned randomly)
zone_colors = struct(...
    'outdoor_open', [0.8 0.95 0.8], ...      % Light green
    'outdoor_obstructed', [0.95 0.9 0.7], ...% Light yellow
    'indoor_light', [0.85 0.9 0.95], ...     % Light blue
    'indoor_heavy', [0.75 0.75 0.8] ...      % Gray
);

% Draw illustrative zones (these are examples, actual assignment is random per sample)
% Outdoor open - streets/plazas
rectangle('Position', [0, 0, 300, 50], 'FaceColor', zone_colors.outdoor_open, 'EdgeColor', 'none');
rectangle('Position', [0, 250, 300, 50], 'FaceColor', zone_colors.outdoor_open, 'EdgeColor', 'none');
rectangle('Position', [130, 50, 40, 200], 'FaceColor', zone_colors.outdoor_open, 'EdgeColor', 'none');

% Outdoor obstructed
rectangle('Position', [0, 50, 60, 80], 'FaceColor', zone_colors.outdoor_obstructed, 'EdgeColor', 'none');
rectangle('Position', [240, 150, 60, 80], 'FaceColor', zone_colors.outdoor_obstructed, 'EdgeColor', 'none');

% Indoor light - glass buildings
rectangle('Position', [60, 50, 70, 80], 'FaceColor', zone_colors.indoor_light, 'EdgeColor', 'none');
rectangle('Position', [170, 170, 70, 80], 'FaceColor', zone_colors.indoor_light, 'EdgeColor', 'none');

% Indoor heavy - concrete buildings
rectangle('Position', [60, 170, 70, 80], 'FaceColor', zone_colors.indoor_heavy, 'EdgeColor', 'none');
rectangle('Position', [170, 50, 70, 80], 'FaceColor', zone_colors.indoor_heavy, 'EdgeColor', 'none');

%% Plot Base Stations
bs_colors = struct(...
    'macro', 'r', ...
    'outdoor_small', 'b', ...
    'indoor_small', 'g' ...
);

bs_markers = struct(...
    'macro', '^', ...
    'outdoor_small', 's', ...
    'indoor_small', 'o' ...
);

bs_sizes = struct(...
    'macro', 200, ...
    'outdoor_small', 120, ...
    'indoor_small', 100 ...
);

% Plot each BS
for i = 1:size(config.bs.positions, 1)
    bs_type = config.bs.types{i};
    x = config.bs.positions(i, 1);
    y = config.bs.positions(i, 2);
    z = config.bs.positions(i, 3);
    
    % Plot BS position
    scatter(x, y, bs_sizes.(bs_type), bs_colors.(bs_type), ...
        bs_markers.(bs_type), 'filled', 'LineWidth', 1.5, ...
        'MarkerEdgeColor', 'k');
    
    % Add label
    text(x, y + 15, sprintf('BS%d\n%s\n%.0fm', i, strrep(bs_type, '_', ' '), z), ...
        'HorizontalAlignment', 'center', 'FontSize', 9, 'FontWeight', 'bold', ...
        'BackgroundColor', 'w', 'EdgeColor', 'k', 'Margin', 2);
    
    % Draw coverage circle (approximate)
    if strcmp(bs_type, 'macro')
        coverage_radius = 150;  % Macro BS coverage
    elseif strcmp(bs_type, 'outdoor_small')
        coverage_radius = 80;   % Outdoor small cell
    else
        coverage_radius = 50;   % Indoor small cell
    end
    
    theta = linspace(0, 2*pi, 100);
    cx = x + coverage_radius * cos(theta);
    cy = y + coverage_radius * sin(theta);
    plot(cx, cy, '--', 'Color', bs_colors.(bs_type), 'LineWidth', 1, 'HandleVisibility', 'off');
end

%% Add legend for zones
legend_entries = {};
legend_handles = [];

% Zone legend
for zone_name = {'outdoor_open', 'outdoor_obstructed', 'indoor_light', 'indoor_heavy'}
    zone = zone_name{1};
    h = patch([0 0], [0 0], zone_colors.(zone), 'EdgeColor', 'k');
    legend_handles(end+1) = h;
    legend_entries{end+1} = sprintf('%s (%.0f%%)', strrep(zone, '_', ' '), ...
        100 * config.zone_distribution.(zone));
end

% BS type legend
for bs_type_name = {'macro', 'outdoor_small', 'indoor_small'}
    bs_type = bs_type_name{1};
    h = scatter(NaN, NaN, bs_sizes.(bs_type), bs_colors.(bs_type), ...
        bs_markers.(bs_type), 'filled', 'LineWidth', 1.5, 'MarkerEdgeColor', 'k');
    legend_handles(end+1) = h;
    
    % Count BSs of this type
    count = sum(strcmp(config.bs.types, bs_type));
    legend_entries{end+1} = sprintf('%s BS (%d)', strrep(bs_type, '_', ' '), count);
end

legend(legend_handles, legend_entries, 'Location', 'eastoutside', 'FontSize', 10);

%% Formatting
xlabel('X Position (m)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('Y Position (m)', 'FontSize', 12, 'FontWeight', 'bold');
title({'Urban Scenario: Base Station Placement (300m × 300m)', ...
       sprintf('6 BSs: 2 Macro + 2 Outdoor Small + 2 Indoor Small | Frequency: %.1f GHz', ...
       config.scenario.frequency / 1e9)}, ...
    'FontSize', 14, 'FontWeight', 'bold');

xlim([config.scenario.bounds.x_min - 20, config.scenario.bounds.x_max + 20]);
ylim([config.scenario.bounds.y_min - 20, config.scenario.bounds.y_max + 20]);

set(gca, 'FontSize', 11);

%% Add text annotations
text(150, -35, 'Note: Zone colors are illustrative. Actual zone assignment is random per sample based on configured distribution.', ...
    'HorizontalAlignment', 'center', 'FontSize', 9, 'FontStyle', 'italic', 'Color', [0.3 0.3 0.3]);

%% Display BS details
fprintf('\n========================================\n');
fprintf('BASE STATION PLACEMENT VISUALIZATION\n');
fprintf('========================================\n\n');

fprintf('Scenario: %d × %d m² urban area\n', ...
    config.scenario.bounds.x_max - config.scenario.bounds.x_min, ...
    config.scenario.bounds.y_max - config.scenario.bounds.y_min);
fprintf('Frequency: %.1f GHz\n', config.scenario.frequency / 1e9);
fprintf('Total BSs: %d\n\n', size(config.bs.positions, 1));

fprintf('BS Details:\n');
fprintf('%-5s %-15s %-25s %-8s %-12s\n', 'ID', 'Type', 'Position (x,y,z)', 'Height', 'Power');
fprintf('%-5s %-15s %-25s %-8s %-12s\n', repmat('-', 1, 5), repmat('-', 1, 15), ...
    repmat('-', 1, 25), repmat('-', 1, 8), repmat('-', 1, 12));

for i = 1:size(config.bs.positions, 1)
    fprintf('BS%-3d %-15s (%-4.0f, %-4.0f, %-4.0f)m %-8.0fm %-12s\n', ...
        i, config.bs.types{i}, ...
        config.bs.positions(i, 1), config.bs.positions(i, 2), config.bs.positions(i, 3), ...
        config.bs.positions(i, 3), ...
        sprintf('%d dBm', config.bs.tx_power_dbm(i)));
end

fprintf('\n========================================\n\n');

%% Save figure
script_dir = fileparts(mfilename('fullpath'));
output_file = fullfile(script_dir, 'bs_placement_visualization.png');
saveas(fig, output_file);
fprintf('✓ Saved visualization: %s\n', output_file);

% Also save as fig for interactive viewing
savefig(fig, fullfile(script_dir, 'bs_placement_visualization.fig'));
fprintf('✓ Saved MATLAB figure: bs_placement_visualization.fig\n\n');
