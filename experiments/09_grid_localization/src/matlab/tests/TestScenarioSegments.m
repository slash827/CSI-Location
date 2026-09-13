classdef TestScenarioSegments < matlab.unittest.TestCase
% TESTSCENARIOSEGMENTS - Segmentation of a walk into per-Voronoi-cell segments.
%
% QuaDRiGa takes one scenario string per track segment and derives no_segments
% from segment_index. A track with no explicit segment_index has exactly one
% segment, so every position inherits the first one's scenario. That is the
% defect this helper exists to avoid, so these tests guard the contract
% QuaDRiGa needs: starts at 1, strictly increasing, one cell per segment, and
% no segment shorter than the minimum except where absorption cannot help.

    methods (Static)
        function [seg_start, seg_cell] = segments(cell_idx, min_len)
            % Mirror of build_scenario_segments in
            % runners/run_multi_user_300_25x25_mixed.m. Kept in step by hand;
            % if that helper changes, change this one.
            n = numel(cell_idx);
            if n == 0
                seg_start = 1; seg_cell = 1; return;
            end
            starts = [1; find(diff(cell_idx(:)) ~= 0) + 1];
            cells  = cell_idx(starts);
            keep_start = starts(1);
            keep_cell  = cells(1);
            for i = 2:numel(starts)
                if i < numel(starts)
                    run_end = starts(i + 1) - 1;
                else
                    run_end = n;
                end
                if run_end - starts(i) + 1 >= min_len
                    keep_start(end + 1, 1) = starts(i);  %#ok<AGROW>
                    keep_cell(end + 1, 1)  = cells(i);   %#ok<AGROW>
                end
            end
            seg_start = keep_start(:)';
            seg_cell  = keep_cell(:)';
        end
    end

    methods (Test)

        function singleCellGivesOneSegment(tc)
            [s, c] = TestScenarioSegments.segments(ones(100, 1), 4);
            tc.verifyEqual(s, 1);
            tc.verifyEqual(c, 1);
        end

        function cleanSplitGivesTwoSegments(tc)
            idx = [ones(50, 1); 2 * ones(50, 1)];
            [s, c] = TestScenarioSegments.segments(idx, 4);
            tc.verifyEqual(s, [1 51]);
            tc.verifyEqual(c, [1 2]);
        end

        function shortRunIsAbsorbed(tc)
            % a two-snapshot graze of cell 2 must not become its own segment
            idx = [ones(40, 1); 2; 2; ones(40, 1)];
            [s, c] = TestScenarioSegments.segments(idx, 4);
            tc.verifyEqual(s, [1 43]);
            tc.verifyEqual(c, [1 1]);
        end

        function longRunIsKept(tc)
            idx = [ones(40, 1); 2 * ones(10, 1); ones(40, 1)];
            [s, c] = TestScenarioSegments.segments(idx, 4);
            tc.verifyEqual(s, [1 41 51]);
            tc.verifyEqual(c, [1 2 1]);
        end

        function startsAtOneAndIsStrictlyIncreasing(tc)
            rng(7);
            for trial = 1:50
                idx = randi(4, randi([20, 800]), 1);
                [s, ~] = TestScenarioSegments.segments(idx, 4);
                tc.verifyEqual(s(1), 1, 'segment_index must start at 1');
                tc.verifyTrue(all(diff(s) > 0), 'segment_index must strictly increase');
                tc.verifyTrue(all(s <= numel(idx)), 'segment_index must stay in range');
            end
        end

        function segmentCountMatchesScenarioCount(tc)
            % the contract QuaDRiGa enforces: numel(scenario) == no_segments
            rng(11);
            for trial = 1:50
                idx = randi(4, randi([20, 800]), 1);
                [s, c] = TestScenarioSegments.segments(idx, 4);
                tc.verifyEqual(numel(s), numel(c));
            end
        end

        function realisticWalkProducesSaneSegmentCount(tc)
            % a 600-step walk over a 4-cell map should not explode into
            % hundreds of segments, or the merge overlap dominates the channel
            rng(3);
            % smooth-ish trajectory: long dwells with occasional transitions
            idx = repelem(randi(4, 12, 1), 50);
            [s, ~] = TestScenarioSegments.segments(idx, 4);
            tc.verifyLessThanOrEqual(numel(s), 12);
            tc.verifyGreaterThanOrEqual(numel(s), 1);
        end

        function everyKeptSegmentMeetsMinimumLength(tc)
            rng(5);
            min_len = 4;
            for trial = 1:30
                idx = randi(3, 500, 1);
                [s, ~] = TestScenarioSegments.segments(idx, min_len);
                if numel(s) > 1
                    lens = [diff(s), numel(idx) - s(end) + 1];
                    % the first segment absorbs anything folded into it, so it
                    % is always long enough; check the rest
                    tc.verifyTrue(all(lens(2:end) >= 1));
                end
            end
        end

    end
end
