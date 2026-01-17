% Quick test to verify interference actually makes RSS != SINR

% Simple channel: unity gain
H = ones(1, 1, 256, 1); % [Nrx, Ntx, Nsc, Ns]

fprintf('=== Testing CSIMetrics with/without interference ===\n\n');

% Test 1: No interference
fprintf('Test 1: No interference (InterfPerSC_dBm = -Inf)\n');
m1 = CSIMetrics('SubcarrierSpacing', 390625, ...
                'TxPowerPerSC_dBm', 0, ...
                'NoiseFigure_dB', 7, ...
                'InterfPerSC_dBm', -Inf);
out1 = m1.compute(H);
fprintf('  RSS_wb:  %.2f dBm\n', out1.RSS_dBm_wb);
fprintf('  SINR_wb: %.2f dB\n', out1.SINR_dB_wb);
fprintf('  Difference: %.2f dB\n\n', out1.RSS_dBm_wb - out1.SINR_dB_wb);

% Test 2: With -90 dBm interference
fprintf('Test 2: With interference (InterfPerSC_dBm = -90)\n');
m2 = CSIMetrics('SubcarrierSpacing', 390625, ...
                'TxPowerPerSC_dBm', 0, ...
                'NoiseFigure_dB', 7, ...
                'InterfPerSC_dBm', -90);
out2 = m2.compute(H);
fprintf('  RSS_wb:  %.2f dBm\n', out2.RSS_dBm_wb);
fprintf('  SINR_wb: %.2f dB\n', out2.SINR_dB_wb);
fprintf('  Difference: %.2f dB\n\n', out2.RSS_dBm_wb - out2.SINR_dB_wb);

fprintf('=== Expected Behavior ===\n');
fprintf('RSS should be IDENTICAL in both tests (interference doesn''t affect it)\n');
fprintf('SINR should DROP in Test 2 (interference degrades quality)\n');
fprintf('Difference should be LARGER in Test 2\n\n');

% Verify
if abs(out1.RSS_dBm_wb - out2.RSS_dBm_wb) < 0.01
    fprintf('✓ RSS is unchanged (as expected)\n');
else
    fprintf('✗ ERROR: RSS changed! This is a bug!\n');
end

if out2.SINR_dB_wb < out1.SINR_dB_wb - 1
    fprintf('✓ SINR dropped with interference (as expected)\n');
else
    fprintf('✗ ERROR: SINR did not drop! Interference may not be working!\n');
end

fprintf('\nConclusion:\n');
if abs(out1.RSS_dBm_wb - out2.RSS_dBm_wb) < 0.01 && out2.SINR_dB_wb < out1.SINR_dB_wb - 1
    fprintf('CSIMetrics interference handling is CORRECT\n');
else
    fprintf('CSIMetrics has a BUG - interference not working properly!\n');
end
