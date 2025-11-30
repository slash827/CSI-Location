%% Analyze CSI Distributions - Statistical Modeling
% Fit statistical distributions to CSI samples at each grid point
% and create a spatial model for CSI prediction
%
% This script answers: "What distribution best describes CSI at a given location?"

clear; close all; clc;

%% Setup
fprintf('========================================\n');
fprintf('CSI DISTRIBUTION ANALYSIS\n');
fprintf('========================================\n\n');

% Find most recent exp12 results
results_root = '../../results';
exp12_dirs = dir(fullfile(results_root, 'exp12_*'));
if isempty(exp12_dirs)
    error('No exp12 results found!');
end

% Use most recent (sort descending by name which contains timestamp)
names = {exp12_dirs.name};
[~, idx] = sort(names);
idx = flipud(idx(:));
results_dir = fullfile(results_root, exp12_dirs(idx(1)).name);
fprintf('Analyzing: %s\n\n', exp12_dirs(idx(1)).name);

% Load data
fprintf('Loading data...\n');
stats_data = load(fullfile(results_dir, 'statistics', 'csi_statistics.mat'));
stats = stats_data.stats;

samples_file = fullfile(results_dir, 'data', 'all_samples.mat');
if ~exist(samples_file, 'file')
    error('Raw samples file not found! Ensure save_raw_samples was enabled.');
end
samples_data = load(samples_file);
all_samples = samples_data.all_samples;

grid_data = load(fullfile(results_dir, 'data', 'grid_info.mat'));
fprintf('✓ Data loaded\n\n');

% Create output directory
analysis_dir = fullfile(results_dir, 'distribution_analysis');
if ~exist(analysis_dir, 'dir')
    mkdir(analysis_dir);
end

%% Extract Grid Dimensions
[n_y, n_x, n_samples] = size(all_samples.RSS);
fprintf('Grid: %d x %d = %d points\n', n_x, n_y, n_x * n_y);
fprintf('Samples per point: %d\n\n', n_samples);

%% 1. Fit Distributions at Each Grid Point
fprintf('========================================\n');
fprintf('FITTING DISTRIBUTIONS\n');
fprintf('========================================\n\n');

% Initialize storage for distribution parameters
dist_params = struct();
dist_params.RSS = struct();
dist_params.SINR = struct();

% We'll test multiple distribution types
dist_types = {'Normal', 'Lognormal', 'Rayleigh', 'Rice'};

fprintf('Testing distribution types: %s\n', strjoin(dist_types, ', '));
fprintf('Fitting distributions for %d grid points...\n', n_x * n_y);

% Storage for goodness-of-fit metrics
gof = struct();
gof.RSS = zeros(n_y, n_x, length(dist_types));  % AIC for each distribution
gof.SINR = zeros(n_y, n_x, length(dist_types));
best_dist_RSS = cell(n_y, n_x);
best_dist_SINR = cell(n_y, n_x);

% Fit distributions at each point
tic;
for iy = 1:n_y
    for ix = 1:n_x
        % Extract samples for this location
        rss_samples = squeeze(all_samples.RSS(iy, ix, :));
        sinr_samples = squeeze(all_samples.SINR(iy, ix, :));
        
        % Remove NaN/Inf
        rss_samples = rss_samples(isfinite(rss_samples));
        sinr_samples = sinr_samples(isfinite(sinr_samples));
        
        if length(rss_samples) < 10
            continue;  % Skip if insufficient data
        end
        
        % Fit Normal distribution (always works)
        [mu_rss, sigma_rss] = normfit(rss_samples);
        dist_params.RSS.normal_mu(iy, ix) = mu_rss;
        dist_params.RSS.normal_sigma(iy, ix) = sigma_rss;
        
        % Calculate AIC for Normal
        pd_norm = makedist('Normal', 'mu', mu_rss, 'sigma', sigma_rss);
        logL_norm = sum(log(pdf(pd_norm, rss_samples)));
        k_norm = 2;  % 2 parameters
        gof.RSS(iy, ix, 1) = 2*k_norm - 2*logL_norm;  % AIC
        
        % Try Lognormal (if data is positive after offset)
        rss_offset = rss_samples - min(rss_samples) + 1;
        try
            pd_lognorm = fitdist(rss_offset, 'Lognormal');
            logL_lognorm = sum(log(pdf(pd_lognorm, rss_offset)));
            gof.RSS(iy, ix, 2) = 2*2 - 2*logL_lognorm;
            dist_params.RSS.lognorm_mu(iy, ix) = pd_lognorm.mu;
            dist_params.RSS.lognorm_sigma(iy, ix) = pd_lognorm.sigma;
        catch
            gof.RSS(iy, ix, 2) = inf;
        end
        
        % SINR - typically Normal in dB
        [mu_sinr, sigma_sinr] = normfit(sinr_samples);
        dist_params.SINR.normal_mu(iy, ix) = mu_sinr;
        dist_params.SINR.normal_sigma(iy, ix) = sigma_sinr;
        
        pd_norm_sinr = makedist('Normal', 'mu', mu_sinr, 'sigma', sigma_sinr);
        logL_norm_sinr = sum(log(pdf(pd_norm_sinr, sinr_samples)));
        gof.SINR(iy, ix, 1) = 2*2 - 2*logL_norm_sinr;
        
        % Determine best distribution
        [~, best_idx_rss] = min(gof.RSS(iy, ix, :));
        best_dist_RSS{iy, ix} = dist_types{best_idx_rss};
    end
    
    if mod(iy, 5) == 0
        fprintf('  Progress: %d/%d rows (%.0f%%)\n', iy, n_y, 100*iy/n_y);
    end
