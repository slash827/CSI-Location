classdef CSIMetrics
% CSIMetrics  Convert frequency-domain CSI to RSS, SINR and CQI.
%
% EXPECTED INPUT (frequency-domain CSI):
%   H : complex array [Nrx, Ntx, Nsc]  OR  [Nrx, Ntx, Nsc, Ns]
%       H(:,:,k[,t]) is the channel matrix at subcarrier k (and snapshot t).
%       - SISO: Nrx=Ntx=1 → H is 1x1xNsc (xNs)
%       - MIMO: arbitrary Nrx, Ntx; class will reduce to a scalar per SC via MIMOCombine.
%
% BASIC USAGE (single snapshot):
%   m = CSIMetrics( ...
%         'SubcarrierSpacing', 30e3, ...     % Hz
%         'TxPowerPerSC_dBm', 0, ...         % dBm per subcarrier
%         'NoiseFigure_dB', 7, ...           % UE NF
%         'InterfPerSC_dBm', -Inf, ...       % flat interference (optional)
%         'MIMOCombine','sumPow', ...        % 'sumPow'|'svd'|'maxEig'
%         'RBSizeSC', 12);                   % SC per RB (NR default)
%   out = m.compute(H);   % H is [Nrx,Ntx,Nsc] or [Nrx,Ntx,Nsc,Ns]
%
%   The returned struct 'out' contains per-subcarrier and wideband metrics:
%     out.RSS_dBm_sc     [Nsc x Ns]    per-subcarrier RSS (dBm)
%     out.RSS_dBm_wb     [1   x Ns]    wideband RSS (dBm; sum of SC in linear W)
%     out.SINR_dB_sc     [Nsc x Ns]    per-subcarrier SINR (dB)
%     out.SINR_dB_wb     [1   x Ns]    wideband SINR (dB; average in linear domain)
%     out.CQI_sc         [Nsc x Ns]    per-subcarrier CQI (0..15)
%     out.CQI_RB         [NRB x Ns]    per-RB CQI (median over RB)
%     out.CQI_wb         [1   x Ns]    wideband CQI
%     out.meta           struct        copied knobs (SCS, NF, etc.)
%
% NOTES
% - This class assumes you already have frequency-domain CSI. If you have
%   time-domain taps, do FFT outside and feed the result here.
% - CQI thresholds are a pragmatic NR-like set (good for prototyping).
%   Replace 'CQIThresholds_dB' if you later calibrate to your MCS/BLER.
%
% AUTHOR: your project helper :)

properties
    % Radio/numerology
    SubcarrierSpacing   (1,1) double = 30e3;    % Hz
    TxPowerPerSC_dBm    (1,1) double = 0;       % dBm per subcarrier (0 dBm = 1 mW per SC)
    NoiseFigure_dB      (1,1) double = 7;       % UE noise figure
    Temperature_K       (1,1) double = 290;     % Thermal noise temperature

    % Interference (can be scalar flat across SC; or provide vector per SC in compute)
    InterfPerSC_dBm     (1,1) double = -Inf;    % dBm per SC; -Inf => none

    % MIMO combining policy for reducing H(:,:,k) to a scalar gain
    %  'sumPow' : Frobenius norm^2 (sum of |h_ij|^2)
    %  'svd'    : dominant singular value^2 (best single-stream)
    %  'maxEig' : largest eigenvalue of H*H^H (same as svd^2)
    MIMOCombine         (1,1) string = "sumPow";

    % CQI mapping (NR-like thresholds; CQI=0..15)
    CQIThresholds_dB    (1,16) double = [-Inf, -6.7, -4.7, -2.3, 0.2, 2.4, 4.3, 5.9, ...
                                          8.1, 10.3, 11.7, 14.1, 16.3, 18.7, 21.0, 22.7];

    % Resource-block aggregation
    RBSizeSC            (1,1) double = 12;      % subcarriers per RB (NR default)
end

