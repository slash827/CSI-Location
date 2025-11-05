classdef ExperimentUtils
    % EXPERIMENTUTILS - Common utilities for all QuaDRiGa experiments
    % Provides reusable functions for channel generation, delay extraction,
    % frequency conversion, and results saving.
    %
    % Usage:
    %   utils = ExperimentUtils();
    %   [H, delays] = utils.generateChannel(params);
    %   H_freq = utils.convertToFrequency(h_t, tau, fvec);
    %   utils.saveResults(fig, experiment_name, report_data);
    
    methods (Static)
        
        %% Channel Generation with robust delay extraction
        function [H_taps, delays_ns, channel_obj, layout_obj] = generateChannel(params)
            % GENERATECHANNEL - Generate QuaDRiGa channel with robust delay handling
            %
            % Input params struct fields:
            %   - center_frequency: Center frequency in Hz (default: 3.5e9)
            %   - sample_density: Sample density (default: 2)
            %   - use_absolute_delays: Boolean (default: 1)
            %   - tx_position: [x; y; z] in meters (default: [0; 0; 25])
            %   - rx_position: [x; y; z] in meters (required)
            %   - scenario: 3GPP scenario string (default: '3GPP_38.901_UMa_LOS')
            %
            % Outputs:
            %   - H_taps: Complex channel taps [Ntaps x 1]
            %   - delays_ns: Delays in nanoseconds [Ntaps x 1]
            %   - channel_obj: QuaDRiGa channel object
            %   - layout_obj: QuaDRiGa layout object
            
            % Default parameters
            if ~isfield(params, 'center_frequency'), params.center_frequency = 3.5e9; end
            if ~isfield(params, 'sample_density'), params.sample_density = 2; end
            if ~isfield(params, 'use_absolute_delays'), params.use_absolute_delays = 1; end
            if ~isfield(params, 'tx_position'), params.tx_position = [0; 0; 25]; end
            if ~isfield(params, 'scenario'), params.scenario = '3GPP_38.901_UMa_LOS'; end
            
            % Create simulation parameters
            s = qd_simulation_parameters;
            s.center_frequency = params.center_frequency;
            s.sample_density = params.sample_density;
            s.use_absolute_delays = params.use_absolute_delays;
            
            % Create layout
            l = qd_layout(s);
            l.tx_position = params.tx_position;
            l.tx_array = qd_arrayant('omni');
            l.rx_position = params.rx_position;
            l.rx_array = qd_arrayant('omni');
            l.set_scenario(params.scenario);
            
            % Generate channel
            c = l.get_channels;
            H_coeff = c.coeff;
            taus = c.delay;
            
            % Extract taps for single link
            H_taps = squeeze(H_coeff(1,1,:,1));
            
            % Robust delay extraction
            if size(taus, 2) == length(H_taps)
                % Case: taus is [Nrx x Ntaps x Nsnap]
                delays_s = squeeze(taus(1,:,1));
            elseif size(taus, 3) == length(H_taps)
                % Case: taus is [Nrx x Ntx x Ntaps x Nsnap]
                delays_s = squeeze(taus(1,1,:,1));
            else
                % Fallback: equal spacing over 1 microsecond
                warning('Cannot match delay dimensions. Using equal spacing.');
                delays_s = linspace(0, 1e-6, length(H_taps));
            end
            
            % Ensure column vectors
            H_taps = H_taps(:);
            delays_s = delays_s(:);
            delays_ns = delays_s * 1e9;  % Convert to nanoseconds
            
            % Return objects if requested
            channel_obj = c;
            layout_obj = l;
        end
        
        %% Convert time-domain taps to frequency-domain CSI
        function H_freq = convertToFrequency(h_t, tau, fvec)
            % CONVERTTOFREQUENCY - Convert time-domain channel to frequency domain
            %
            % Inputs:
            %   - h_t: Time-domain taps [Ntaps x 1]
            %   - tau: Delays in seconds [Ntaps x 1]
            %   - fvec: Frequency vector in Hz [1 x Nsc] or [Nsc x 1]
            %
            % Output:
            %   - H_freq: Frequency-domain CSI [1 x Nsc]
            %
            % Formula: H(f) = Σ h(τ) * exp(-j2πfτ)
            
            % Ensure column vectors
            h_t = h_t(:);
            tau = tau(:);
            fvec = fvec(:)';  % Row vector
            
            Nsc = length(fvec);
            H_freq = zeros(1, Nsc);
            
            for k = 1:Nsc
                H_freq(k) = sum(h_t .* exp(-1j * 2*pi * fvec(k) .* tau));
            end
        end
        
        %% Create timestamped results directory
        function results_dir = createResultsDir(experiment_name)
            % CREATERESULTSDIR - Create timestamped results directory
            %
            % Input:
            %   - experiment_name: String like 'exp01' or 'exp04'
            %
            % Output:
            %   - results_dir: Full path to created directory
            
            timestamp = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
            results_base_dir = fullfile(fileparts(fileparts(mfilename('fullpath'))), 'results');
            results_dir = fullfile(results_base_dir, [experiment_name '_' timestamp]);
            
            if ~exist(results_dir, 'dir')
                mkdir(results_dir);
            end
        end
        
        %% Save figure(s) to results directory
        function saveFigures(fig_handles, filenames, results_dir)
            % SAVEFIGURES - Save one or more figures as PNG and FIG
            %
            % Inputs:
            %   - fig_handles: Single figure handle or cell array of handles
            %   - filenames: Single filename (no extension) or cell array
            %   - results_dir: Directory to save in
            %
            % Example:
            %   saveFigures(fig, 'myplot', results_dir)
            %   saveFigures({fig1, fig2}, {'plot1', 'plot2'}, results_dir)
            
            % Convert to cell arrays if not already
            if ~iscell(fig_handles)
                fig_handles = {fig_handles};
            end
            if ~iscell(filenames)
                filenames = {filenames};
            end
            
            % Save each figure
            for i = 1:length(fig_handles)
                % Get the figure handle
                fig_h = fig_handles{i};
                
                % If numeric handle, validate it
                if isnumeric(fig_h)
                    if ~ishandle(fig_h) || ~strcmp(get(fig_h, 'Type'), 'figure')
                        warning('ExperimentUtils:invalidFigure', 'Invalid figure handle at index %d, using gcf', i);
                        fig_h = gcf;
                    end
                end
                
                % Make figure current
                figure(fig_h);
                
                % Prepare paths
                png_path = fullfile(results_dir, [filenames{i} '.png']);
                fig_path = fullfile(results_dir, [filenames{i} '.fig']);
                
                % Save using the validated handle
                saveas(fig_h, png_path);
                savefig(fig_h, fig_path);
            end
        end
        
        %% Create standard text report header
        function fid = createReportHeader(results_dir, experiment_title)
            % CREATEREPORTHEADER - Create text report with standard header
            %
            % Inputs:
            %   - results_dir: Directory to save report
            %   - experiment_title: Title string
            %
            % Output:
            %   - fid: File identifier for writing
            
            report_path = fullfile(results_dir, 'experiment_report.txt');
            fid = fopen(report_path, 'w');
            
            timestamp = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
            
            fprintf(fid, '========================================\n');
            fprintf(fid, '%s\n', experiment_title);
            fprintf(fid, '========================================\n\n');
            fprintf(fid, 'Execution Time: %s\n\n', timestamp);
        end
        
        %% Write simulation parameters section
        function writeSimParams(fid, params)
            % WRITESIMPARAMS - Write simulation parameters to report
            %
            % Inputs:
            %   - fid: File identifier
            %   - params: Struct with fields like center_frequency, scenario, etc.
            
            fprintf(fid, '--- SIMULATION PARAMETERS ---\n');
            
            if isfield(params, 'center_frequency')
                fprintf(fid, 'Center Frequency: %.2f GHz\n', params.center_frequency/1e9);
            end
            if isfield(params, 'bandwidth')
                fprintf(fid, 'Bandwidth: %.2f MHz\n', params.bandwidth/1e6);
            end
            if isfield(params, 'num_subcarriers')
                fprintf(fid, 'Number of Subcarriers: %d\n', params.num_subcarriers);
                if isfield(params, 'bandwidth')
                    fprintf(fid, 'Subcarrier Spacing: %.2f kHz\n', params.bandwidth/params.num_subcarriers/1e3);
                end
            end
            if isfield(params, 'sample_density')
                fprintf(fid, 'Sample Density: %d\n', params.sample_density);
            end
            if isfield(params, 'scenario')
                fprintf(fid, 'Scenario: %s\n', params.scenario);
            end
            if isfield(params, 'tx_position')
                fprintf(fid, 'BS Position: [%.1f, %.1f, %.1f] m\n', ...
                    params.tx_position(1), params.tx_position(2), params.tx_position(3));
            end
            if isfield(params, 'rx_position')
                fprintf(fid, 'UE Position: [%.1f, %.1f, %.1f] m\n', ...
                    params.rx_position(1), params.rx_position(2), params.rx_position(3));
            end
            if isfield(params, 'tx_position') && isfield(params, 'rx_position')
                dist = norm(params.rx_position - params.tx_position);
                fprintf(fid, 'Distance: %.2f m\n', dist);
            end
            
            fprintf(fid, '\n');
        end
        
        %% Close report with standard footer
        function closeReport(fid, files_generated)
            % CLOSEREPORT - Write files list and close report
            %
            % Inputs:
            %   - fid: File identifier
            %   - files_generated: Cell array of filenames
            
            fprintf(fid, '--- FILES GENERATED ---\n');
            for i = 1:length(files_generated)
                fprintf(fid, '%s\n', files_generated{i});
            end
            fprintf(fid, '\n');
            
            fprintf(fid, '========================================\n');
            fprintf(fid, 'END OF REPORT\n');
            fprintf(fid, '========================================\n');
            
            fclose(fid);
        end
        
        %% Create standard figure with proper sizing
        function fig = createFigure(title_str, layout)
            % CREATEFIGURE - Create figure with standard sizing
            %
            % Inputs:
            %   - title_str: Figure title
            %   - layout: 'square' (0.8x0.8), 'wide' (0.8x0.4), 'tall' (0.5x0.8)
            %
            % Output:
            %   - fig: Figure handle
            
            if nargin < 2
                layout = 'square';
            end
            
            switch layout
                case 'square'
                    position = [0.1 0.1 0.8 0.8];
                case 'wide'
                    position = [0.1 0.1 0.8 0.4];
                case 'tall'
                    position = [0.1 0.1 0.5 0.8];
                otherwise
                    position = [0.1 0.1 0.8 0.8];
            end
            
            fig = figure('Name', title_str, 'Units', 'normalized', 'Position', position);
        end
        
        %% Calculate basic channel statistics
        function stats = calculateChannelStats(H_taps, delays_ns)
            % CALCULATECHANNELSTATS - Calculate common channel statistics
            %
            % Inputs:
            %   - H_taps: Complex channel taps [Ntaps x 1]
            %   - delays_ns: Delays in nanoseconds [Ntaps x 1]
            %
            % Output:
            %   - stats: Struct with fields:
            %       .num_taps, .total_power, .path_loss_dB,
            %       .dominant_tap_idx, .dominant_tap_power,
            %       .mean_delay_ns, .rms_delay_spread_ns
            
            stats = struct();
            
            power_profile = abs(H_taps).^2;
            stats.num_taps = length(H_taps);
            stats.total_power = sum(power_profile);
            stats.path_loss_dB = -10*log10(stats.total_power);
            
            [stats.dominant_tap_power, stats.dominant_tap_idx] = max(power_profile);
            stats.dominant_tap_ratio = stats.dominant_tap_power / stats.total_power;
            
            % Delay spread statistics
            stats.mean_delay_ns = sum(delays_ns .* power_profile) / stats.total_power;
            stats.rms_delay_spread_ns = sqrt(sum((delays_ns - stats.mean_delay_ns).^2 .* power_profile) / stats.total_power);
            stats.delay_range_ns = [min(delays_ns), max(delays_ns)];
        end
        
    end
end
