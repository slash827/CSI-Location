%% Extract Base Station Parameters from exp11 Results
% This script extracts all BS configuration and run details from:
% results/exp11_2025-11-15_14-07-52
%
% Generated: November 27, 2025

%% 1. Define paths
results_dir = 'd:\gilad\projects\Academy\CSI-Location\results\exp11_2025-11-15_14-07-52';
dataset_dir = fullfile(results_dir, 'dataset');

% Load metadata
metadata_file = fullfile(dataset_dir, 'nlos_metadata.mat');
train_file = fullfile(dataset_dir, 'train_data.mat');
val_file = fullfile(dataset_dir, 'val_data.mat');

fprintf('Loading experiment data from: %s\n\n', results_dir);

% Load the metadata
load(metadata_file);

% The metadata should contain simulation parameters and BS configuration
% Check available variables
fprintf('=== LOADED METADATA VARIABLES ===\n');
whos
fprintf('\n');


%% 2. Extract Base Station Configuration

fprintf('=== BASE STATION CONFIGURATION ===\n\n');

% From the metadata, extract BS information
if exist('s', 'var')  % simulation_parameters
    fprintf('Carrier Frequency: %.2f GHz\n', s.center_frequency/1e9);
    lambda = physconst('LightSpeed') / s.center_frequency;
    fprintf('Wavelength: %.4f m\n', lambda);
    fprintf('Samples per half wavelength: %d\n\n', s.samples_per_meter * lambda/2);
end

if exist('l', 'var')  % layout
    num_bs = l.no_tx;
    fprintf('Number of Base Stations: %d\n\n', num_bs);
    
    for i_bs = 1:num_bs
        fprintf('--- Base Station %d ---\n', i_bs);
        
        % Position
        pos = l.tx_position(:, i_bs);
        fprintf('Position: [x=%.2fm, y=%.2fm, z=%.2fm]\n', pos(1), pos(2), pos(3));
        
        % Antenna array
        antenna = l.tx_array(i_bs);
        fprintf('Antenna Type: %s\n', class(antenna));
        fprintf('Number of Elements: %d\n', antenna.no_elements);
        
        % Array configuration
        if isprop(antenna, 'element_position')
            elem_pos = antenna.element_position;
            fprintf('Array Size: %d x %d x %d\n', ...
                length(unique(elem_pos(1,:))), ...
                length(unique(elem_pos(2,:))), ...
                length(unique(elem_pos(3,:))));
        end
        
        % Element spacing
        if antenna.no_elements > 1
            elem_pos = antenna.element_position;
            dx = diff(unique(elem_pos(1,:)));
            dy = diff(unique(elem_pos(2,:)));
            if ~isempty(dx)
                fprintf('Element Spacing (X): %.4f wavelengths\n', dx(1));
            end
            if ~isempty(dy)
                fprintf('Element Spacing (Y): %.4f wavelengths\n', dy(1));
            end
        end
        
        fprintf('\n');
    end
    
    % BS Geometry Analysis
    fprintf('=== BASE STATION GEOMETRY ===\n\n');
    positions = l.tx_position(1:2, :)';  % Get x,y coordinates
    
    % Calculate inter-BS distances
    fprintf('Inter-BS Distances:\n');
    for i = 1:num_bs
        for j = i+1:num_bs
            dist = norm(positions(i,:) - positions(j,:));
            fprintf('  BS%d ↔ BS%d: %.2f m\n', i, j, dist);
        end
    end
    
    % Calculate coverage area
    min_x = min(positions(:,1));
    max_x = max(positions(:,1));
    min_y = min(positions(:,2));
    max_y = max(positions(:,2));
    
    fprintf('\nBS Coverage Area:\n');
    fprintf('  X: %.2f to %.2f m (span: %.2f m)\n', min_x, max_x, max_x-min_x);
    fprintf('  Y: %.2f to %.2f m (span: %.2f m)\n', min_y, max_y, max_y-min_y);
    fprintf('\n');
end


%% 3. Experiment Overview

fprintf('=== EXPERIMENT 11 OVERVIEW ===\n\n');
fprintf('Experiment: NLOS-Enhanced Large-Scale Data Generation\n');
fprintf('Execution Date: 2025-11-15_14-07-52\n\n');

% Extract experiment details from metadata
if exist('config', 'var')
    fprintf('--- Configuration ---\n');
    disp(config);
