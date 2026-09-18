%% SETUP SCRIPT - Run this once to configure your workspace
% This script:
% 1. Checks QuaDRiGa installation
% 2. Adds project paths
% 3. Verifies everything works
% 4. Shows you what to do next

clear; clc;
fprintf('========================================\n');
fprintf('CSI LOCATION PROJECT - SETUP\n');
fprintf('========================================\n\n');

%% Step 1: Check QuaDRiGa
fprintf('Step 1: Checking QuaDRiGa installation...\n');
if ~exist('qd_simulation_parameters', 'file')
    % Search, rather than assuming one machine's layout. Set the QUADRIGA_HOME
    % environment variable to skip the guesswork on a new machine.
    candidates = {getenv('QUADRIGA_HOME'), ...
                  'D:\programs\QuaDRiGa', ...
                  'C:\programs\QuaDRiGa', ...
                  fullfile(getenv('USERPROFILE'), 'QuaDRiGa'), ...
                  fullfile(fileparts(mfilename('fullpath')), '..', 'QuaDRiGa')};
    for c = 1:numel(candidates)
        if ~isempty(candidates{c}) && isfolder(candidates{c})
            addpath(genpath(candidates{c}));
            if exist('qd_simulation_parameters', 'file')
                fprintf('  Found QuaDRiGa at: %s\n', candidates{c});
                savepath;
                break;
            end
        end
    end
end

if exist('qd_simulation_parameters', 'file')
    fprintf('  ✓ QuaDRiGa found!\n');
    qd_path = which('qd_simulation_parameters');
    fprintf('  Location: %s\n\n', fileparts(qd_path));
else
    fprintf('  ✗ QuaDRiGa NOT FOUND!\n\n');
    fprintf('  Please install QuaDRiGa:\n');
    fprintf('  1. Download from: https://quadriga-channel-model.de/\n');
    fprintf('  2. Extract to folder (e.g., D:\\programs\\QuaDRiGa)\n');
    fprintf('  3. Add to path: addpath(genpath(''D:\\programs\\QuaDRiGa''));\n');
    fprintf('  4. Save path: savepath;\n');
    fprintf('  5. Re-run this script\n\n');
    fprintf('========================================\n');
    return;
end

%% Step 2: Add project paths
fprintf('Step 2: Adding project paths...\n');
project_root = fileparts(mfilename('fullpath'));
utils_path = fullfile(project_root, 'utils');
experiments_path = fullfile(project_root, 'experiments');
results_path = fullfile(project_root, 'results');

if exist(utils_path, 'dir')
    addpath(utils_path);
    fprintf('  ✓ Added utils/ to path\n');
end

if exist(experiments_path, 'dir')
    fprintf('  ✓ Found experiments/ folder\n');
end

if ~exist(results_path, 'dir')
    mkdir(results_path);
    fprintf('  ✓ Created results/ folder\n');
else
    fprintf('  ✓ Found results/ folder\n');
end

% Save path
try
    savepath;
    fprintf('  ✓ Path saved permanently\n\n');
catch
    fprintf('  ⚠ Could not save path (may need admin rights)\n');
    fprintf('    You''ll need to run setup again next time\n\n');
end

%% Step 3: Check CSIMetrics
fprintf('Step 3: Checking utilities...\n');
if exist('CSIMetrics', 'file')
    fprintf('  ✓ CSIMetrics class found\n\n');
else
    fprintf('  ✗ CSIMetrics class NOT found\n');
    fprintf('    Check that utils/CSIMetrics.m exists\n\n');
end

%% Step 4: Quick test
fprintf('Step 4: Running quick test...\n');
try
    s = qd_simulation_parameters;
    s.center_frequency = 3.5e9;
    l = qd_layout(s);
    l.tx_position = [0; 0; 25];
    l.rx_position = [50; 0; 1.5];
    l.tx_array = qd_arrayant('omni');
    l.rx_array = qd_arrayant('omni');
    l.set_scenario('3GPP_38.901_UMa_LOS');
    c = l.get_channels;
    H = c.coeff;
    
    fprintf('  ✓ QuaDRiGa simulation successful!\n');
    fprintf('  ✓ Generated CSI matrix: %s\n\n', mat2str(size(H)));
catch ME
    fprintf('  ✗ Test failed: %s\n\n', ME.message);
end

%% Step 5: Show structure
fprintf('========================================\n');
fprintf('PROJECT STRUCTURE\n');
fprintf('========================================\n');
fprintf('CSI_location/\n');
fprintf('├── experiments/          ← Your experiments here\n');
fprintf('│   ├── 01_basics/        ← START HERE!\n');
fprintf('│   ├── 02_single_ue_analysis/\n');
fprintf('│   ├── 03_ue_movement/\n');
fprintf('│   ├── 04_data_generation/\n');
fprintf('│   └── 05_ml_training/\n');
fprintf('├── utils/                ← Helper functions\n');
fprintf('│   └── CSIMetrics.m\n');
fprintf('├── results/              ← Output goes here\n');
fprintf('├── docs/                 ← Documentation\n');
fprintf('└── setup.m               ← This file\n\n');

%% Step 6: Next steps
fprintf('========================================\n');
fprintf('SETUP COMPLETE! 🎉\n');
fprintf('========================================\n\n');

fprintf('NEXT STEPS:\n\n');
fprintf('1. Read the overview:\n');
fprintf('   >> open experiments/EXPERIMENT_INDEX.md\n\n');

fprintf('2. Start with basics:\n');
fprintf('   >> cd experiments/01_basics\n');
fprintf('   >> exp01_minimal_setup\n\n');

fprintf('3. Progress through experiments:\n');
fprintf('   - Level 1: Basics (3 experiments, ~30 min)\n');
fprintf('   - Level 2: Single UE Analysis\n');
fprintf('   - Level 3: UE Movement\n');
fprintf('   - Level 4: Data Generation\n');
fprintf('   - Level 5: ML Training\n\n');

fprintf('4. Get help:\n');
fprintf('   - Each folder has README.md\n');
fprintf('   - See docs/ for comprehensive guides\n');
fprintf('   - Console output explains everything\n\n');

fprintf('========================================\n');
fprintf('Ready to start? Run:\n');
fprintf('  cd experiments/01_basics\n');
fprintf('  exp01_minimal_setup\n');
fprintf('========================================\n');
