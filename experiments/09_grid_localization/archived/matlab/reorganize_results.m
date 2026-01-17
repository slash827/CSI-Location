%% Reorganize Results into Grid Localization Structure
% This script moves existing experiment results into the new structure:
% results/grid_localization/grid_NxN/exp_*

clear; clc;

% Setup paths
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
results_dir = fullfile(project_root, 'results');

fprintf('Running from: experiments/09_grid_localization\n');

fprintf('========================================\n');
fprintf('Reorganizing Results Folders\n');
fprintf('========================================\n\n');

% Get all exp13* folders in results directory
folders = dir(fullfile(results_dir, 'exp13*'));
folders = folders([folders.isdir]);

if isempty(folders)
    fprintf('No exp13* folders found in results directory.\n');
    return;
end

fprintf('Found %d experiment folders to reorganize.\n\n', length(folders));

% Create grid_localization directory
grid_loc_dir = fullfile(results_dir, 'grid_localization');
if ~exist(grid_loc_dir, 'dir')
    mkdir(grid_loc_dir);
    fprintf('Created directory: %s\n\n', grid_loc_dir);
end

% Process each folder
moved_count = 0;
skipped_count = 0;

for i = 1:length(folders)
    folder_name = folders(i).name;
    source_path = fullfile(results_dir, folder_name);
    
    % Try to determine grid size from config file
    config_file = fullfile(source_path, 'corrected_comparison_results.mat');
    
    if exist(config_file, 'file')
        try
            data = load(config_file, 'config');
            grid_size = data.config.grid_size;
            
            % Create grid-specific subdirectory
            grid_subdir = sprintf('grid_%dx%d', grid_size, grid_size);
            target_base = fullfile(grid_loc_dir, grid_subdir);
            
            if ~exist(target_base, 'dir')
                mkdir(target_base);
                fprintf('Created directory: %s\n', grid_subdir);
            end
            
            % Move folder
            target_path = fullfile(target_base, folder_name);
            
            if exist(target_path, 'dir')
                fprintf('  [SKIP] %s already exists in %s\n', folder_name, grid_subdir);
                skipped_count = skipped_count + 1;
            else
                movefile(source_path, target_path);
                fprintf('  [MOVED] %s -> %s/%s\n', folder_name, grid_subdir, folder_name);
                moved_count = moved_count + 1;
            end
            
        catch ME
            fprintf('  [ERROR] Could not process %s: %s\n', folder_name, ME.message);
            skipped_count = skipped_count + 1;
        end
    else
        fprintf('  [SKIP] %s (no config file found)\n', folder_name);
        skipped_count = skipped_count + 1;
    end
end

fprintf('\n========================================\n');
fprintf('Summary:\n');
fprintf('  Moved:   %d folders\n', moved_count);
fprintf('  Skipped: %d folders\n', skipped_count);
fprintf('  Total:   %d folders\n', length(folders));
fprintf('========================================\n');
