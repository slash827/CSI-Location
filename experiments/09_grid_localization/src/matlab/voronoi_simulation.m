%% Define Voronoi Centers
voronoi_centers = [
    5, 5;      % Center 1: Indoor
    20, 5;     % Center 2: LOS
    5, 20;     % Center 3: NLOS
    20, 20;    % Center 4: UMi
];

% Scenarios per center
scenarios = {
    'BERLIN_UMa_NLOS',
    '3GPP_38.901_UMa_LOS',
    '3GPP_38.901_UMa_NLOS',
    '3GPP_38.901_UMi_LOS'
};

%% Function: Find nearest center
function cell_idx = find_nearest_center(x, y, centers)
    distances = sqrt((centers(:,1) - x).^2 + (centers(:,2) - y).^2);
    [~, cell_idx] = min(distances);
end

%% Apply to all tracks
for i = 1:l.no_rx
    pos = l.rx_track(i).initial_position;
    cell_idx = find_nearest_center(pos(1), pos(2), voronoi_centers);
    l.rx_track(i).scenario = scenarios{cell_idx};
end

%% Generate
l.set_scenario();
channels = l.init_builder().get_channels();