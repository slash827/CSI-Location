function plot_ue_log(csvFile_name, dataDir, regionMapFile)
%% plot_ue_log.m
% Import a UE log CSV (e.g. ue_003.csv) and produce a single figure:
%   left column (stacked):  RSRP, RSRQ, SINR vs time, colored by serving_bs
%   right column:           square x/y map of UE positions, colored by serving_bs
%   bottom:                 one shared horizontal legend for the whole figure
%
% plot_ue_log(csvFileName, dataDir) plots fullfile(dataDir, csvFileName).
% plot_ue_log(csvFileName, dataDir, regionMapFile) overrides the default
% region-map path of fullfile(dataDir, 'region_map.mat').
%
% Expected CSV columns: timestamp,x,y,area_id,rsrp,rsrq,sinr,cqi,serving_bs,distance
% Uses only base MATLAB (no toolboxes required).

%% Configuration
if nargin < 3 || isempty(regionMapFile)
    regionMapFile = fullfile(dataDir, 'region_map.mat');
end
csvFile = fullfile(dataDir, csvFile_name);

%% Import
T = readtable(csvFile);

requiredVars = {'timestamp', 'x', 'y', 'rsrp', 'rsrq', 'sinr', 'serving_bs', 'area_id', 'distance'};
missingVars = setdiff(requiredVars, T.Properties.VariableNames);
if ~isempty(missingVars)
    error('plot_ue_log:missingColumns', ...
        'CSV is missing expected column(s): %s', strjoin(missingVars, ', '));
end

if ~isfile(regionMapFile)
    error('plot_ue_log:missingRegionMap', ...
        ['Region map not found: %s\n' ...
         'Run build_region_map(dataDir) once to generate it.'], regionMapFile);
end
mapData = load(regionMapFile, 'regionMap', 'allBsIds', 'allAreaIds');

% Every BS id / area id that appears anywhere in the dataset (not just this
% file), so BS N is always the same color and always gets a legend entry
% even for a UE log that only ever used one of them, and the area palette
% is sized for the whole dataset rather than a fixed assumed count.
allBsIds    = mapData.allBsIds;
bsNames     = compose('BS %d', allBsIds);
bsPalette   = bsColorPalette(max(allBsIds));
colors      = bsPalette(allBsIds, :);
areaPalette = bsColorPalette(max(mapData.allAreaIds));

% Handover events: rows where the serving BS changes from the previous row.
% Each event gets its own color (in time order) so the vertical line on the
% quality plots, the small diamond on their time axis, and the diamond on
% the map can all be matched by eye.
transIdx    = find(diff(T.serving_bs) ~= 0) + 1;
nTrans      = numel(transIdx);
transColors = turbo(max(nTrans, 1));
transColors = transColors(1:nTrans, :);
transTimes  = T.timestamp(transIdx);

% Handle jump discontinuities in distance at handover transitions
t_dist = T.timestamp;
d_dist = T.distance;
for i = numel(transIdx):-1:1
    idx = transIdx(i);
    t_dist = [t_dist(1:idx-1); NaN; t_dist(idx:end)];
    d_dist = [d_dist(1:idx-1); NaN; d_dist(idx:end)];
end

% Sample interval, used to close the small gap between adjacent area-shading
% regions so contiguous same-area runs butt up against each other cleanly.
dt = median(diff(T.timestamp));

%% Single figure: 3 stacked quality plots on the left, square map on the right,
%% one shared horizontal legend spanning the bottom
figure('Name', 'UE Log', 'Color', 'w');
tl = tiledlayout(3, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
title(tl, csvFile, 'Interpreter', 'none');

timeLim = [T.timestamp(1), T.timestamp(end)];

% 1) SINR vs time
nexttile(1);
yyaxis left;
ax3 = gca; ax3.YColor = 'k';
shadeAreas(T.timestamp, T.area_id, dt, areaPalette);
plotByBs(T.timestamp, T.sinr, T.serving_bs, allBsIds, bsNames, colors);
markTransitions(transTimes, transColors);
xlabel('Time (s)');
ylabel('SINR (dB)');

yyaxis right;
hDist = plot(t_dist, d_dist, 'r-', 'LineWidth', 1.2, 'DisplayName', 'Distance to BS');
ylabel('Distance (m)');
ax3.YColor = 'r';
title('SINR vs Time');
xlim(timeLim);
grid on;

