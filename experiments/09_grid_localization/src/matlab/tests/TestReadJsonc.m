classdef TestReadJsonc < matlab.unittest.TestCase
% TestReadJsonc — unit tests for read_jsonc.m
%
% Run from MATLAB:
%   cd experiments/09_grid_localization/src/matlab
%   results = runtests('tests/TestReadJsonc');
%   disp(results)

    properties
        ScriptDir  % directory of read_jsonc.m
    end

    methods (TestMethodSetup)
        function addReadJsoncPath(tc)
            test_dir       = fileparts(mfilename('fullpath'));    % tests/
            src_matlab_dir = fileparts(test_dir);                 % src/matlab/
            tc.ScriptDir   = fullfile(src_matlab_dir, 'lib');
            addpath(tc.ScriptDir);
        end
    end

    % ── helpers ──────────────────────────────────────────────────────────────

    methods (Access = private)
        function p = tmpJsonc(~, content)
            % Write content to a temp .jsonc file, return path string.
            p = [tempname, '.jsonc'];
            fid = fopen(p, 'w');
            fprintf(fid, '%s', content);
            fclose(fid);
        end
    end

    % ── tests ─────────────────────────────────────────────────────────────────

    methods (Test)

        function test_plain_json(tc)
            p = tc.tmpJsonc('{"a": 1, "b": "hello"}');
            result = read_jsonc(p);
            tc.verifyEqual(result.a, 1);
            tc.verifyEqual(result.b, 'hello');
        end

        function test_single_line_comment_stripped(tc)
            p = tc.tmpJsonc(sprintf('{\n  // this is a comment\n  "key": 42\n}'));
            result = read_jsonc(p);
            tc.verifyEqual(result.key, 42);
        end

        function test_inline_comment_stripped(tc)
            p = tc.tmpJsonc(sprintf('{\n  "key": 99  // inline\n}'));
            result = read_jsonc(p);
            tc.verifyEqual(result.key, 99);
        end

        function test_nested_object(tc)
            content = sprintf(['{\n  // comment\n  "grid": {\n'...
                               '    "size": 15,  // size\n'...
                               '    "spacing": 2.0\n  }\n}']);
            p = tc.tmpJsonc(content);
            result = read_jsonc(p);
            tc.verifyEqual(result.grid.size, 15);
            tc.verifyEqual(result.grid.spacing, 2.0);
        end

        function test_array_value(tc)
            p = tc.tmpJsonc('{"pos": [48, 48, 10]}');
            result = read_jsonc(p);
            tc.verifyEqual(result.pos, [48, 48, 10]);
        end

        function test_scientific_notation(tc)
            p = tc.tmpJsonc('{"freq": 3.5e9}');
            result = read_jsonc(p);
            tc.verifyEqual(result.freq, 3.5e9, 'AbsTol', 1e3);
        end

        function test_missing_file_errors(tc)
            tc.verifyError(@() read_jsonc('/nonexistent/file.jsonc'), '');
        end

        function test_real_ne_bs_config(tc)
            % Smoke-test: the actual ne_bs config must parse correctly.
            script_d    = fileparts(mfilename('fullpath'));
            config_path = fullfile(script_d, '..', '..', '..', '..', ...
                                   'configs', 'ne_bs_voronoi_15x15_config.jsonc');
            if ~exist(config_path, 'file')
                tc.assumeFail('ne_bs config not found — skipping');
            end
            result = read_jsonc(config_path);
            tc.verifyEqual(result.experiment.name, 'ne_bs_voronoi_15x15');
            tc.verifyEqual(result.base_station.position, [48, 48, 10]);
            tc.verifyEqual(result.grid.size, 15);
        end

    end
end
