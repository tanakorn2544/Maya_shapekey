
import re

def flip_name(name):
    # Copy of the function from utils.py
    
    # Check _L / _R
    if re.search(r'(_[Ll])($|[\._])', name):
        return re.sub(r'(_[Ll])($|[\._])', lambda m: m.group(1).replace('l', 'r').replace('L', 'R') + m.group(2), name)
    if re.search(r'(_[Rr])($|[\._])', name):
        return re.sub(r'(_[Rr])($|[\._])', lambda m: m.group(1).replace('r', 'l').replace('R', 'L') + m.group(2), name)

    # Check .L / .R
    if re.search(r'(\.[Ll])($|[\._])', name):
        return re.sub(r'(\.[Ll])($|[\._])', lambda m: m.group(1).replace('l', 'r').replace('L', 'R') + m.group(2), name)
    if re.search(r'(\.[Rr])($|[\._])', name):
        return re.sub(r'(\.[Rr])($|[\._])', lambda m: m.group(1).replace('r', 'l').replace('R', 'L') + m.group(2), name)

    return None

test_names = [
    "index_01_l.001",
    "Bone.L",
    "Bone_L",
    "Leg_L_01",
    "Arm.L.002"
]

for name in test_names:
    flipped = flip_name(name)
    print(f"'{name}' -> '{flipped}'")
