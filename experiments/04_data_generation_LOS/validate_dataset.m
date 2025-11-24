function validate_dataset(dataset_path)
% VALIDATE_DATASET Validate generated dataset quality
%
% Usage:
%   validate_dataset('../../results/exp10_2025-11-07_12-00-00/dataset')

    % Add utils to path
    addpath(fullfile(fileparts(mfilename('fullpath')), '..', '..', 'utils'));

    fprintf('========================================\n');
    fprintf('DATASET VALIDATION\n');
    fprintf('========================================\n\n');
    
    %% Load data
    fprintf('Loading dataset...\n');
    train_file = fullfile(dataset_path, 'train_data.mat');
    val_file = fullfile(dataset_path, 'val_data.mat');
    
    if ~exist(train_file, 'file') || ~exist(val_file, 'file')
        error('Dataset files not found in: %s', dataset_path);
    end
    
    train_data = load(train_file);
    val_data = load(val_file);
    
    n_train = length(train_data.positions_x);
    n_val = length(val_data.positions_x);
    
    fprintf('✓ Training samples: %d\n', n_train);
    fprintf('✓ Validation samples: %d\n', n_val);
    fprintf('✓ Total samples: %d\n\n', n_train + n_val);
    
    %% Check data integrity
    fprintf('Checking data integrity...\n');
    
    % Check for NaN/Inf
    train_has_nan = any(isnan(train_data.positions_x)) || any(isnan(train_data.positions_y));
    val_has_nan = any(isnan(val_data.positions_x)) || any(isnan(val_data.positions_y));
    
    if train_has_nan || val_has_nan
        warning('Found NaN values in positions!');
    else
        fprintf('✓ No NaN values\n');
    end
    
    % Check bounds
    x_min = 10; x_max = 90;
    y_min = 10; y_max = 90;
    
    train_in_bounds = all(train_data.positions_x >= x_min & train_data.positions_x <= x_max) && ...
                      all(train_data.positions_y >= y_min & train_data.positions_y <= y_max);
    val_in_bounds = all(val_data.positions_x >= x_min & val_data.positions_x <= x_max) && ...
                    all(val_data.positions_y >= y_min & val_data.positions_y <= y_max);
    
    if train_in_bounds && val_in_bounds
        fprintf('✓ All positions within bounds [%d,%d] × [%d,%d]\n', x_min, x_max, y_min, y_max);
    else
        warning('Some positions outside bounds!');
    end
    
    fprintf('\n');
    
    %% Spatial coverage analysis
    fprintf('Analyzing spatial coverage...\n');
    
    % Create grid
    grid_size = 10;  % 10x10 meter regions
    x_edges = x_min:grid_size:x_max;
    y_edges = y_min:grid_size:y_max;
    
    % Count samples per region
    [train_counts, ~, ~] = histcounts2(train_data.positions_x, train_data.positions_y, ...
                                       x_edges, y_edges);
    [val_counts, ~, ~] = histcounts2(val_data.positions_x, val_data.positions_y, ...
                                     x_edges, y_edges);
    
    total_counts = train_counts + val_counts;
    
    % Statistics
    n_regions = numel(total_counts);
    empty_regions = sum(total_counts(:) == 0);
    coverage = 100 * (1 - empty_regions / n_regions);
    
    fprintf('  Grid size: %d × %d regions (%dm spacing)\n', ...
            length(x_edges)-1, length(y_edges)-1, grid_size);
    fprintf('  Covered regions: %d / %d (%.1f%%)\n', ...
            n_regions - empty_regions, n_regions, coverage);
    fprintf('  Samples per region:\n');
    fprintf('    Min: %d\n', min(total_counts(total_counts > 0)));
    fprintf('    Max: %d\n', max(total_counts(:)));
    fprintf('    Mean: %.1f\n', mean(total_counts(total_counts > 0)));
    fprintf('    Median: %.1f\n\n', median(total_counts(total_counts > 0)));
    
    %% Diversity analysis
    fprintf('Analyzing dataset diversity...\n');
    
    % Distance distribution
    all_x = [train_data.positions_x, val_data.positions_x];
    all_y = [train_data.positions_y, val_data.positions_y];
    
    % Sample 1000 random pairs for distance calculation
    n_samples = min(1000, length(all_x));
    idx = randperm(length(all_x), n_samples);
    
    distances = [];
    for i = 1:length(idx)-1
        dist = sqrt((all_x(idx(i)) - all_x(idx(i+1)))^2 + ...
                   (all_y(idx(i)) - all_y(idx(i+1)))^2);
        distances = [distances, dist];
    end
    
    fprintf('  Inter-sample distances (random pairs):\n');
    fprintf('    Mean: %.2f m\n', mean(distances));
    fprintf('    Std: %.2f m\n', std(distances));
    fprintf('    Median: %.2f m\n\n', median(distances));
    
    %% Feature statistics
    fprintf('Feature statistics...\n');
    
    fprintf('  Training set:\n');
    fprintf('    CQI wideband: %.2f ± %.2f dB\n', ...
            mean(train_data.CQI_wb), std(train_data.CQI_wb));
    fprintf('    RSRP: %.2f ± %.2f dBm\n', ...
            mean(train_data.RSRP), std(train_data.RSRP));
    fprintf('    SINR wideband: %.2f ± %.2f dB\n', ...
            mean(train_data.SINR_wb), std(train_data.SINR_wb));
    
    fprintf('\n  Validation set:\n');
    fprintf('    CQI wideband: %.2f ± %.2f dB\n', ...
            mean(val_data.CQI_wb), std(val_data.CQI_wb));
    fprintf('    RSRP: %.2f ± %.2f dBm\n', ...
            mean(val_data.RSRP), std(val_data.RSRP));
    fprintf('    SINR wideband: %.2f ± %.2f dB\n\n', ...
            mean(val_data.SINR_wb), std(val_data.SINR_wb));
    
    %% Generate validation plots
    fprintf('Generating validation plots...\n');
    
    output_dir = fileparts(dataset_path);
    
    % 1. Spatial coverage heatmap
    fig1 = figure('Name', 'Spatial Coverage Heatmap', 'Position', [100, 100, 1000, 400]);
    
    subplot(1, 2, 1);
    imagesc(x_edges(1:end-1), y_edges(1:end-1), train_counts');
    axis xy; colorbar;
    xlabel('X Position (m)'); ylabel('Y Position (m)');
    title('Training Set Coverage (samples per region)');
    set(gca, 'FontSize', 11);
    
    subplot(1, 2, 2);
    imagesc(x_edges(1:end-1), y_edges(1:end-1), val_counts');
    axis xy; colorbar;
    xlabel('X Position (m)'); ylabel('Y Position (m)');
    title('Validation Set Coverage (samples per region)');
    set(gca, 'FontSize', 11);
    
    % 2. Position distributions
    fig2 = figure('Name', 'Position Distributions', 'Position', [100, 100, 1000, 400]);
    
    subplot(2, 2, 1);
    histogram(train_data.positions_x, 30, 'FaceColor', 'b', 'EdgeColor', 'k');
    xlabel('X Position (m)'); ylabel('Frequency');
    title('Training X Distribution');
    grid on;
    
    subplot(2, 2, 2);
    histogram(train_data.positions_y, 30, 'FaceColor', 'b', 'EdgeColor', 'k');
    xlabel('Y Position (m)'); ylabel('Frequency');
    title('Training Y Distribution');
    grid on;
    
    subplot(2, 2, 3);
    histogram(val_data.positions_x, 30, 'FaceColor', 'r', 'EdgeColor', 'k');
    xlabel('X Position (m)'); ylabel('Frequency');
    title('Validation X Distribution');
    grid on;
    
    subplot(2, 2, 4);
    histogram(val_data.positions_y, 30, 'FaceColor', 'r', 'EdgeColor', 'k');
    xlabel('Y Position (m)'); ylabel('Frequency');
    title('Validation Y Distribution');
    grid on;
    
    % 3. 2D scatter plot
    fig3 = figure('Name', 'Position Scatter Plots', 'Position', [100, 100, 1000, 400]);
    
    subplot(1, 2, 1);
    scatter(train_data.positions_x, train_data.positions_y, 10, 'b', 'filled', 'MarkerFaceAlpha', 0.3);
    xlabel('X Position (m)'); ylabel('Y Position (m)');
    title(sprintf('Training Set Positions (n=%d)', n_train));
    grid on; axis equal;
    xlim([x_min, x_max]); ylim([y_min, y_max]);
    
    subplot(1, 2, 2);
    scatter(val_data.positions_x, val_data.positions_y, 10, 'r', 'filled', 'MarkerFaceAlpha', 0.3);
    xlabel('X Position (m)'); ylabel('Y Position (m)');
    title(sprintf('Validation Set Positions (n=%d)', n_val));
    grid on; axis equal;
    xlim([x_min, x_max]); ylim([y_min, y_max]);
    
    % Save all figures using ExperimentUtils
    ExperimentUtils.saveFigures({fig1, fig2, fig3}, ...
                                {'validation_coverage', 'validation_distributions', 'validation_scatter'}, ...
                                output_dir);
    fprintf('✓ Saved: validation_coverage.png/.fig\n');
    fprintf('✓ Saved: validation_distributions.png/.fig\n');
    fprintf('✓ Saved: validation_scatter.png/.fig\n');
    
    close(fig1); close(fig2); close(fig3);
    
    %% Final summary
    fprintf('\n========================================\n');
    fprintf('VALIDATION COMPLETE\n');
    fprintf('========================================\n\n');
    
    fprintf('✅ Dataset Quality: ');
    if coverage > 90 && ~train_has_nan && ~val_has_nan
        fprintf('EXCELLENT\n');
    elseif coverage > 70
        fprintf('GOOD\n');
    else
        fprintf('NEEDS IMPROVEMENT\n');
    end
    
    fprintf('✅ Spatial Coverage: %.1f%%\n', coverage);
    fprintf('✅ Data Integrity: %s\n\n', ...
            iif(train_has_nan || val_has_nan, 'Issues found', 'OK'));
    
    fprintf('📊 Ready for ML training!\n');
    fprintf('   Update ml_training/config.py:\n');
    fprintf('   DEFAULT_DATASET_PATH = "%s"\n\n', dataset_path);
end

function result = iif(condition, true_val, false_val)
    if condition
        result = true_val;
    else
        result = false_val;
    end
end
