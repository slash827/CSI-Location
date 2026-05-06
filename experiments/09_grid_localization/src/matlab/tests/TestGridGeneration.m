classdef TestGridGeneration < matlab.unittest.TestCase
% TestGridGeneration — tests for grid position generation and adjacency maps.
%
% These functions are embedded in generate_simulation_data.m but can be
% tested independently by replicating their logic here.  When the functions
% are eventually extracted into GeometryUtils.m the tests will point there.
%
% Run from MATLAB:
%   cd experiments/09_grid_localization/src/matlab
%   results = runtests('tests/TestGridGeneration');
%   disp(results)

    % ── helpers (replicate grid-gen logic from generate_simulation_data.m) ────

    methods (Static, Access = private)

        function positions = buildGridPositions(grid_size, spacing, offset, ue_height)
            [X, Y] = meshgrid(0:spacing:(grid_size-1)*spacing, ...
                              0:spacing:(grid_size-1)*spacing);
            positions = [X(:) + offset(1), ...
                         Y(:) + offset(2), ...
                         ones(grid_size^2, 1) * ue_height];
        end

        function neighbors = buildNeighbors(grid_size, connectivity)
            n_points  = grid_size^2;
            neighbors = cell(n_points, 1);
            for row = 1:grid_size
                for col = 1:grid_size
                    idx  = (row-1)*grid_size + col;
                    nbrs = [];
                    if col < grid_size,  nbrs = [nbrs, idx+1];            end
                    if col > 1,          nbrs = [nbrs, idx-1];            end
                    if row < grid_size,  nbrs = [nbrs, idx+grid_size];    end
                    if row > 1,          nbrs = [nbrs, idx-grid_size];    end
                    if connectivity == 8
                        if row>1 && col>1,                          nbrs = [nbrs, idx-grid_size-1]; end
                        if row>1 && col<grid_size,                  nbrs = [nbrs, idx-grid_size+1]; end
                        if row<grid_size && col>1,                  nbrs = [nbrs, idx+grid_size-1]; end
                        if row<grid_size && col<grid_size,          nbrs = [nbrs, idx+grid_size+1]; end
                    end
                    neighbors{idx} = nbrs;
                end
            end
        end

    end

    % ── grid position tests ───────────────────────────────────────────────────

    methods (Test)

        function test_grid_point_count(tc)
            pos = TestGridGeneration.buildGridPositions(15, 2.0, [5,5], 1.5);
            tc.verifyEqual(size(pos, 1), 225);  % 15x15
            tc.verifyEqual(size(pos, 2), 3);    % x, y, z
        end

        function test_grid_extent_15x15(tc)
            % spacing=2, offset=[5,5], size=15 → X,Y in [5, 33]
            pos = TestGridGeneration.buildGridPositions(15, 2.0, [5,5], 1.5);
            tc.verifyEqual(min(pos(:,1)), 5.0,  'AbsTol', 1e-9);
            tc.verifyEqual(max(pos(:,1)), 33.0, 'AbsTol', 1e-9);
            tc.verifyEqual(min(pos(:,2)), 5.0,  'AbsTol', 1e-9);
            tc.verifyEqual(max(pos(:,2)), 33.0, 'AbsTol', 1e-9);
        end

        function test_ue_height_uniform(tc)
            pos = TestGridGeneration.buildGridPositions(10, 5.0, [0,0], 2.0);
            tc.verifyTrue(all(pos(:,3) == 2.0));
        end

        function test_grid_spacing(tc)
            % All consecutive x-values in the first row differ by exactly spacing.
            spacing = 2.0;
            pos     = TestGridGeneration.buildGridPositions(5, spacing, [0,0], 1.5);
            x_vals  = sort(unique(pos(:,1)));
            diffs   = diff(x_vals);
            tc.verifyTrue(all(abs(diffs - spacing) < 1e-9));
        end

        % ── BS geometry check for ne_bs experiment ──────────────────────────

        function test_ne_bs_outside_grid(tc)
            % Serving BS at (48,48) must be outside the 15x15 grid [5,33]
            bs = [48, 48, 10];
            pos = TestGridGeneration.buildGridPositions(15, 2.0, [5,5], 1.5);
            x_range = [min(pos(:,1)), max(pos(:,1))];
            y_range = [min(pos(:,2)), max(pos(:,2))];
            tc.verifyTrue(bs(1) > x_range(2) || bs(2) > y_range(2), ...
                'NE BS should be outside the grid boundary');
        end

        function test_ne_bs_azimuth_spread(tc)
            % All 225 grid points, viewed from BS (48,48), must span <90 degrees.
            bs  = [48, 48, 10];
            pos = TestGridGeneration.buildGridPositions(15, 2.0, [5,5], 1.5);
            dx  = pos(:,1) - bs(1);
            dy  = pos(:,2) - bs(2);
            az  = atan2d(dx, dy);   % azimuth in degrees
            spread = max(az) - min(az);
            tc.verifyLessThan(spread, 90, ...
                sprintf('Expected <90 deg spread from NE BS, got %.1f deg', spread));
        end

        function test_center_bs_azimuth_spread(tc)
            % Center BS (19,19) should give much wider angular spread (>270 deg).
            % (Points almost surround the BS.)
            bs  = [19, 19, 10];
            pos = TestGridGeneration.buildGridPositions(15, 2.0, [5,5], 1.5);
            dx  = pos(:,1) - bs(1);
            dy  = pos(:,2) - bs(2);
            az  = atan2d(dx, dy);
            spread = max(az) - min(az);
            tc.verifyGreaterThan(spread, 270);
        end

    end

    % ── adjacency / neighbor tests ────────────────────────────────────────────

    methods (Test)

        function test_4conn_corner_has_2_neighbors(tc)
            % Top-left corner (index 1) has exactly 2 neighbors in 4-connectivity.
            nbrs = TestGridGeneration.buildNeighbors(5, 4);
            tc.verifyEqual(numel(nbrs{1}), 2);
        end

        function test_4conn_edge_has_3_neighbors(tc)
            % Top-edge center (index 3 in a 5x5 grid) has 3 neighbors.
            nbrs = TestGridGeneration.buildNeighbors(5, 4);
            tc.verifyEqual(numel(nbrs{3}), 3);
        end

        function test_4conn_interior_has_4_neighbors(tc)
            % Interior point (e.g. index 7 = row2, col2 in 5x5) has 4 neighbors.
            nbrs = TestGridGeneration.buildNeighbors(5, 4);
            tc.verifyEqual(numel(nbrs{7}), 4);
        end

        function test_8conn_corner_has_3_neighbors(tc)
            nbrs = TestGridGeneration.buildNeighbors(5, 8);
            tc.verifyEqual(numel(nbrs{1}), 3);
        end

        function test_8conn_interior_has_8_neighbors(tc)
            % Interior point in 8-connectivity has 8 neighbors.
            nbrs = TestGridGeneration.buildNeighbors(5, 8);
            tc.verifyEqual(numel(nbrs{7}), 8);
        end

        function test_neighbors_are_symmetric(tc)
            % If B is a neighbor of A, A must be a neighbor of B.
            nbrs = TestGridGeneration.buildNeighbors(10, 8);
            n    = numel(nbrs);
            for i = 1:n
                for j = nbrs{i}
                    tc.verifyTrue(ismember(i, nbrs{j}), ...
                        sprintf('Asymmetric: %d neighbor of %d but not vice versa', i, j));
                end
            end
        end

        function test_no_self_loops(tc)
            nbrs = TestGridGeneration.buildNeighbors(10, 8);
            for i = 1:numel(nbrs)
                tc.verifyFalse(ismember(i, nbrs{i}), ...
                    sprintf('Point %d is its own neighbor', i));
            end
        end

        function test_walk_stays_in_grid(tc)
            % A random walk of 10000 steps must never leave the grid.
            rng(42);
            grid_size   = 15;
            nbrs        = TestGridGeneration.buildNeighbors(grid_size, 8);
            n_points    = grid_size^2;
            n_steps     = 10000;
            walk        = zeros(n_steps + 1, 1);
            walk(1)     = ceil(n_points / 2);

            for s = 1:n_steps
                cands   = nbrs{walk(s)};
                walk(s+1) = cands(randi(numel(cands)));
            end

            tc.verifyTrue(all(walk >= 1) && all(walk <= n_points));
        end

        function test_walk_visits_majority_of_grid(tc)
            % A long walk should visit most grid points (coverage test).
            rng(42);
            grid_size = 15;
            nbrs      = TestGridGeneration.buildNeighbors(grid_size, 8);
            n_points  = grid_size^2;
            n_steps   = n_points * 400;    % 400 steps per point (same as config)
            walk      = zeros(n_steps + 1, 1);
            walk(1)   = ceil(n_points / 2);

            for s = 1:n_steps
                cands     = nbrs{walk(s)};
                walk(s+1) = cands(randi(numel(cands)));
            end

            n_visited = numel(unique(walk));
            tc.verifyGreaterThan(n_visited / n_points, 0.95, ...
                sprintf('Walk visited only %.0f%% of grid points', ...
                        n_visited/n_points*100));
        end

    end
end
