%% verify_reorganisation.m — smoke-test the src/matlab/ reorganisation
%
% Verifies that all lib/ files are reachable after moving to core/ lib/ runners/
% and that their public APIs work correctly with simple inputs.
% Does NOT require QuaDRiGa or a full simulation run.
%
% Run from MATLAB:
%   cd experiments/09_grid_localization/src/matlab
%   verify_reorganisation
%
% Expected output: a series of [OK] lines with no errors.

fprintf('=== verify_reorganisation — src/matlab/ path smoke-test ===\n\n');

% ── 1. Path setup (mirrors how runners set up paths) ─────────────────────────
test_dir       = fileparts(mfilename('fullpath'));   % tests/
src_matlab_dir = fileparts(test_dir);               % src/matlab/
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
fprintf('[OK] addpath(core/) and addpath(lib/) succeeded\n');

% ── 2. read_jsonc — lib/read_jsonc.m ─────────────────────────────────────────
config_path = fullfile(src_matlab_dir, '..', '..', 'configs', ...
                       'ne_bs_voronoi_15x15_config.jsonc');
cfg = read_jsonc(config_path);
assert(strcmp(cfg.experiment.name, 'ne_bs_voronoi_15x15'), ...
    'read_jsonc: experiment name mismatch');
assert(cfg.grid.size == 15, 'read_jsonc: grid size mismatch');
assert(isequal(cfg.base_station.position, [48, 48, 10]), ...
    'read_jsonc: BS position mismatch');
fprintf('[OK] read_jsonc — parsed ne_bs_voronoi_15x15_config.jsonc correctly\n');

% ── 3. GeometryUtils.euclidean_distance — lib/GeometryUtils.m ────────────────
d = GeometryUtils.euclidean_distance([0 0], [3 4]);
assert(abs(d - 5.0) < 1e-10, 'GeometryUtils.euclidean_distance: expected 5.0');
fprintf('[OK] GeometryUtils.euclidean_distance([0,0],[3,4]) = %.4f  (expected 5.0)\n', d);

% ── 4. GeometryUtils.check_if_in_bounds ──────────────────────────────────────
bounds = struct('x_min', 0, 'x_max', 10, 'y_min', 0, 'y_max', 10);
assert(GeometryUtils.check_if_in_bounds([5, 5], bounds), ...
    'GeometryUtils.check_if_in_bounds: [5,5] should be inside [0-10,0-10]');
assert(~GeometryUtils.check_if_in_bounds([15, 5], bounds), ...
    'GeometryUtils.check_if_in_bounds: [15,5] should be outside [0-10,0-10]');
fprintf('[OK] GeometryUtils.check_if_in_bounds — inside/outside correct\n');

% ── 5. AreaGenerator.generate — lib/AreaGenerator.m ─────────────────────────
ag_cfg = struct();
ag_cfg.num_areas         = 4;
ag_cfg.area_bounds       = bounds;
ag_cfg.area_types        = {'residential', 'office', 'shopping_center', 'park'};
ag_cfg.transition_width  = 2.0;
ag_cfg.random_seed       = 42;
areas = AreaGenerator.generate(ag_cfg);
assert(length(areas) == 4, 'AreaGenerator.generate: expected 4 areas');
assert(isfield(areas(1), 'id'),       'AreaGenerator: missing field id');
assert(isfield(areas(1), 'seed'),     'AreaGenerator: missing field seed');
assert(isfield(areas(1), 'scenario'), 'AreaGenerator: missing field scenario');
fprintf('[OK] AreaGenerator.generate — produced %d areas with correct fields\n', length(areas));

% ── 6. TrafficUtils.get_area_load — lib/TrafficUtils.m ───────────────────────
traffic_cfg = struct('traffic_variation', 0.1);
t_peak   = datetime(2026, 5, 1, 14, 0, 0);  % 14:00 — peak for shopping_center
t_offpeak = datetime(2026, 5, 1,  3, 0, 0); %  3:00 — off-peak
load_peak    = TrafficUtils.get_area_load('shopping_center', t_peak,    traffic_cfg);
load_offpeak = TrafficUtils.get_area_load('shopping_center', t_offpeak, traffic_cfg);
assert(load_peak > load_offpeak, ...
    'TrafficUtils: peak load should exceed off-peak load for shopping_center');
fprintf('[OK] TrafficUtils.get_area_load — peak (%.2f) > off-peak (%.2f)\n', ...
        load_peak, load_offpeak);

% ── 7. core/ reachable (generate_simulation_data exists on path) ─────────────
assert(exist('generate_simulation_data', 'file') == 2, ...
    'core/generate_simulation_data.m not found — addpath(core/) may have failed');
fprintf('[OK] generate_simulation_data.m is reachable from core/\n');

fprintf('\n=== All checks passed — reorganisation verified ===\n');