elseif exist('nlos_distribution', 'var')
    fprintf('--- NLOS Distribution ---\n');
    disp(nlos_distribution);
end

% Load training data to inspect structure
fprintf('\n=== DATASET STRUCTURE ===\n\n');
train_data = load(train_file);
fprintf('Training data variables:\n');
train_fields = fieldnames(train_data);
disp(train_fields);

% Display sample counts - find the data fields dynamically
X_field = '';
Y_field = '';
nlos_field = '';

for i = 1:length(train_fields)
    fname = train_fields{i};
    if contains(lower(fname), 'feature') || strcmp(fname, 'X') || contains(fname, 'csi')
        X_field = fname;
    elseif contains(lower(fname), 'position') || strcmp(fname, 'Y') || contains(lower(fname), 'label') && ~contains(lower(fname), 'nlos')
        Y_field = fname;
    elseif contains(lower(fname), 'nlos')
        nlos_field = fname;
    end
end

if ~isempty(X_field)
    fprintf('\nTraining samples: %d\n', size(train_data.(X_field), 1));
    fprintf('Features per sample: %d\n', size(train_data.(X_field), 2));
end

if ~isempty(Y_field)
    fprintf('Output dimensions: %d\n', size(train_data.(Y_field), 2));
end

if ~isempty(nlos_field)
    fprintf('\nNLOS Distribution in Training Set:\n');
    unique_labels = unique(train_data.(nlos_field));
    for i = 1:length(unique_labels)
        count = sum(train_data.(nlos_field) == unique_labels(i));
        pct = 100 * count / length(train_data.(nlos_field));
        fprintf('  Type %d: %d samples (%.1f%%)\n', unique_labels(i), count, pct);
    end
end

% Load validation data
val_data = load(val_file);
fprintf('\nValidation data variables:\n');
val_fields = fieldnames(val_data);
disp(val_fields);

% Find validation data field
X_val_field = '';
for i = 1:length(val_fields)
    fname = val_fields{i};
    if contains(lower(fname), 'feature') || strcmp(fname, 'X') || contains(fname, 'csi')
        X_val_field = fname;
        break;
    end
end

if ~isempty(X_val_field)
    fprintf('\nValidation samples: %d\n', size(val_data.(X_val_field), 1));
end

fprintf('\n');


%% 4. Feature Analysis

fprintf('=== FEATURE BREAKDOWN ===\n\n');

if ~isempty(X_field)
    total_features = size(train_data.(X_field), 2);
    
    % Based on experiment report: 12291 features total
    % Wideband: 3 (CQI, RSRP, SINR)
    % Per-subcarrier: 4096 × 3 types = 12288
    
    wideband_features = 3;
    subcarrier_features = total_features - wideband_features;
    num_subcarriers = subcarrier_features / 3;
    
    fprintf('Total Features: %d\n', total_features);
    fprintf('  - Wideband metrics: %d (CQI, RSRP, SINR)\n', wideband_features);
    fprintf('  - Subcarrier features: %d\n', subcarrier_features);
    fprintf('  - Number of subcarriers: %d\n', num_subcarriers);
    fprintf('  - Types per subcarrier: 3 (amplitude, phase, real/imag)\n\n');
    
    % Analyze feature statistics
    fprintf('Feature Statistics (Training Set):\n');
    fprintf('  Mean: %.4f\n', mean(train_data.(X_field)(:)));
    fprintf('  Std: %.4f\n', std(train_data.(X_field)(:)));
    fprintf('  Min: %.4f\n', min(train_data.(X_field)(:)));
    fprintf('  Max: %.4f\n', max(train_data.(X_field)(:)));
end

fprintf('\n');

%% 5. Export Summary to File

output_file = fullfile(results_dir, 'bs_parameters_extracted.txt');
fid = fopen(output_file, 'w');

fprintf(fid, '========================================\n');
fprintf(fid, 'EXP11 BASE STATION PARAMETERS\n');
fprintf(fid, '========================================\n\n');
fprintf(fid, 'Extracted: %s\n\n', datestr(now));

if exist('s', 'var')
    fprintf(fid, '--- Network Configuration ---\n');
    fprintf(fid, 'Carrier Frequency: %.2f GHz\n', s.center_frequency/1e9);
    lambda = physconst('LightSpeed') / s.center_frequency;
    fprintf(fid, 'Wavelength: %.4f m\n\n', lambda);
end

