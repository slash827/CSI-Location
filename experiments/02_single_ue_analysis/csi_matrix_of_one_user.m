%% Minimal QuaDRiGa: 1 BS, 1 UE, snapshot + subcarrier CSI (with replot helpers)
clear; clc;

% ---------- Simulation parameters ----------
s = qd_simulation_parameters;
s.center_frequency    = 3.5e9;  % 5G mid-band
s.sample_density      = 2;
s.use_absolute_delays = 1;      % helpful for frequency response

% ---------- Layout ----------
l = qd_layout(s);
l.tx_position = [0; 0; 25];
l.tx_array    = qd_arrayant('omni');

l.rx_position = [200; 60; 1.5];  % moved & offset to increase multipath richness
l.rx_array    = qd_arrayant('omni');

% Scenario: pick NLOS for more frequency selectivity
l.set_scenario('3GPP_38.901_UMa_LOS');

% ---------- Channel: taps (time-domain) ----------
c = l.get_channels;                % qd_channel object
H_taps = c.coeff;                  % [Nrx x Ntx x Ntaps x Nsnap]
taus_s = c.delay;                  % [1 x Ntaps x Nsnap] seconds

% One link (SISO)
h_t  = squeeze(H_taps(1,1,:,1));   % [Ntaps x 1]
tau  = squeeze(aus_s_to_col(taus_s)); % [Ntaps x 1] helper makes column

% ---------- Figure 1: impulse response ----------
figImpulse = plot_impulse(h_t);  % returns figure handle

% ---------- Frequency response across subcarriers (OFDM-like) ----------
BW   = 100e6;                     % wider BW for clearer selectivity
Nsc  = 1024;
f_axis = linspace(-BW/2, BW/2, Nsc);   % baseband subcarrier freqs [Hz]

H_sc = zeros(1,1,Nsc);
for k = 1:Nsc
    % H(f) = sum_l  h_l * exp(-j*2*pi*f_k*tau_l)
    H_sc(1,1,k) = sum( h_t .* exp(-1j*2*pi*f_axis(k).*tau) );
end

Hmag = squeeze(abs(H_sc));        % [Nsc x 1] linear magnitude
HdB  = 20*log10(Hmag + eps);      % [Nsc x 1] dB

% ---------- Figures 2–3: CSI (linear + dB) ----------
figCSI_lin = plot_csi_linear(Hmag, Nsc);
figCSI_dB  = plot_csi_dB(HdB, Nsc);

% ---------- Quick delay-spread → coherence bandwidth ----------
P = abs(h_t).^2 / (sum(abs(h_t).^2) + eps);
tau_bar = sum(P.*tau);
tau_rms = sqrt( sum(P.*(tau - tau_bar).^2) );
fprintf('RMS delay spread ≈ %.2f ns\n', tau_rms*1e9);
fprintf('Coherence BW ~ 1/(5*sigma_tau) ≈ %.1f MHz\n', 1/(5*tau_rms)/1e6);

% Example subcarrier
k0 = round(Nsc/2);
fprintf('Example H at k=%d: %.4g + %.4gi, |H|=%.3g (%.1f dB)\n', ...
        k0, real(H_sc(1,1,k0)), imag(H_sc(1,1,k0)), Hmag(k0), HdB(k0));
fprintf('_______________________________________________________________\n');

% 1) Create the metrics object (tune knobs as you like)
m = CSIMetrics( ...
      'SubcarrierSpacing', 100e6/1024, ...  % or your SCS (Hz). If BW=100MHz & Nsc=1024
      'TxPowerPerSC_dBm',  0, ...
      'NoiseFigure_dB',    7, ...
      'InterfPerSC_dBm',  -Inf, ...
      'MIMOCombine',      'sumPow', ...
      'RBSizeSC',          12);

% 2) Compute metrics from your CSI
out = m.compute(H_sc);   % H_sc is [1,1,Nsc], OK

% 3) Inspect
disp(out.RSS_dBm_wb);     % wideband RSS (dBm)
disp(out.SINR_dB_wb);     % wideband SINR (dB)
disp(out.CQI_wb);         % wideband CQI (0..15)

% Per-subcarrier
figure; plot(out.SINR_dB_sc); grid on; title('SINR per subcarrier [dB]');
figure; stairs(out.CQI_sc); grid on; title('CQI per subcarrier (0..15)');

% to see all the csi values: 'H_sc' in the command window
% to see all the csi values as vector: 'squeeze(H_sc)' in the command window
% to see only the magnitude: 'disp(abs(squeeze(H_sc)))'
% to see only the phase (angle in radiant): 'disp(angle(squeeze(H_sc)))'

% ======================================================================
% ========== STORE RE-PLOT HELPERS IN WORKSPACE ========================
% Everything you need to redraw later, without saving files to disk.
%   Plots.Impulse.replot()
%   Plots.CSI.linear.replot()
%   Plots.CSI.dB.replot()
% ======================================================================
Plots = struct();

% Keep raw data you might need
Plots.Data.h_t   = h_t;
Plots.Data.tau   = tau;
Plots.Data.H_sc  = H_sc;
Plots.Data.Hmag  = Hmag;
Plots.Data.HdB   = HdB;
Plots.Data.f_axis = f_axis;
Plots.Data.Nsc    = Nsc;

Plots.Handles.figImpulse = figImpulse;
Plots.Handles.figCSI_lin = figCSI_lin;
Plots.Handles.figCSI_dB  = figCSI_dB;

Plots.Impulse.replot      = @() plot_impulse(Plots.Data.h_t);
Plots.CSI.linear.replot   = @() plot_csi_linear(Plots.Data.Hmag, Plots.Data.Nsc);
Plots.CSI.dB.replot       = @() plot_csi_dB(Plots.Data.HdB, Plots.Data.Nsc);

Plots.showAll = @() show_all_plots(Plots);

assignin('base','Plots',Plots); 

% ======================= Local helper functions ========================
function f = plot_impulse(h)
    f = figure('Name','Impulse Response');
    stem(abs(h),'filled'); grid on
    xlabel('Tap index'); ylabel('|h|'); title('Channel Impulse Response');
end

function f = plot_csi_linear(Hmag, Nsc)
    f = figure('Name','|H(f)| linear (zoomed)');
    plot(1:Nsc, Hmag, 'LineWidth',1.5), grid on
    xlabel('Subcarrier index'), ylabel('|H(f)|')
    title('|H(f)| (linear, zoomed)')
    ylim([0, max(Hmag)*1.1 + eps]);
end

function f = plot_csi_dB(HdB, Nsc)
    f = figure('Name','|H(f)| in dB');
    plot(1:Nsc, HdB, 'LineWidth',1.5), grid on
    xlabel('Subcarrier index'); ylabel('|H(f)| [dB]');
    title('|H(f)| across subcarriers (dB)');
end

function col = aus_s_to_col(taus_s)
    % helper: turn [1 x Ntaps x 1] into [Ntaps x 1] column
    col = squeeze(taus_s(1,:,1)).';
end

function show_all_plots(Plots)
    Plots.Impulse.replot();
    Plots.CSI.linear.replot();
    Plots.CSI.dB.replot();
end