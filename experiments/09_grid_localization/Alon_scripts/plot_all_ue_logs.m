function plot_all_ue_logs(dataDir, outDir)
%% plot_all_ue_logs.m
% Plot every UE trajectory log CSV in dataDir, saving one PNG per log.
%
% plot_all_ue_logs(dataDir) saves PNGs to fullfile(dataDir, 'plots').
% plot_all_ue_logs(dataDir, outDir) saves to outDir instead.
%
% Requires a region map already built for dataDir -- see build_region_map.m.

%% Configuration
if nargin < 2 || isempty(outDir)
    outDir = fullfile(dataDir, 'plots');
end
if ~isfolder(outDir)
    mkdir(outDir);
end

regionMapFile = fullfile(dataDir, 'region_map.mat');
if ~isfile(regionMapFile)
    error('plot_all_ue_logs:missingRegionMap', ...
        ['Region map not found: %s\n' ...
         'Run build_region_map(''%s'') once to generate it.'], regionMapFile, dataDir);
end

%% Find and plot all log files
files = dir(fullfile(dataDir, '*.csv'));
if isempty(files)
    error('plot_all_ue_logs:noFiles', 'No CSV files found in %s', dataDir);
end

for ticker = 1:numel(files)
    plot_ue_log(files(ticker).name, dataDir, regionMapFile);
    set(gcf, 'Color', 'white');
    saveas(gcf, fullfile(outDir, [files(ticker).name(1:end-3), 'png']));
    close(gcf);
end
end
