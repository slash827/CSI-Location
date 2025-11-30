% Emergency script to save partial progress from OOM situation
% Run this in the MATLAB workspace where exp13_urban_dataset failed

fprintf('Saving partial progress...\n');

% Use the output_dir variable that should exist in workspace
if ~exist('output_dir', 'var')
    % Try to find it from checkpoint or manually construct
    if exist('checkpoint_file', 'var')
        output_dir = fileparts(fileparts(checkpoint_file));
    else
        error('Cannot find output_dir. Please set it manually: output_dir = ''path/to/exp13_YYYY-MM-DD_HH-MM-SS'';');
    end
end

dataset_dir = fullfile(output_dir, 'dataset');
fprintf('Output directory: %s\n', output_dir);

% Save what we have
if exist('train_data', 'var')
    fprintf('Saving training data (%d samples)...\n', length(train_data.positions_x));
    save(fullfile(dataset_dir, 'train_data_partial.mat'), '-struct', 'train_data', '-v7.3');
end

if exist('val_data', 'var')
    fprintf('Saving validation data (%d samples)...\n', length(val_data.positions_x));
    save(fullfile(dataset_dir, 'val_data_partial.mat'), '-struct', 'val_data', '-v7.3');
end

if exist('metadata', 'var')
    fprintf('Saving metadata...\n');
    save(fullfile(dataset_dir, 'metadata_partial.mat'), '-struct', 'metadata', '-v7.3');
end

fprintf('\n✓ Partial progress saved!\n');
fprintf('Files saved in: %s\n', dataset_dir);
fprintf('\nYou now have ~%d samples saved.\n', length(train_data.positions_x) + length(val_data.positions_x));
