function qd_dir = ensure_quadriga()
%ENSURE_QUADRIGA  Put QuaDRiGa on the MATLAB path (also on parfor workers) and return its folder.
%
%   Looks for qd_simulation_parameters on the path, then in $QUADRIGA_HOME and a few
%   usual places. Errors if it cannot be found. Call it at the top of any runner and
%   of any function that runs on a parallel worker.

    if exist('qd_simulation_parameters', 'file')
        qd_dir = fileparts(which('qd_simulation_parameters'));
        return;
    end
    candidates = {getenv('QUADRIGA_HOME'), ...
                  fullfile(getenv('USERPROFILE'), 'Documents', 'programs', 'QuaDRiGa'), ...
                  fullfile(getenv('USERPROFILE'), 'QuaDRiGa'), ...
                  'D:\programs\QuaDRiGa', 'C:\programs\QuaDRiGa'};
    for c = 1:numel(candidates)
        if ~isempty(candidates{c}) && isfolder(candidates{c})
            addpath(genpath(candidates{c}));
            if exist('qd_simulation_parameters', 'file')
                qd_dir = fileparts(which('qd_simulation_parameters'));
                return;
            end
        end
    end
    error('QuaDRiGa not found. Set the QUADRIGA_HOME environment variable to its folder.');
end
