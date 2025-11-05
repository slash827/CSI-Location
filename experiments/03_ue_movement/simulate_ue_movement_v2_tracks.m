%% simulate_ue_movement_v2_tracks.m
% One BS, UE moving along a track (time-consistent snapshot sequence if available).
% Adds the three plots:
%   (1) CQI over time
%   (2) Surface view (BS + UE samples)
%   (3) UE trajectory with direction
%
% Falls back to per-step regeneration if track API is unavailable in your build.

clear; clc; close all; rng(7);

%% 0) Core parameters
fc     = 3.5e9;          BW = 100e6; Nsc = 256; SCS_Hz = BW/Nsc;
TxPerSC_dBm = 0;         NF_dB = 7;

T  = 60;                  % number of snapshots
p0 = [ 50; -30; 1.5];
p1 = [260;  90; 1.5];
P  = [linspace(p0(1),p1(1),T);
      linspace(p0(2),p1(2),T);
      linspace(p0(3),p1(3),T)];

%% 1) QuaDRiGa setup
s = qd_simulation_parameters;
s.center_frequency    = fc;
s.sample_density      = 2;
s.use_absolute_delays = 1;

l = qd_layout(s);
l.tx_position = [0;0;25];   l.tx_array = qd_arrayant('omni');
l.rx_array    = qd_arrayant('omni');
l.set_scenario('3GPP_38.901_UMa_LOS');

%% 2) Try to build a RX track (time-consistent channels)
use_track = true;
try
    trk = qd_track;                        % create track object
    trk.name = 'UE1';
    trk.initial_position = P(:,1);         % set starting point
    % Many QuaDRiGa builds support assigning positions directly:
    trk.positions = P;                     % 3xT, meters
    % (If your build lacks .positions, comment the line above and
    %  replace with an API supported by your version.)
    l.rx_track = {trk};                    % attach track to RX #1

    % Generate multi-snapshot channel along the track
    c = l.get_channels;                    % qd_channel (4th dim = snapshots)
    Htaps = c.coeff;                       % [Nr x Nt x Ntaps x T]
    taus  = c.delay;                       % [1 x Ntaps x T]
    assert(size(Htaps,4) == T, 'Snapshot count mismatch; falling back.');
catch ME
    warning('Track-based generation failed (%s). Falling back to easy loop.', ME.message);
    use_track = false;
end

%% 3) Compute metrics over snapshots
CQI_thr_dB = [-Inf,-6.7,-4.7,-2.3,0.2,2.4,4.3,5.9,8.1,10.3,11.7,14.1,16.3,18.7,21.0,22.7];
CQI_wb  = zeros(T,1);  SINR_wb = zeros(T,1);  RSS_wb  = zeros(T,1);
X = P(1,:).'; Y = P(2,:).'; Z = P(3,:).';

fvec = linspace(-BW/2, BW/2, Nsc);

if use_track
    % ----- Time-consistent snapshots from Htaps/taus -----
    for t = 1:T
        h   = squeeze(Htaps(1,1,:,t));         % taps at snapshot t
        tau = squeeze(taus(:,1,t));            % delays (s)

        % taps -> frequency CSI
        Hsc = zeros(1,1,Nsc);
        for k = 1:Nsc
            Hsc(1,1,k) = sum( h .* exp(-1j*2*pi*fvec(k).*tau) );
        end

        [RSS_wb(t), SINR_wb(t), CQI_wb(t)] = local_metrics(Hsc, TxPerSC_dBm, SCS_Hz, NF_dB, CQI_thr_dB);
    end
else
    % ----- Fallback: regenerate each step (easy mode) -----
    for t = 1:T
        l.rx_position = P(:,t);
        c   = l.get_channels;
        h   = squeeze(c.coeff(1,1,:,1));
        tau = squeeze(c.delay(:,1));
        Hsc = zeros(1,1,Nsc);
        for k = 1:Nsc
            Hsc(1,1,k) = sum( h .* exp(-1j*2*pi*fvec(k).*tau) );
        end
        [RSS_wb(t), SINR_wb(t), CQI_wb(t)] = local_metrics(Hsc, TxPerSC_dBm, SCS_Hz, NF_dB, CQI_thr_dB);
    end
end

%% 4) Plots (the three you asked for)

% (1) CQI over time
figure('Name','CQI over time (tracks)');
stairs(1:T, CQI_wb, 'LineWidth',1.6); grid on;
xlabel('Time step'); ylabel('CQI (0..15)');
title('CQI change over time');

% (2) Surface view (BS + UE samples)
figure('Name','Surface view (tracks)');
plot(0,0,'^','MarkerSize',10,'MarkerFaceColor',[0.85 0.1 0.1],'Color',[0.85 0.1 0.1]); hold on;
scatter(X,Y,25,linspace(1,0,T),'filled');
colormap('parula'); c = colorbar; c.Label.String = 'Time (relative)';
legend({'BS (0,0,25)','UE samples'},'Location','best');
xlabel('X [m]'); ylabel('Y [m]'); axis equal; grid on;
title('Surface view: BS and UE sample locations');

% (3) UE trajectory with direction
figure('Name','UE Trajectory (tracks)');
plot(X,Y,'-','LineWidth',1.5); hold on; grid on; axis equal;
plot(X(1),Y(1),'go','MarkerFaceColor','g','DisplayName','Start');
plot(X(end),Y(end),'ro','MarkerFaceColor','r','DisplayName','End');
quiver(X(1:end-1),Y(1:end-1),diff(X),diff(Y),0,'Color',[0 0.3 0.8]); % arrows
plot(0,0,'^','MarkerSize',10,'MarkerFaceColor',[0.85 0.1 0.1],'Color',[0.85 0.1 0.1],'DisplayName','BS');
xlabel('X [m]'); ylabel('Y [m]'); 
legend({'Path','Start','End','Direction','BS'},'Location','best');
title('UE movement on the surface');

%% 5) Tidy table for ML
traj_tbl = table((1:T).', X, Y, Z, RSS_wb, SINR_wb, CQI_wb, ...
    'VariableNames', {'t','x','y','z','RSS_dBm','SINR_dB','CQI'});
assignin('base','traj_tbl_tracks', traj_tbl);
disp(traj_tbl(1:min(10,T),:));

%% ---- local helper ----
function [RSS_dBm_wb, SINR_dB_wb, CQI_wb] = local_metrics(Hsc, TxPerSC_dBm, SCS_Hz, NF_dB, CQI_thr_dB)
    Gk          = abs(squeeze(Hsc)).^2;              % per-SC gain
    Pt_W_sc     = 10^((TxPerSC_dBm-30)/10);
    S_W_sc      = Pt_W_sc .* Gk;
    RSS_dBm_wb  = 10*log10(sum(S_W_sc)+eps) + 30;

    kB = 1.38064852e-23; T_K = 290;
    N_W_sc      = kB*T_K*SCS_Hz * 10^(NF_dB/10);
    SINR_lin_sc = S_W_sc ./ max(N_W_sc,eps);
    SINR_dB_wb  = 10*log10(mean(SINR_lin_sc));

    idx = find(SINR_dB_wb >= CQI_thr_dB, 1, 'last') - 1;
    if isempty(idx), idx = 0; end
    CQI_wb = max(0,min(15,idx));
end