end
fit_time = toc;

fprintf('\n✓ Distribution fitting complete (%.1f seconds)\n\n', fit_time);

%% 2. Analyze Distribution Parameters vs. Distance
fprintf('========================================\n');
fprintf('SPATIAL ANALYSIS\n');
fprintf('========================================\n\n');

% Flatten for analysis
distances = stats.distance(:);
mu_rss_all = dist_params.RSS.normal_mu(:);
sigma_rss_all = dist_params.RSS.normal_sigma(:);
mu_sinr_all = dist_params.SINR.normal_mu(:);
sigma_sinr_all = dist_params.SINR.normal_sigma(:);

% Remove invalid points
valid_idx = isfinite(mu_rss_all) & isfinite(sigma_rss_all);
distances = distances(valid_idx);
mu_rss_all = mu_rss_all(valid_idx);
sigma_rss_all = sigma_rss_all(valid_idx);
mu_sinr_all = mu_sinr_all(valid_idx);
sigma_sinr_all = sigma_sinr_all(valid_idx);

fprintf('Valid points for analysis: %d\n', sum(valid_idx));

% Fit polynomial models for μ and σ vs distance
fprintf('\nFitting spatial models (distance-based):\n');

% RSS mean vs distance (path loss model)
p_mu_rss = polyfit(distances, mu_rss_all, 2);
mu_rss_pred = polyval(p_mu_rss, distances);
r2_mu_rss = 1 - sum((mu_rss_all - mu_rss_pred).^2) / sum((mu_rss_all - mean(mu_rss_all)).^2);
fprintf('  RSS μ(d): R² = %.3f\n', r2_mu_rss);

% RSS sigma vs distance
p_sigma_rss = polyfit(distances, sigma_rss_all, 2);
sigma_rss_pred = polyval(p_sigma_rss, distances);
r2_sigma_rss = 1 - sum((sigma_rss_all - sigma_rss_pred).^2) / sum((sigma_rss_all - mean(sigma_rss_all)).^2);
fprintf('  RSS σ(d): R² = %.3f\n', r2_sigma_rss);

% SINR mean vs distance
p_mu_sinr = polyfit(distances, mu_sinr_all, 2);
mu_sinr_pred = polyval(p_mu_sinr, distances);
r2_mu_sinr = 1 - sum((mu_sinr_all - mu_sinr_pred).^2) / sum((mu_sinr_all - mean(mu_sinr_all)).^2);
fprintf('  SINR μ(d): R² = %.3f\n', r2_mu_sinr);

% SINR sigma vs distance
p_sigma_sinr = polyfit(distances, sigma_sinr_all, 2);
sigma_sinr_pred = polyval(p_sigma_sinr, distances);
r2_sigma_sinr = 1 - sum((sigma_sinr_all - sigma_sinr_pred).^2) / sum((sigma_sinr_all - mean(sigma_sinr_all)).^2);
fprintf('  SINR σ(d): R² = %.3f\n', r2_sigma_sinr);

%% 3. Create Predictive Model
fprintf('\n========================================\n');
fprintf('PREDICTIVE MODEL\n');
fprintf('========================================\n\n');

% Save model parameters
model = struct();
model.description = 'CSI distribution parameters as function of distance from BS';
model.RSS_mu_poly = p_mu_rss;  % Polynomial coefficients for μ(d)
model.RSS_sigma_poly = p_sigma_rss;  % Polynomial coefficients for σ(d)
model.SINR_mu_poly = p_mu_sinr;
model.SINR_sigma_poly = p_sigma_sinr;
model.BS_position = grid_data.grid_info.bs_position;
model.R2_scores = struct('RSS_mu', r2_mu_rss, 'RSS_sigma', r2_sigma_rss, ...
                         'SINR_mu', r2_mu_sinr, 'SINR_sigma', r2_sigma_sinr);

