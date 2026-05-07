function config = read_jsonc(filepath)
% READ_JSONC Read JSONC file (JSON with comments) and parse it
% Strips // comments and then uses jsondecode
%
% Input:
%   filepath - Path to .jsonc file
% Output:
%   config - Parsed configuration structure

    % Read entire file
    raw_text = fileread(filepath);
    
    % Split into lines
    lines = splitlines(raw_text);
    
    % Remove // comments and empty lines
    cleaned_lines = {};
    for i = 1:length(lines)
        line = strtrim(lines{i});
        
        % Skip empty lines
        if isempty(line)
            continue;
        end
        
        % Find // comment (but not inside strings)
        % Simple approach: find first // that's not in a string
        comment_pos = strfind(line, '//');
        if ~isempty(comment_pos)
            % Check if it's inside quotes
            in_string = false;
            actual_comment_pos = [];
            for j = 1:length(line)
                if line(j) == '"' && (j == 1 || line(j-1) ~= '\')
                    in_string = ~in_string;
                end
                if j == comment_pos(1) && ~in_string
                    actual_comment_pos = j;
                    break;
                end
            end
            
            if ~isempty(actual_comment_pos)
                % Remove comment part
                line = strtrim(line(1:actual_comment_pos-1));
            end
        end
        
        % Add line if not empty after comment removal
        if ~isempty(line)
            cleaned_lines{end+1} = line; %#ok<AGROW>
        end
    end
    
    % Join back into single string
    json_text = strjoin(cleaned_lines, newline);
    
    % Parse JSON
    config = jsondecode(json_text);
end
