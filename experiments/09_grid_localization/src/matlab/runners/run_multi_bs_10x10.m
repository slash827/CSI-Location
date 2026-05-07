%% Run Multi-BS 10x10 Simulation
% Tests whether multi-BS RSS measurements can replace AoA for localization.
%
% SCENARIO:
%   - 10x10 grid, 2m spacing, Voronoi 4-cell environment (same as voronoi_10x10)
%   - Serving BS at grid center [14, 14, 10]
%   - 2 interfering BSs at opposite grid corners:
%       IBS-1: [5,  5, 10]  (lower-left)
%       IBS-2: [23, 23, 10] (upper-right)
%   - Outputs: rss_wb (serving), sinr_wb, aoa_az, aoa_el
%              rss_ibs_1 (IBS-1 RSS), rss_ibs_2 (IBS-2 RSS)  ← multi-BS features
%   - 400 steps/point = 40,000 total samples
%
% Research question:
%   rss_ibs_1 + rss_ibs_2 add 2D ranging → does this approach AoA accuracy?
%
% Usage:
%   cd experiments/09_grid_localization/src/matlab
%   run_multi_bs_10x10
%
% Output:
%   results/grid_localization/grid_10x10/sim_data_voronoi_multiBs_<timestamp>/
%     - simulation_data.mat  (includes rss_ibs_1, rss_ibs_2 fields)
%     - data_generation_config.jsonc

src_matlab_dir = fileparts(fileparts(mfilename('fullpath')));  % runners/../ = src/matlab
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
global OVERRIDE_CONFIG_NAME;
OVERRIDE_CONFIG_NAME = 'multi_bs_10x10_config.jsonc';

fprintf('=== Multi-BS 10x10 (1 serving + 2 interferers) ===\n');
fprintf('Config: %s\n\n', OVERRIDE_CONFIG_NAME);

generate_simulation_data;

clear src_matlab_dir = fileparts(fileparts(mfilename('fullpath')));  % runners/../ = src/matlab
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
global OVERRIDE_CONFIG_NAME;

fprintf('\n=== Multi-BS 10x10 Complete ===\n');
fprintf('Next steps:\n');
fprintf('  Compare feature sets:\n');
fprintf('    1. rss              (single-BS, distance-only baseline)\n');
fprintf('    2. rss+sinr         (with interference, breaks RSS=SINR degeneracy)\n');
fprintf('    3. rss+rss_ibs_1+rss_ibs_2  (multi-BS RSS ranging)\n');
fprintf('    4. rss+sinr+rss_ibs_1+rss_ibs_2  (full multi-BS)\n');
fprintf('    5. rss+sinr+aoa_azimuth+aoa_elevation  (AoA baseline for comparison)\n');
