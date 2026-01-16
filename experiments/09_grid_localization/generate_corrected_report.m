function generate_corrected_report(output_dir, config, static_data, transition_data, results)
    report_file = fullfile(output_dir, 'CORRECTED_SUMMARY_REPORT.md');
    fid = fopen(report_file, 'w');
    
    fprintf(fid, '# Experiment 13E (CORRECTED): Fair Comparison Summary\n\n');
    fprintf(fid, '**Date:** %s\n\n', datestr(now, 'yyyy-mm-dd HH:MM:SS'));
    
    fprintf(fid, '## IMPORTANT: Experimental Design Correction\n\n');
    fprintf(fid, '### Original Mistake\n');
    fprintf(fid, 'The original exp13e compared two **different problems**:\n');
    fprintf(fid, '- Static: 9-class classification (which grid point?)\n');
    fprintf(fid, '- Transition: 24-class classification (which edge?) ← UNFAIR!\n\n');
    
    fprintf(fid, '### Corrected Approach\n');
    fprintf(fid, 'Both methods now solve the **same problem**: predict location (1-9)\n');
    fprintf(fid, '- Method 1 (Static): Use only RSS_current → predict location\n');
    fprintf(fid, '- Method 2 (Transition): Use RSS_current + RSS_previous → predict location\n');
    fprintf(fid, '  - Enforces spatial constraint: can only move between adjacent grid points\n');
    fprintf(fid, '  - Finds best (current, previous) pair that explains both RSS values\n\n');
    
    fprintf(fid, '## Configuration\n\n');
    fprintf(fid, '```\n');
    fprintf(fid, 'Scenario:        %s\n', config.scenario);
    fprintf(fid, 'Grid Size:       %dx%d\n', config.grid_size, config.grid_size);
    fprintf(fid, 'Spacing:         %.1f meters\n', config.spacing);
    fprintf(fid, 'Random Steps:    %d\n', config.n_steps);
    fprintf(fid, 'Classification:  9-class (grid points)\n');
    fprintf(fid, '```\n\n');
    
    fprintf(fid, '## Fair Comparison Results\n\n');
    fprintf(fid, '### Accuracy (Multiple History Lengths)\n\n');
    fprintf(fid, '| Metric | Static | Trans(h=1) | Trans(h=2) | Trans(h=3) | Best Improvement |\n');
    fprintf(fid, '|:-------|:-------|:-----------|:-----------|:-----------|:-----------------|\n');
    fprintf(fid, '| RSS    | %.2f%% | %.2f%%     | %.2f%%     | %.2f%%     | **%+.2f%%** |\n', ...
        results.rss.static_acc, results.rss.transition_acc(1), results.rss.transition_acc(2), ...
        results.rss.transition_acc(3), max(results.rss.transition_acc - results.rss.static_acc));
    fprintf(fid, '| SINR   | %.2f%% | %.2f%%     | %.2f%%     | %.2f%%     | **%+.2f%%** |\n', ...
        results.sinr.static_acc, results.sinr.transition_acc(1), results.sinr.transition_acc(2), ...
        results.sinr.transition_acc(3), max(results.sinr.transition_acc - results.sinr.static_acc));
    fprintf(fid, '| CQI    | %.2f%% | %.2f%%     | %.2f%%     | %.2f%%     | **%+.2f%%** |\n\n', ...
        results.cqi.static_acc, results.cqi.transition_acc(1), results.cqi.transition_acc(2), ...
        results.cqi.transition_acc(3), max(results.cqi.transition_acc - results.cqi.static_acc));
    
    fprintf(fid, '### Mean Absolute Error (grid points)\n\n');
    fprintf(fid, '| Metric | Static | Trans(h=1) | Trans(h=2) | Trans(h=3) | Best Improvement (%%) |\n');
    fprintf(fid, '|:-------|:-------|:-----------|:-----------|:-----------|:---------------------|\n');
    mae_improv_rss = (results.rss.mae_static - results.rss.mae_transition) / results.rss.mae_static * 100;
    fprintf(fid, '| RSS    | %.3f  | %.3f      | %.3f      | %.3f      | **%+.2f%%** |\n', ...
        results.rss.mae_static, results.rss.mae_transition(1), results.rss.mae_transition(2), ...
        results.rss.mae_transition(3), max(mae_improv_rss));
    mae_improv_sinr = (results.sinr.mae_static - results.sinr.mae_transition) / results.sinr.mae_static * 100;
    fprintf(fid, '| SINR   | %.3f  | %.3f      | %.3f      | %.3f      | **%+.2f%%** |\n', ...
        results.sinr.mae_static, results.sinr.mae_transition(1), results.sinr.mae_transition(2), ...
        results.sinr.mae_transition(3), max(mae_improv_sinr));
    mae_improv_cqi = (results.cqi.mae_static - results.cqi.mae_transition) / results.cqi.mae_static * 100;
    fprintf(fid, '| CQI    | %.3f  | %.3f      | %.3f      | %.3f      | **%+.2f%%** |\n\n', ...
        results.cqi.mae_static, results.cqi.mae_transition(1), results.cqi.mae_transition(2), ...
        results.cqi.mae_transition(3), max(mae_improv_cqi));
    
    fprintf(fid, '*Note: h=1 uses last transition, h=2 uses last 2 transitions, h=3 uses last 3 transitions. Lower MAE is better.*\n\n');
    
    fprintf(fid, '## Interpretation\n\n');
    
    best_rss_improvement = max(results.rss.transition_acc - results.rss.static_acc);
    if best_rss_improvement > 1
    best_rss_improvement = max(results.rss.transition_acc - results.rss.static_acc);
    if best_rss_improvement > 1
        fprintf(fid, '### ✅ Transition-Based Approach WINS!\n\n');
        fprintf(fid, 'Adding delta information **improved** localization accuracy by %.2f%%.\n\n', ...
            best_rss_improvement);
        fprintf(fid, '**Why it helps:**\n');
        fprintf(fid, '- Delta provides geometric movement cues\n');
        fprintf(fid, '- Helps disambiguate overlapping RSS regions\n');
        fprintf(fid, '- Variance amplification is compensated by additional information\n\n');
    elseif best_rss_improvement < -1
        fprintf(fid, '### ❌ Static Approach WINS!\n\n');
        fprintf(fid, 'Adding delta information **degraded** localization accuracy by %.2f%%.\n\n', ...
            abs(best_rss_improvement));
        fprintf(fid, '**Why it hurts:**\n');
        fprintf(fid, '- Variance amplification: Var(Δ) ≈ Var(A) + Var(B)\n');
        fprintf(fid, '- Delta noise outweighs geometric benefits\n');
        fprintf(fid, '- RSS alone provides sufficient separability\n\n');
    else
        fprintf(fid, '### ⚖️ Neutral Result\n\n');
        fprintf(fid, 'Delta information has **no significant impact** (%.2f%% change).\n\n', ...
            best_rss_improvement);
        fprintf(fid, '**Interpretation:**\n');
        fprintf(fid, '- Benefits and drawbacks cancel out\n');
        fprintf(fid, '- May depend on specific scenario characteristics\n\n');
    end
    
    % History length analysis
    fprintf(fid, '## History Length Analysis (RSS)\n\n');
    fprintf(fid, 'Performance as history length increases:\n\n');
    fprintf(fid, '| History | Accuracy | MAE | Improvement vs Static |\n');
    fprintf(fid, '|:--------|:---------|:----|:---------------------|\n');
    for h = 1:3
        acc_improv = results.rss.transition_acc(h) - results.rss.static_acc;
        fprintf(fid, '| h=%d     | %.2f%%   | %.3f | %+.2f%% |\n', ...
            h, results.rss.transition_acc(h), results.rss.mae_transition(h), acc_improv);
    end
    fprintf(fid, '\n');
    
    % Check for overfitting
    if results.rss.transition_acc(3) < results.rss.transition_acc(1)
        fprintf(fid, '⚠️ **OVERFITTING DETECTED:** Performance degrades with longer history\n\n');
        fprintf(fid, 'This suggests the model is fitting to training noise when using too much history.\n\n');
    elseif results.rss.transition_acc(3) > results.rss.transition_acc(2) && ...
           results.rss.transition_acc(2) > results.rss.transition_acc(1)
        fprintf(fid, '✓ **IMPROVEMENT:** Longer history consistently helps\n\n');
        fprintf(fid, 'The model benefits from additional movement context.\n\n');
    else
        fprintf(fid, '➡️ **MIXED:** No clear trend with history length\n\n');
        fprintf(fid, 'The optimal history length may depend on specific conditions.\n\n');
    end
    
    fprintf(fid, '---\n\n');
    fprintf(fid, '*Generated by exp13e_corrected_fair_comparison.m*\n');
    
    fclose(fid);
    fprintf('Report generated: %s\n', report_file);
end
