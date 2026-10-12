function build_region_map(dataDir, outFile)
%% build_region_map.m
% Precomputes one convex hull per area_id, pooling (x, y) points across
% every UE log CSV in dataDir, and saves the result to outFile.
%
% build_region_map(dataDir) saves to fullfile(dataDir, 'region_map.mat').
% build_region_map(dataDir, outFile) saves to outFile instead.
%
% Rationale: approximating an area's extent from a single UE's sparse,
% zig-zagging trajectory is noisy (a hull either over-fills unvisited gaps,
% or a tighter shape bridges/misses depending on that one route's path).
% With thousands of pooled points per area from many independent routes,
% a plain convex hull is a much more stable, honest footprint -- and
% computing it once and caching it means every UE plot overlays the same
% fixed backdrop instead of re-deriving its own approximation.
%
% Run this once per dataDir (or whenever its CSVs are added/changed):
%   build_region_map(dataDir)
% plot_ue_log.m / plot_all_ue_logs.m then load the resulting .mat rather
% than recomputing anything.

%% Configuration
if nargin < 2 || isempty(outFile)
    outFile = fullfile(dataDir, 'region_map.mat');
end
filePattern = '*.csv';

%% Pool (x, y, area_id, serving_bs) across every log
files = dir(fullfile(dataDir, filePattern));
if isempty(files)
    error('build_region_map:noFiles', ...
        'No files matching %s found in %s', filePattern, dataDir);
end

nFiles = numel(files);
allX = cell(nFiles, 1);
allY = cell(nFiles, 1);
allArea = cell(nFiles, 1);
allBs = cell(nFiles, 1);

nUsed = 0;
for k = 1:nFiles
    fp = fullfile(files(k).folder, files(k).name);
    Tk = readtable(fp);
    if ~all(ismember({'x', 'y', 'area_id', 'serving_bs'}, Tk.Properties.VariableNames))
        warning('build_region_map:skipFile', ...
            'Skipping %s (missing x/y/area_id/serving_bs)', files(k).name);
        continue;
    end
    allX{k} = Tk.x;
    allY{k} = Tk.y;
    allArea{k} = Tk.area_id;
    allBs{k} = Tk.serving_bs;
    nUsed = nUsed + 1;
end
fprintf('Pooled points from %d of %d files.\n', nUsed, nFiles);

bigX = vertcat(allX{:});
bigY = vertcat(allY{:});
bigArea = vertcat(allArea{:});
bigBs = vertcat(allBs{:});

% Every BS id / area id that appears anywhere in the dataset, so callers
% can always show a complete, consistent BS legend and size their area
% color palette correctly, even for a UE log that only used a subset.
allBsIds = sort(unique(bigBs));
allAreaIds = sort(unique(bigArea));

%% One convex hull per area id
regionMap = struct('area_id', {}, 'hull_x', {}, 'hull_y', {}, 'n_points', {});

for i = 1:numel(allAreaIds)
    a = allAreaIds(i);
    mask = bigArea == a;
    px = bigX(mask);
    py = bigY(mask);
    k = convhull(px, py);
    regionMap(end + 1) = struct( ...
        'area_id', a, 'hull_x', px(k), 'hull_y', py(k), 'n_points', nnz(mask)); %#ok<AGROW>
    fprintf('  Area %d: %d pooled points, hull has %d vertices\n', a, nnz(mask), numel(k));
end

save(outFile, 'regionMap', 'allBsIds', 'allAreaIds');
fprintf('Saved %s with %d regions and %d BS ids.\n', outFile, numel(regionMap), numel(allBsIds));
end
