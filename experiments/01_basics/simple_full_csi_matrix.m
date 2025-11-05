%% Minimal QuaDRiGa Simulation — 1 BS, 1 static UE
clear; clc;

% Step 1: Create simulation settings
s = qd_simulation_parameters;
s.center_frequency = 3.5e9;  % 3.5 GHz = 5G mid-band
s.sample_density = 2;

% Step 2: Create layout
l = qd_layout(s);

% Step 3: Add 1 base station
l.tx_position = [0; 0; 25];    % BS at origin, 25 meters height
l.tx_array = qd_arrayant('omni');  % Simple omni antenna

% Step 4: Add 1 user equipment (UE)
l.rx_position = [50; 0; 1.5];      % UE 50 meters away, height = 1.5m
l.rx_array = qd_arrayant('omni');  % Simple omni UE antenna

% Step 5: Set scenario (Urban Macro, LOS)
l.set_scenario('3GPP_38.901_UMa_LOS');

% Step 6: Generate the channel
c = l.get_channels;

% Step 7: Display CSI
H = c.coeff;  % H is [Rx x Tx x Taps x Snapshots]
fprintf('CSI matrix size: %s\n', mat2str(size(H)));
disp('Example complex CSI tap values:');
disp(squeeze(H(1,1,:,1)));  % Show tap values of first link

% Optional: Plot impulse response
figure('Name', 'Channel Impulse Response');
stem(1:length(squeeze(H(1,1,:,1))), abs(squeeze(H(1,1,:,1))));
xlabel('Tap Index'); ylabel('|h|'); title('Impulse Response');