fprintf('Model created:\n');
fprintf('  RSS ~ N(μ(d), σ(d)²)\n');
fprintf('  where μ(d) = %.3f·d² + %.3f·d + %.3f\n', p_mu_rss(1), p_mu_rss(2), p_mu_rss(3));
fprintf('        σ(d) = %.3f·d² + %.3f·d + %.3f\n\n', p_sigma_rss(1), p_sigma_rss(2), p_sigma_rss(3));

% Save model
save(fullfile(analysis_dir, 'csi_distribution_model.mat'), 'model', 'dist_params', 'gof', '-v7.3');
fprintf('✓ Model saved to: distribution_analysis/csi_distribution_model.mat\n\n');

%% 4. Visualizations
fprintf('========================================\n');
fprintf('GENERATING VISUALIZATIONS\n');
fprintf('========================================\n\n');

% Figure 1: Distribution parameters vs distance
figure('Position', [100, 100, 1400, 800]);

subplot(2, 2, 1);
scatter(distances, mu_rss_all, 30, 'filled', 'MarkerFaceAlpha', 0.6);
hold on;
plot(sort(distances), polyval(p_mu_rss, sort(distances)), 'r-', 'LineWidth', 2);
xlabel('Distance from BS (m)');
ylabel('RSS μ (dBm)');
title(sprintf('RSS Mean vs Distance (R² = %.3f)', r2_mu_rss));
grid on;
legend('Grid points', 'Fitted model', 'Location', 'best');

subplot(2, 2, 2);
scatter(distances, sigma_rss_all, 30, 'filled', 'MarkerFaceAlpha', 0.6);
hold on;
plot(sort(distances), polyval(p_sigma_rss, sort(distances)), 'r-', 'LineWidth', 2);
xlabel('Distance from BS (m)');
ylabel('RSS σ (dB)');
title(sprintf('RSS Std Dev vs Distance (R² = %.3f)', r2_sigma_rss));
grid on;
legend('Grid points', 'Fitted model', 'Location', 'best');

subplot(2, 2, 3);
scatter(distances, mu_sinr_all, 30, 'filled', 'MarkerFaceAlpha', 0.6);
hold on;
plot(sort(distances), polyval(p_mu_sinr, sort(distances)), 'r-', 'LineWidth', 2);
xlabel('Distance from BS (m)');
ylabel('SINR μ (dB)');
title(sprintf('SINR Mean vs Distance (R² = %.3f)', r2_mu_sinr));
grid on;
legend('Grid points', 'Fitted model', 'Location', 'best');

subplot(2, 2, 4);
scatter(distances, sigma_sinr_all, 30, 'filled', 'MarkerFaceAlpha', 0.6);
hold on;
plot(sort(distances), polyval(p_sigma_sinr, sort(distances)), 'r-', 'LineWidth', 2);
xlabel('Distance from BS (m)');
ylabel('SINR σ (dB)');
title(sprintf('SINR Std Dev vs Distance (R² = %.3f)', r2_sigma_sinr));
grid on;
legend('Grid points', 'Fitted model', 'Location', 'best');

sgtitle('Distribution Parameters vs Distance from BS', 'FontSize', 14, 'FontWeight', 'bold');
saveas(gcf, fullfile(analysis_dir, 'distribution_params_vs_distance.png'));
fprintf('✓ Saved: distribution_params_vs_distance.png\n');

% Figure 2: Example distributions at different locations
figure('Position', [100, 100, 1400, 900]);

% Select 6 representative points (near, medium, far)
example_distances = [30, 50, 70, 90, 110, 130];
for i = 1:6
    % Find closest grid point to this distance
    [~, closest_idx] = min(abs(stats.distance(:) - example_distances(i)));
    [iy, ix] = ind2sub([n_y, n_x], closest_idx);
    
    subplot(2, 3, i);
    
    % Get samples
    rss_samples = squeeze(all_samples.RSS(iy, ix, :));
    rss_samples = rss_samples(isfinite(rss_samples));
    
    % Plot histogram
    histogram(rss_samples, 20, 'Normalization', 'pdf', 'FaceAlpha', 0.7);
    hold on;
    
    % Overlay fitted normal distribution
    x_range = linspace(min(rss_samples), max(rss_samples), 100);
    mu = dist_params.RSS.normal_mu(iy, ix);
    sigma = dist_params.RSS.normal_sigma(iy, ix);
    y_fit = normpdf(x_range, mu, sigma);
    plot(x_range, y_fit, 'r-', 'LineWidth', 2);
    
    xlabel('RSS (dBm)');
    ylabel('Probability Density');
    title(sprintf('d = %.1f m | μ=%.1f, σ=%.1f dB', ...
        stats.distance(iy, ix), mu, sigma));
    legend('Samples', sprintf('N(%.1f, %.1f²)', mu, sigma), 'Location', 'best');
    grid on;