% 2) RSRP vs time
nexttile(3);
yyaxis left;
ax1 = gca; ax1.YColor = 'k';
shadeAreas(T.timestamp, T.area_id, dt, areaPalette);
plotByBs(T.timestamp, T.rsrp, T.serving_bs, allBsIds, bsNames, colors);
markTransitions(transTimes, transColors);
xlabel('Time (s)');
ylabel('RSRP (dBm)');

yyaxis right;
plot(t_dist, d_dist, 'r-', 'LineWidth', 1.2, 'HandleVisibility', 'off');
ylabel('Distance (m)');
ax1.YColor = 'r';
title('RSRP vs Time');
xlim(timeLim);
grid on;

% 3) RSRQ vs time
nexttile(5);
yyaxis left;
ax2 = gca; ax2.YColor = 'k';
shadeAreas(T.timestamp, T.area_id, dt, areaPalette);
plotByBs(T.timestamp, T.rsrq, T.serving_bs, allBsIds, bsNames, colors);
markTransitions(transTimes, transColors);
xlabel('Time (s)');
ylabel('RSRQ (dB)');

yyaxis right;
plot(t_dist, d_dist, 'r-', 'LineWidth', 1.2, 'HandleVisibility', 'off');
ylabel('Distance (m)');
ax2.YColor = 'r';
title('RSRQ vs Time');
xlim(timeLim);
grid on;

% 4) UE position map -- spans all 3 rows on the right, forced square 200x200,
% top-justified within that span now that the legend lives outside the grid
axMap = nexttile(2, [3 1]);
origPos = axMap.Position;
hold on;
% General-area backdrop: one convex hull per area id, precomputed once by
% build_region_map.m from every UE log's points pooled together. Far more
% stable than approximating an area's extent from a single sparse,
% zig-zagging trajectory. Drawn for all areas regardless of whether this
% UE visited them.
areaHandlesMap = plotRegionMap(mapData.regionMap, areaPalette);
plot(T.x, T.y, '-', 'Color', [0.85 0.85 0.85], 'LineWidth', 1, ...
    'HandleVisibility', 'off');   % faint path for context, excluded from legend
bsHandlesMap = plotByBs(T.x, T.y, T.serving_bs, allBsIds, bsNames, colors);

% Handover markers -- same per-event colors/order as the vertical lines and
% bottom-axis diamonds on the time plots; smaller than the start/end markers
hHandover = scatter(nan, nan, 45, [0.3 0.3 0.3], 'd', 'filled', 'MarkerEdgeColor', 'k');
scatter(T.x(transIdx), T.y(transIdx), 45, transColors, 'd', 'filled', ...
    'MarkerEdgeColor', 'k', 'LineWidth', 1, 'HandleVisibility', 'off');

% Start / end of the walk
hStart = scatter(T.x(1), T.y(1), 130, 'g', 'p', 'filled', 'MarkerEdgeColor', 'k', 'LineWidth', 1.2);
hEnd = scatter(T.x(end), T.y(end), 130, 'r', 's', 'filled', 'MarkerEdgeColor', 'k', 'LineWidth', 1.2);
hold off;
xlabel('X (m)');
ylabel('Y (m)');
title('UE Trajectory');
xlim([0 200]);
ylim([0 200]);
grid on;
axis square;

% Top-justify: axis square centers the square in the tile's tall rectangle;
% pin its top edge to the tile's original top edge instead.
squarePos = axMap.Position;
squarePos(2) = origPos(2) + origPos(4) - squarePos(4);
axMap.Position = squarePos;

%% One shared horizontal legend for the whole figure: areas (ascending),
% then BS (ascending), then Distance, Handover, Start, End -- regardless of whether
% this particular UE's trajectory includes all of them.
[legHandles, legLabels] = areaAndBsLegendEntries(areaHandlesMap, bsHandlesMap, bsNames);
legHandles = [legHandles(:); hDist; hHandover; hStart; hEnd];
legLabels  = [legLabels(:); {'Distance to BS'; 'Handover'; 'Start'; 'End'}];
lgd = legend(legHandles, legLabels, 'Orientation', 'horizontal', 'NumColumns', numel(legLabels));
lgd.Layout.Tile = 'south';

%% ------------------------------------------------------------------
function areaHandles = shadeAreas(timestamps, areaIds, dt, areaPalette)
% Shades the background over each contiguous area_id run, using a fixed
% color per area id (from areaPalette, sized by the caller for the whole
% dataset) so a given area always gets the same shade across subplots and
% across different UE logs. Regions are padded by half a sample interval
% so adjacent same-area runs butt up cleanly with no hairline gap. Returns
% a containers.Map area_id -> handle (one representative patch per area);
% all patches are excluded from any automatic legend since the figure's
% shared legend is built explicitly.
boundaryIdx = find(diff(areaIds) ~= 0);
segStarts = [1; boundaryIdx + 1];
segEnds   = [boundaryIdx; numel(areaIds)];

