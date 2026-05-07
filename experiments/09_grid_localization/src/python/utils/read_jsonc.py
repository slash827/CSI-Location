"""
Helper to read JSONC files (JSON with comments)
"""
import json
import re


def read_jsonc(filepath):
    """
    Read JSONC file (JSON with comments) and parse it.
    Strips // comments and then uses json.loads
    
    Args:
        filepath: Path to .jsonc file
    
    Returns:
        Parsed configuration dictionary
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Remove single-line comments (// ...)
    # This regex handles comments while preserving // inside strings
    lines = []
    for line in text.split('\n'):
        # Find // that's not inside a string
        in_string = False
        escape_next = False
        comment_pos = None
        
        for i, char in enumerate(line):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
            
            if not in_string and i < len(line) - 1:
                if line[i:i+2] == '//':
                    comment_pos = i
                    break
        
        if comment_pos is not None:
            line = line[:comment_pos].rstrip()
        
        lines.append(line)
    
    # Join back and parse
    cleaned_text = '\n'.join(lines)
    return json.loads(cleaned_text)