if exist('l', 'var')
    fprintf(fid, '--- Base Station Configuration ---\n');
    fprintf(fid, 'Number of Base Stations: %d\n\n', l.no_tx);
    
    for i_bs = 1:l.no_tx
        fprintf(fid, 'Base Station %d:\n', i_bs);
        pos = l.tx_position(:, i_bs);
        fprintf(fid, '  Position: [%.2f, %.2f, %.2f] m\n', pos(1), pos(2), pos(3));
        fprintf(fid, '  Antennas: %d\n', l.tx_array(i_bs).no_elements);
        fprintf(fid, '\n');
    end
    
    positions = l.tx_position(1:2, :)';
    fprintf(fid, '--- Inter-BS Distances ---\n');
    for i = 1:l.no_tx
        for j = i+1:l.no_tx
            dist = norm(positions(i,:) - positions(j,:));
            fprintf(fid, 'BS%d ↔ BS%d: %.2f m\n', i, j, dist);
        end
    end
    fprintf(fid, '\n');
end

fprintf(fid, '--- Dataset Statistics ---\n');
if ~isempty(X_field)
    fprintf(fid, 'Training samples: %d\n', size(train_data.(X_field), 1));
end
if ~isempty(X_val_field)
    fprintf(fid, 'Validation samples: %d\n', size(val_data.(X_val_field), 1));
end
if ~isempty(X_field) && ~isempty(X_val_field)
    fprintf(fid, 'Total samples: %d\n', size(train_data.(X_field), 1) + size(val_data.(X_val_field), 1));
end
if ~isempty(X_field)
    fprintf(fid, 'Features per sample: %d\n', size(train_data.(X_field), 2));
end

fclose(fid);
fprintf('✓ Parameters saved to: %s\n\n', output_file);

%% 6. Visualization

if exist('l', 'var')
    figure('Name', 'EXP11 - Base Station Layout');
    hold on; grid on; axis equal;
    
    % Plot BS positions
    for i_bs = 1:l.no_tx
        pos = l.tx_position(:, i_bs);
        plot(pos(1), pos(2), 'r^', 'MarkerSize', 15, 'LineWidth', 2, ...
             'MarkerFaceColor', 'r');
        text(pos(1)+5, pos(2)+5, sprintf('BS%d', i_bs), ...
             'FontSize', 12, 'FontWeight', 'bold');
    end
    
    % Plot coverage area
    positions = l.tx_position(1:2, :)';
    min_x = min(positions(:,1));
    max_x = max(positions(:,1));
    min_y = min(positions(:,2));
    max_y = max(positions(:,2));
    
    rectangle('Position', [min_x-10, min_y-10, max_x-min_x+20, max_y-min_y+20], ...
        'EdgeColor', 'b', 'LineStyle', '--', 'LineWidth', 1.5);
    
    xlabel('X Position (m)', 'FontSize', 12);
    ylabel('Y Position (m)', 'FontSize', 12);
    title('EXP11 - Base Station Layout', 'FontSize', 14, 'FontWeight', 'bold');
    legend('Base Stations', 'Coverage Area', 'Location', 'best');
    hold off;
    
    plot_file = fullfile(results_dir, 'bs_layout_exp11.png');
    saveas(gcf, plot_file);
    fprintf('✓ BS layout saved to: %s\n', plot_file);
end

%% 7. Quick Reference Summary

fprintf('\n╔════════════════════════════════════════╗\n');
fprintf('║   EXP11 QUICK REFERENCE SUMMARY        ║\n');
fprintf('╠════════════════════════════════════════╣\n');
if exist('s', 'var')
    fprintf('║ Carrier Frequency: %.2f GHz           ║\n', s.center_frequency/1e9);
end
if exist('l', 'var')
    fprintf('║ Number of BS: %d                       ║\n', l.no_tx);
    fprintf('║ Antennas per BS: %d                    ║\n', l.tx_array(1).no_elements);
end
if ~isempty(X_field) && ~isempty(X_val_field)
    fprintf('║ Total Samples: %d                     ║\n', size(train_data.(X_field), 1) + size(val_data.(X_val_field), 1));
    fprintf('║ Training: %d | Validation: %d        ║\n', size(train_data.(X_field), 1), size(val_data.(X_val_field), 1));
end
fprintf('╚════════════════════════════════════════╝\n\n');

fprintf('✓ Script completed successfully!\n');
