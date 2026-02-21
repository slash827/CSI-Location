classdef GeometryUtils
% GEOMETRYUTILS - Geometric utility functions for Voronoi-based simulation
%
% Static methods for:
%   - Finding which Voronoi area contains a point
%   - Checking if points are within bounds
%   - Distance calculations
    
    methods (Static)
        
        function area_idx = find_area(point, areas)
            % FIND_AREA Find which Voronoi area contains a point
            %
            % Input:
            %   point - [x, y] coordinate
            %   areas - struct array with .seed field
            %
            % Output:
            %   area_idx - index of closest area (Voronoi cell assignment)
            
            num_areas = length(areas);
            min_dist = inf;
            area_idx = 1;
            
            for i = 1:num_areas
                dist = GeometryUtils.euclidean_distance(point, areas(i).seed);
                if dist < min_dist
                    min_dist = dist;
                    area_idx = i;
                end
            end
        end
        
        
        function in_bounds = check_if_in_bounds(point, bounds)
            % CHECK_IF_IN_BOUNDS Check if a point is within specified bounds
            %
            % Input:
            %   point  - [x, y] coordinate
            %   bounds - [x_min, x_max, y_min, y_max]
            %
            % Output:
            %   in_bounds - boolean, true if point is within bounds
            
            x_min = bounds(1);
            x_max = bounds(2);
            y_min = bounds(3);
            y_max = bounds(4);
            
            in_bounds = (point(1) >= x_min) && (point(1) <= x_max) && ...
                        (point(2) >= y_min) && (point(2) <= y_max);
        end
        
        
        function dist = euclidean_distance(p1, p2)
            % EUCLIDEAN_DISTANCE Compute 2D Euclidean distance
            %
            % Input:
            %   p1 - [x, y] first point
            %   p2 - [x, y] second point
            %
            % Output:
            %   dist - Euclidean distance
            
            dist = sqrt((p1(1) - p2(1))^2 + (p1(2) - p2(2))^2);
        end
        
    end
end
