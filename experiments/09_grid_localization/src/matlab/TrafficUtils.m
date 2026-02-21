classdef TrafficUtils
% TRAFFICUTILS - Traffic load calculation utilities
%
% Static methods for:
%   - Getting traffic load based on area type and time
%   - Modeling time-of-day traffic patterns
    
    methods (Static)
        
        function load = get_area_load(area_type, timestamp, config)
            % GET_AREA_LOAD Calculate traffic load for an area
            %
            % Input:
            %   area_type - string (e.g., 'shopping_center', 'residential')
            %   timestamp - datetime object
            %   config    - simulation config (contains traffic patterns)
            %
            % Output:
            %   load - traffic load value (0-1 scale)
            
            % Extract hour of day
            hour = timestamp.Hour;
            
            % Define base load patterns (0-1 scale)
            % Peak hours and patterns vary by area type
            switch area_type
                case 'shopping_center'
                    % Peak: 12-20 (noon to evening)
                    if hour >= 12 && hour < 20
                        load = 0.8 + 0.2 * rand();  % High load with variation
                    elseif hour >= 9 && hour < 12
                        load = 0.5 + 0.2 * rand();  % Medium load
                    else
                        load = 0.1 + 0.1 * rand();  % Low load
                    end
                    
                case 'residential'
                    % Peak: 7-9 (morning), 18-22 (evening)
                    if (hour >= 7 && hour < 9) || (hour >= 18 && hour < 22)
                        load = 0.7 + 0.2 * rand();  % High load
                    elseif hour >= 22 || hour < 6
                        load = 0.2 + 0.1 * rand();  % Low load (night)
                    else
                        load = 0.4 + 0.2 * rand();  % Medium load
                    end
                    
                case 'office'
                    % Peak: 9-17 (business hours)
                    if hour >= 9 && hour < 17
                        load = 0.8 + 0.2 * rand();  % High load
                    else
                        load = 0.1 + 0.1 * rand();  % Low load
                    end
                    
                case 'highway'
                    % Peak: 7-9 (morning rush), 17-19 (evening rush)
                    if (hour >= 7 && hour < 9) || (hour >= 17 && hour < 19)
                        load = 0.9 + 0.1 * rand();  % Very high load
                    elseif hour >= 1 && hour < 5
                        load = 0.1 + 0.1 * rand();  % Very low load (night)
                    else
                        load = 0.5 + 0.2 * rand();  % Medium load
                    end
                    
                case 'parking_lot'
                    % Similar to shopping center but less intense
                    if hour >= 10 && hour < 20
                        load = 0.6 + 0.2 * rand();
                    else
                        load = 0.2 + 0.1 * rand();
                    end
                    
                case 'park'
                    % Peak: 10-18 (daytime)
                    if hour >= 10 && hour < 18
                        load = 0.6 + 0.2 * rand();
                    elseif hour >= 20 || hour < 7
                        load = 0.05 + 0.05 * rand();  % Very low at night
                    else
                        load = 0.3 + 0.2 * rand();
                    end
                    
                otherwise
                    % Default uniform load
                    load = 0.5;
            end
        end
        
    end
end