areaHandles = containers.Map('KeyType', 'double', 'ValueType', 'any');
for k = 1:numel(segStarts)
    a  = areaIds(segStarts(k));
    t1 = timestamps(segStarts(k)) - dt / 2;
    t2 = timestamps(segEnds(k)) + dt / 2;

    r = xregion(t1, t2, 'FaceColor', areaPalette(a, :), 'FaceAlpha', 0.15, 'EdgeColor', 'none');
    r.HandleVisibility = 'off';
    if ~isKey(areaHandles, a)
        areaHandles(a) = r;
    end
end
end

function areaHandles = plotRegionMap(regionMap, areaPalette)
% Draws the precomputed convex-hull-per-area backdrop (see
% build_region_map.m), which pools points across every UE log rather than
% approximating each area's extent from just this one trajectory. Returns
% a containers.Map area_id -> patch handle, same convention as shadeAreas.
areaHandles = containers.Map('KeyType', 'double', 'ValueType', 'any');
for i = 1:numel(regionMap)
    a = regionMap(i).area_id;
    h = patch(regionMap(i).hull_x, regionMap(i).hull_y, areaPalette(a, :), ...
        'FaceAlpha', 0.15, 'EdgeColor', areaPalette(a, :), 'LineWidth', 1, ...
        'HandleVisibility', 'off');
    areaHandles(a) = h;
end
end

function [handles, labels] = areaAndBsLegendEntries(areaHandles, bsHandles, bsNames)
% Returns handles/labels with Area entries first (ascending area number),
% then BS entries (ascending BS number), regardless of the order those
% objects were drawn in, so callers can build a consistently sorted legend
% (optionally appending more entries afterward).
areaKeys = sort(cell2mat(keys(areaHandles)));
handles = gobjects(0);
labels = {};
for a = areaKeys
    handles(end + 1) = areaHandles(a); %#ok<AGROW>
    labels{end + 1} = sprintf('Area %d', a); %#ok<AGROW>
end
for i = 1:numel(bsHandles)
    handles(end + 1) = bsHandles(i); %#ok<AGROW>
    labels{end + 1} = bsNames{i}; %#ok<AGROW>
end
end

function markTransitions(transTimes, transColors)
% Dotted vertical line at each handover time, colored to match the
% corresponding marker on the trajectory map, plus a small matching
% diamond sitting on the time axis itself so the two views (time and
% space) can be visually tied together at a glance.
for k = 1:numel(transTimes)
    xline(transTimes(k), ':', 'Color', transColors(k, :), 'LineWidth', 1.5, ...
        'HandleVisibility', 'off');
end
yl = ylim;
scatter(transTimes, repmat(yl(1), size(transTimes)), 45, transColors, 'd', 'filled', ...
    'MarkerEdgeColor', 'k', 'HandleVisibility', 'off');
ylim(yl);   % guard against the new markers nudging the auto-scaled limits
end

function handles = plotByBs(xData, yData, bsCol, bsIds, bsNames, colors)
% Scatter xData vs yData, one series per BS id, colored per BS and
% returning each series' handle so the caller can build a sorted legend,
% without requiring gscatter / any toolbox. bsIds is the full set of BS ids
% to represent (not just the ones present in this data), so a BS absent
% from this particular UE log still gets an (empty but legend-able) series.
% Leaves hold on so callers can layer more annotations on top.
hold on;
handles = gobjects(numel(bsIds), 1);
for i = 1:numel(bsIds)
    mask = bsCol == bsIds(i);
    handles(i) = scatter(xData(mask), yData(mask), 14, colors(i, :), 'filled', ...
        'DisplayName', bsNames{i}, 'HandleVisibility', 'off');
end
end

function colors = bsColorPalette(n)
% Fixed, colorblind-checked categorical color order (blue, orange, aqua,
% yellow, magenta, green, violet, red). Beyond 8 base stations, extra
% colors are drawn from a continuous colormap since the fixed set runs out.
base = [ ...
     42 120 214   % blue
    235 104  52   % orange
     27 175 122   % aqua
    237 161   0   % yellow
    232 123 164   % magenta
      0 131   0   % green
     74  58 167   % violet
    227  73  72   % red
    ] / 255;

if n <= size(base, 1)
    colors = base(1:n, :);
else
    colors = [base; turbo(n - size(base, 1))];
end
end
end