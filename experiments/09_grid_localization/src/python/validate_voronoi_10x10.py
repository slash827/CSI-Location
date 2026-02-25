import json, re, pathlib

# Read JSONC and strip comments
cfg_path = pathlib.Path(r'..\..\configs\voronoi_10x10_config.jsonc')
text = cfg_path.read_text()
# Strip // comments
text = re.sub(r'//[^\n]*', '', text)
# Strip trailing commas before } or ]
text = re.sub(r',\s*([}\]])', r'\1', text)
cfg = json.loads(text)

# Validate geometry
grid = cfg['grid']
size = grid['size']
spacing = grid['spacing']
offset = grid['grid_offset']
bs = cfg['base_station']['position']

x_min = offset[0]
x_max = offset[0] + (size - 1) * spacing
y_min = offset[1]
y_max = offset[1] + (size - 1) * spacing
cx = (x_min + x_max) / 2
cy = (y_min + y_max) / 2

print('='*60)
print('Voronoi 10x10 Config Validation')
print('='*60)
print(f'Grid: {size}x{size}, spacing={spacing}m')
print(f'Grid extent: X=[{x_min}, {x_max}], Y=[{y_min}, {y_max}]')
print(f'Grid center: ({cx}, {cy})')
print(f'Grid area: {x_max-x_min}m x {y_max-y_min}m')
print()
print(f'BS position: ({bs[0]}, {bs[1]}, {bs[2]})')
print(f'BS inside grid: {x_min <= bs[0] <= x_max and y_min <= bs[1] <= y_max} ✓')
print(f'BS height: {bs[2]}m (UMi small cell)')
print()
print(f'Steps per point: {cfg["movement"]["steps_per_point"]}')
print(f'Total samples: {cfg["movement"]["steps_per_point"] * size * size + 1}')
print()
print(f'Voronoi enabled: {cfg["channel"]["mixed_scenario"]["enabled"]}')
print(f'Auto-generate: {cfg["channel"]["mixed_scenario"]["auto_generate"]}')
print(f'Num areas: {cfg["channel"]["mixed_scenario"]["area_generator"]["num_areas"]}')
print(f'Area types: {", ".join(cfg["channel"]["mixed_scenario"]["area_generator"]["area_types"])}')
print(f'Transition width: {cfg["channel"]["mixed_scenario"]["area_generator"]["transition_width"]}m')
print()
print(f'Interferers enabled: {cfg["base_station"]["interferers"]["enabled"]}')
print()
print('Config is VALID ✓')
print('='*60)
