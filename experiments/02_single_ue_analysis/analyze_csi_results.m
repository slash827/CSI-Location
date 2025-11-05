%% Detailed CSI Analysis Script
% Run this after simple_full_csi_matrix.m to understand your results

%% 1. Extract CSI matrix
H = c.coeff;  % [Rx x Tx x Taps x Snapshots]
fprintf('===== CSI MATRIX STRUCTURE =====\n');
fprintf('Full size: %s\n', mat2str(size(H)));
fprintf('Rx antennas: %d\n', size(H,1));
fprintf('Tx antennas: %d\n', size(H,2));
fprintf('Multipath taps: %d\n', size(H,3));
fprintf('Time snapshots: %d\n\n', size(H,4));

%% 2. Analyze Each Multipath Tap
fprintf('===== MULTIPATH TAP ANALYSIS =====\n');
h_taps = squeeze(H(1,1,:,1));  % Extract all taps for first link
for tap = 1:length(h_taps)
    magnitude = abs(h_taps(tap));
    phase_deg = angle(h_taps(tap)) * 180/pi;
    power_dB = 10*log10(abs(h_taps(tap))^2);
    
    fprintf('Tap %d:\n', tap);
    fprintf('  Complex value: %.6f %+.6fi\n', real(h_taps(tap)), imag(h_taps(tap)));
    fprintf('  Magnitude: %.6f\n', magnitude);
    fprintf('  Phase: %.2f degrees\n', phase_deg);
    fprintf('  Power: %.2f dB\n\n', power_dB);
end

%% 3. Channel Characteristics
fprintf('===== CHANNEL STATISTICS =====\n');
total_power = sum(abs(h_taps).^2);
fprintf('Total channel power: %.6f (%.2f dB)\n', total_power, 10*log10(total_power));

dominant_tap = find(abs(h_taps) == max(abs(h_taps)));
fprintf('Dominant tap index: %d\n', dominant_tap);
fprintf('Dominant tap power: %.2f%% of total\n\n', 100*abs(h_taps(dominant_tap))^2/total_power);

% RMS delay spread
delays = c.delay;  % Delay of each tap in seconds
power_profile = abs(h_taps).^2;
mean_delay = sum(delays .* power_profile) / sum(power_profile);
rms_delay_spread = sqrt(sum((delays - mean_delay).^2 .* power_profile) / sum(power_profile));
fprintf('RMS Delay Spread: %.2f ns\n', rms_delay_spread * 1e9);
fprintf('Coherence Bandwidth (approx): %.2f MHz\n\n', 1/(5*rms_delay_spread) / 1e6);

%% 4. Path Loss and Distance
distance = norm(l.rx_position - l.tx_position);
path_loss_dB = -10*log10(total_power);
fprintf('===== PROPAGATION METRICS =====\n');
fprintf('Distance BS to UE: %.2f meters\n', distance);
fprintf('Path Loss: %.2f dB\n', path_loss_dB);
fprintf('Center Frequency: %.2f GHz\n', s.center_frequency/1e9);
wavelength = 3e8 / s.center_frequency;
fprintf('Wavelength: %.4f meters\n\n', wavelength);

%% 5. Comprehensive Visualization
figure('Name', 'Complete CSI Analysis', 'Position', [100 100 1400 900]);

% Subplot 1: Impulse Response (Magnitude)
subplot(3,3,1);
stem(1:length(h_taps), abs(h_taps), 'LineWidth', 2);
xlabel('Tap Index'); ylabel('|h|'); 
title('Channel Impulse Response (Magnitude)');
grid on;

% Subplot 2: Impulse Response (Power in dB)
subplot(3,3,2);
stem(1:length(h_taps), 10*log10(abs(h_taps).^2), 'LineWidth', 2, 'Color', 'r');
xlabel('Tap Index'); ylabel('Power (dB)'); 
title('Power Delay Profile');
grid on;

% Subplot 3: Phase Response
subplot(3,3,3);
stem(1:length(h_taps), angle(h_taps)*180/pi, 'LineWidth', 2, 'Color', 'g');
xlabel('Tap Index'); ylabel('Phase (degrees)'); 
title('Phase of Each Tap');
grid on;

% Subplot 4: Complex Plane (Constellation)
subplot(3,3,4);
plot(real(h_taps), imag(h_taps), 'bo', 'MarkerSize', 10, 'LineWidth', 2);
hold on;
plot([0 real(h_taps(1))], [0 imag(h_taps(1))], 'r--', 'LineWidth', 1.5);
hold off;
xlabel('Real'); ylabel('Imaginary'); 
title('CSI Taps in Complex Plane');
grid on; axis equal;

% Subplot 5: Delay Profile
subplot(3,3,5);
stem(delays*1e9, abs(h_taps), 'LineWidth', 2, 'Color', 'm');
xlabel('Delay (ns)'); ylabel('|h|'); 
title('Time Delay Profile');
grid on;

% Subplot 6: Cumulative Power
subplot(3,3,6);
cumulative_power = cumsum(abs(h_taps).^2) / total_power * 100;
plot(1:length(h_taps), cumulative_power, 'o-', 'LineWidth', 2);
xlabel('Tap Index'); ylabel('Cumulative Power (%)'); 
title('Cumulative Power Distribution');
grid on; ylim([0 105]);

% Subplot 7: Real and Imaginary Parts
subplot(3,3,7);
bar([real(h_taps), imag(h_taps)]);
xlabel('Tap Index'); ylabel('Value'); 
title('Real vs Imaginary Components');
legend('Real', 'Imaginary');
grid on;

% Subplot 8: Frequency Response
subplot(3,3,8);
freq_samples = 1024;
H_freq = fft(h_taps, freq_samples);
freq_axis = linspace(-s.center_frequency/2, s.center_frequency/2, freq_samples) / 1e6;
plot(freq_axis, 10*log10(abs(fftshift(H_freq)).^2), 'LineWidth', 1.5);
xlabel('Frequency (MHz)'); ylabel('Power (dB)'); 
title('Channel Frequency Response');
grid on;

% Subplot 9: Summary Text
subplot(3,3,9);
axis off;
summary_text = sprintf([...
    'CHANNEL SUMMARY\n\n' ...
    'Scenario: %s\n' ...
    'Frequency: %.2f GHz\n' ...
    'Distance: %.1f m\n' ...
    'Path Loss: %.1f dB\n\n' ...
    'Number of Taps: %d\n' ...
    'Dominant Tap: #%d\n' ...
    'RMS Delay: %.1f ns\n' ...
    'Total Power: %.2f dB\n'], ...
    l.scenario{1}, s.center_frequency/1e9, distance, path_loss_dB, ...
    length(h_taps), dominant_tap, rms_delay_spread*1e9, 10*log10(total_power));
text(0.1, 0.5, summary_text, 'FontSize', 10, 'FontName', 'Courier', ...
    'VerticalAlignment', 'middle');

%% 6. Save Results
results = struct();
results.CSI_matrix = H;
results.distance_m = distance;
results.path_loss_dB = path_loss_dB;
results.rms_delay_spread_ns = rms_delay_spread * 1e9;
results.dominant_tap = dominant_tap;
results.total_power_dB = 10*log10(total_power);
results.scenario = l.scenario{1};
results.frequency_GHz = s.center_frequency / 1e9;

save('csi_analysis_results.mat', 'results');
fprintf('Results saved to: csi_analysis_results.mat\n');