methods
    function obj = CSIMetrics(varargin)
        % Allow name-value overrides at construction
        for k = 1:2:numel(varargin)
            obj.(varargin{k}) = varargin{k+1};
        end
    end

    function out = compute(obj, H, varargin)
        % COMPUTE  Main entry: from CSI → RSS, SINR, CQI.
        %
        % H : [Nrx,Ntx,Nsc] or [Nrx,Ntx,Nsc,Ns]
        %
        % Optional name-value:
        %   'InterfPerSC_dBmVec' : provide a vector (Nsc x 1) interference per SC (dBm)
        %                          which overrides the scalar InterfPerSC_dBm.
        p = inputParser;
        p.addParameter('InterfPerSC_dBmVec', [], @(x)isnumeric(x));
        p.parse(varargin{:});
        Ik_vec_dBm = p.Results.InterfPerSC_dBmVec;

        [Nrx,Ntx,Nsc,Ns,H4] = obj.normalizeH(H);  %#ok<ASGLU>
        G = obj.subcarrierGain(H4);                 % [Nsc x Ns] linear gain per SC

        % Powers
        Pt_W_sc  = 10.^((obj.TxPowerPerSC_dBm-30)/10);        % W per SC (scalar)
        S_W_sc   = Pt_W_sc .* G;                              % [Nsc x Ns]
        RSS_dBm_sc = 10*log10(S_W_sc + eps) + 30;             % [Nsc x Ns]
        RSS_dBm_wb = 10*log10(sum(S_W_sc,1) + eps) + 30;      % [1 x Ns]

        % Noise per SC: kTB * NF
        kB          = 1.38064852e-23;
        NF_lin      = 10^(obj.NoiseFigure_dB/10);
        N_W_sc      = kB * obj.Temperature_K * obj.SubcarrierSpacing * NF_lin; % scalar (per SC, W)

        % Interference per SC
        if ~isempty(Ik_vec_dBm)
            if numel(Ik_vec_dBm) ~= Nsc, error('InterfPerSC_dBmVec must have length Nsc'); end
            I_W_sc = 10.^((Ik_vec_dBm(:)-30)/10);            % [Nsc x 1]
        elseif isfinite(obj.InterfPerSC_dBm)
            I_W_sc = 10.^((obj.InterfPerSC_dBm-30)/10) * ones(Nsc,1); % flat
        else
            I_W_sc = zeros(Nsc,1);
        end

        % SINR per SC
        Den_W_sc   = N_W_sc + I_W_sc;                         % [Nsc x 1]
        SINR_lin_sc= S_W_sc ./ max(Den_W_sc, eps);            % [Nsc x Ns]
        SINR_dB_sc = 10*log10(SINR_lin_sc + eps);             % [Nsc x Ns]

        % Wideband SINR (average in linear domain)
        SINR_lin_wb= mean(SINR_lin_sc, 1);                    % [1 x Ns]
        SINR_dB_wb = 10*log10(SINR_lin_wb + eps);             % [1 x Ns]

        % CQI per SC (thresholding)
        CQI_sc = obj.sinrToCQI(SINR_dB_sc);                   % [Nsc x Ns]

        % Per-RB CQI (median)
        RB      = obj.RBSizeSC;
        NRB     = ceil(Nsc/RB);
        CQI_RB  = zeros(NRB, Ns);
        for t = 1:Ns
            for r = 1:NRB
                idx = ((r-1)*RB+1):min(r*RB, Nsc);
                CQI_RB(r,t) = median(CQI_sc(idx,t));
            end
        end

        % Wideband CQI from wideband SINR
        CQI_wb = arrayfun(@(x) obj.sinrToCQIscalar(x), SINR_dB_wb);

        % Pack output
        out = struct();
        out.RSS_dBm_sc = RSS_dBm_sc;       % [Nsc x Ns]
        out.RSS_dBm_wb = RSS_dBm_wb;       % [1 x Ns]
        out.SINR_dB_sc = SINR_dB_sc;       % [Nsc x Ns]
        out.SINR_dB_wb = SINR_dB_wb;       % [1 x Ns]
        out.CQI_sc     = CQI_sc;           % [Nsc x Ns]
        out.CQI_RB     = CQI_RB;           % [NRB x Ns]
        out.CQI_wb     = CQI_wb;           % [1 x Ns]

        out.meta = struct( ...
            'SubcarrierSpacing', obj.SubcarrierSpacing, ...
            'TxPowerPerSC_dBm',  obj.TxPowerPerSC_dBm, ...
            'NoiseFigure_dB',    obj.NoiseFigure_dB, ...
            'Temperature_K',     obj.Temperature_K, ...
            'InterfPerSC_dBm',   obj.InterfPerSC_dBm, ...
            'MIMOCombine',       char(obj.MIMOCombine), ...
            'RBSizeSC',          obj.RBSizeSC, ...
            'CQIThresholds_dB',  obj.CQIThresholds_dB );

    end
end

methods (Access=private)
    function [Nrx,Ntx,Nsc,Ns,H4] = normalizeH(~, H)
        % Ensure shape [Nrx,Ntx,Nsc,Ns]
        sz = size(H);
        if numel(sz) < 3, error('H must be at least [Nrx,Ntx,Nsc].'); end
        Nrx = sz(1); Ntx = sz(2); Nsc = sz(3);
        if numel(sz) == 3
            Ns = 1;
            H4 = reshape(H, [Nrx,Ntx,Nsc,1]);
        else
            Ns = prod(sz(4:end));
            H4 = reshape(H, [Nrx,Ntx,Nsc,Ns]);
        end
        H4 = double(H4);
    end

    function G = subcarrierGain(obj, H4)
        % Reduce MIMO H(:,:,k,t) to a scalar gain per SC (and per snapshot).
        [~,~,Nsc,Ns] = size(H4);
        G = zeros(Nsc,Ns);
        for t = 1:Ns
            for k = 1:Nsc
                Hk = H4(:,:,k,t);
                switch lower(obj.MIMOCombine)
                    case 'sumpow'
                        G(k,t) = sum(abs(Hk(:)).^2);          % ||H||_F^2
                    case 'svd'
                        s = svd(Hk,'econ'); G(k,t) = (s(1))^2; % dominant stream
                    case 'maxeig'
                        ev = eig(Hk*Hk'); G(k,t) = max(real(ev));
                    otherwise
                        error('Unknown MIMOCombine "%s".', obj.MIMOCombine);
                end
            end
        end
        % If you prefer explicit "equal power per Tx antenna", uncomment:
        % G = G / size(H4,2);
    end

    function CQI = sinrToCQI(obj, SINR_dB_sc)
        % Vectorized SINR(dB) → CQI(0..15) per SC
        th = obj.CQIThresholds_dB(:).';
        [Nsc,Ns] = size(SINR_dB_sc);
        CQI = zeros(Nsc,Ns);
        for i = 15:-1:0
            CQI(SINR_dB_sc >= th(i+1)) = i;
        end
    end

    function c = sinrToCQIscalar(obj, sinrWB_dB)
        th = obj.CQIThresholds_dB(:).';
        idx = find(sinrWB_dB >= th, 1, 'last') - 1;
        if isempty(idx), idx = 0; end
        c = max(0,min(15,idx));
    end
end
end