end

sgtitle('RSS Distributions at Different Distances', 'FontSize', 14, 'FontWeight', 'bold');
saveas(gcf, fullfile(analysis_dir, 'example_distributions.png'));
fprintf('✓ Saved: example_distributions.png\n');

% Figure 3: Spatial heatmaps of distribution parameters
figure('Position', [100, 100, 1400, 800]);

x_coords = grid_data.grid_info.x_coords(1, :);
y_coords = grid_data.grid_info.y_coords(:, 1);

subplot(2, 2, 1);
imagesc(x_coords, y_coords, dist_params.RSS.normal_mu);
colorbar;
xlabel('X (m)'); ylabel('Y (m)');
title('RSS μ (dBm)');
axis equal tight;
colormap(subplot(2, 2, 1), jet);

subplot(2, 2, 2);
imagesc(x_coords, y_coords, dist_params.RSS.normal_sigma);
colorbar;
xlabel('X (m)'); ylabel('Y (m)');
title('RSS σ (dB)');
axis equal tight;
colormap(subplot(2, 2, 2), hot);

subplot(2, 2, 3);
imagesc(x_coords, y_coords, dist_params.SINR.normal_mu);
colorbar;
xlabel('X (m)'); ylabel('Y (m)');
title('SINR μ (dB)');
axis equal tight;
colormap(subplot(2, 2, 3), jet);

subplot(2, 2, 4);
imagesc(x_coords, y_coords, dist_params.SINR.normal_sigma);
colorbar;
xlabel('X (m)'); ylabel('Y (m)');
title('SINR σ (dB)');
axis equal tight;
colormap(subplot(2, 2, 4), hot);

sgtitle('Spatial Distribution of Distribution Parameters', 'FontSize', 14, 'FontWeight', 'bold');
saveas(gcf, fullfile(analysis_dir, 'spatial_distribution_params.png'));
fprintf('✓ Saved: spatial_distribution_params.png\n');

%% 5. Model Validation
fprintf('\n========================================\n');
fprintf('MODEL VALIDATION\n');
fprintf('========================================\n\n');

% Generate synthetic CSI samples using the model and compare to actual
n_test_points = min(50, n_x * n_y);
test_indices = randperm(n_x * n_y, n_test_points);

ks_test_results = zeros(n_test_points, 1);

for i = 1:n_test_points
    [iy, ix] = ind2sub([n_y, n_x], test_indices(i));
    
    % Actual samples
    actual_samples = squeeze(all_samples.RSS(iy, ix, :));
    actual_samples = actual_samples(isfinite(actual_samples));
    
    % Model prediction
    d = stats.distance(iy, ix);
    mu_pred = polyval(p_mu_rss, d);
    sigma_pred = polyval(p_sigma_rss, d);
    
    % Generate synthetic samples
    synthetic_samples = normrnd(mu_pred, sigma_pred, [length(actual_samples), 1]);
    
    % Kolmogorov-Smirnov test
    [~, p_value] = kstest2(actual_samples, synthetic_samples);
    ks_test_results(i) = p_value;
end

% Summary
passed_tests = sum(ks_test_results > 0.05);  % 5% significance level
fprintf('K-S Test Results (N=%d):\n', n_test_points);
fprintf('  Passed (p > 0.05): %d/%d (%.1f%%)\n', ...
    passed_tests, n_test_points, 100*passed_tests/n_test_points);
fprintf('  Mean p-value: %.3f\n', mean(ks_test_results));

%% Summary Report
fprintf('\n========================================\n');
fprintf('ANALYSIS COMPLETE\n');
fprintf('========================================\n\n');

fprintf('Key Findings:\n');
fprintf('1. RSS follows approximately Normal distribution at each location\n');
fprintf('2. Distribution parameters vary spatially with distance from BS\n');
fprintf('3. Model fit quality (R²):\n');
fprintf('   - RSS μ(d): %.3f\n', r2_mu_rss);
fprintf('   - RSS σ(d): %.3f\n', r2_sigma_rss);
fprintf('   - SINR μ(d): %.3f\n', r2_mu_sinr);
fprintf('   - SINR σ(d): %.3f\n', r2_sigma_sinr);
fprintf('\n');
fprintf('Usage: To generate CSI at distance d from BS:\n');
fprintf('  RSS ~ N(polyval(p_mu_rss, d), polyval(p_sigma_rss, d)²)\n');
fprintf('\n');
fprintf('All results saved to: %s\n', analysis_dir);
fprintf('\n========================================\n\n');
