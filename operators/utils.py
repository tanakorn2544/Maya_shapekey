import bpy
import re

def flip_name(name):
    """Flip .L/.R, _L/_R, L_, R_, Left, Right naming conventions, preserving suffixes like .001"""
    
    # 1. Complex Patterns (Suffix sensitive)
    # Matches _L or .L followed by end of string or a dot (for .001)
    # Group 1: The separator (. or _)
    # Group 2: The suffix (.001 or empty)
    
    # Check _L / _R
    # Updated: Allow . or _ or end of string as delimiter
    if re.search(r'(_[Ll])($|[\._])', name):
        return re.sub(r'(_[Ll])($|[\._])', lambda m: m.group(1).replace('l', 'r').replace('L', 'R') + m.group(2), name)
    if re.search(r'(_[Rr])($|[\._])', name):
        return re.sub(r'(_[Rr])($|[\._])', lambda m: m.group(1).replace('r', 'l').replace('R', 'L') + m.group(2), name)

    # Check .L / .R
    if re.search(r'(\.[Ll])($|[\._])', name):
        return re.sub(r'(\.[Ll])($|[\._])', lambda m: m.group(1).replace('l', 'r').replace('L', 'R') + m.group(2), name)
    if re.search(r'(\.[Rr])($|[\._])', name):
        return re.sub(r'(\.[Rr])($|[\._])', lambda m: m.group(1).replace('r', 'l').replace('R', 'L') + m.group(2), name)

    # 2. Variable Separators (for middle occurrences)
    # _L_ -> _R_
    if '_L_' in name: return name.replace('_L_', '_R_')
    if '_R_' in name: return name.replace('_R_', '_L_')
    if '_l_' in name: return name.replace('_l_', '_r_')
    if '_r_' in name: return name.replace('_r_', '_l_')
    
    # 3. Prefixes
    if name.startswith('L_'): return 'R_' + name[2:]
    if name.startswith('R_'): return 'L_' + name[2:]
    if name.startswith('L.'): return 'R.' + name[2:]
    if name.startswith('R.'): return 'L.' + name[2:]
    
    # 4. Words
    if "Left" in name: return name.replace("Left", "Right")
    if "Right" in name: return name.replace("Right", "Left")
    if "left" in name: return name.replace("left", "right")
    # if "right" in name: return name.replace("right", "left")

    return None

def copy_driver_to_fcurve(source_fcurve, target_fcurve, invert_values=False):
    """Copy all driver settings and keyframes from source to target fcurve"""
    target_drv = target_fcurve.driver
    source_drv = source_fcurve.driver
    
    target_drv.type = source_drv.type
    target_drv.expression = source_drv.expression
    
    # Copy variables
    for src_var in source_drv.variables:
        new_var = target_drv.variables.new()
        new_var.name = src_var.name
        new_var.type = src_var.type
        
        for i, src_tgt in enumerate(src_var.targets):
            tgt = new_var.targets[i]
            # tgt.id_type is read-only. Setting .id usually sets id_type implicitly.
            tgt.id = src_tgt.id
            
            # 1. Try to flip Identifier (Object)
            if src_tgt.id and hasattr(src_tgt.id, "name"):
                flipped_id_name = flip_name(src_tgt.id.name)
                
                if flipped_id_name:
                    # Check if exists in same collection type
                    # Usually objects
                    if isinstance(src_tgt.id, bpy.types.Object):
                         if flipped_id_name in bpy.data.objects:
                             tgt.id = bpy.data.objects[flipped_id_name]

            
            if src_var.type == 'TRANSFORMS':
                tgt.transform_type = src_tgt.transform_type
                tgt.transform_space = src_tgt.transform_space
                # Flip bone target
                if src_tgt.bone_target:
                    tgt.bone_target = flip_name(src_tgt.bone_target)
                    
                    if not tgt.bone_target:
                        # Fallback: simple replace
                        val = src_tgt.bone_target
                        if ".L" in val: tgt.bone_target = val.replace(".L", ".R")
                        elif ".R" in val: tgt.bone_target = val.replace(".R", ".L")
                        elif "_L" in val: tgt.bone_target = val.replace("_L", "_R")
                        elif "_R" in val: tgt.bone_target = val.replace("_R", "_L")
                        else:
                             tgt.bone_target = src_tgt.bone_target
            else:
                tgt.data_path = src_tgt.data_path
                # Flip Data Path string if it contains stereo naming
                if src_tgt.data_path:
                    # Naive replace for common patterns if flip_name fails on full string
                    # Try flipping segments or full string
                    flipped_path = flip_name(src_tgt.data_path)
                    if flipped_path:
                        tgt.data_path = flipped_path
                    else:
                        # Try manual sub-string replace (safer)
                        # e.g. ["Key.L"] -> ["Key.R"]
                        val = src_tgt.data_path
                        if ".L" in val: tgt.data_path = val.replace(".L", ".R")
                        elif ".R" in val: tgt.data_path = val.replace(".R", ".L")
                        elif "_L" in val: tgt.data_path = val.replace("_L", "_R")
                        elif "_R" in val: tgt.data_path = val.replace("_R", "_L")
                        
                if src_tgt.bone_target:
                    tgt.bone_target = flip_name(src_tgt.bone_target) or src_tgt.bone_target
    
    # Remove modifiers
    for mod in target_fcurve.modifiers:
        target_fcurve.modifiers.remove(mod)
        
    # Copy keyframes
    # Flip X values if inverted (e.g. Rotate Z -> -Rotate Z)
    for kp in source_fcurve.keyframe_points:
        x_val = -kp.co[0] if invert_values else kp.co[0]
        target_fcurve.keyframe_points.insert(x_val, kp.co[1])
        
    # Set interpolation
    for i, kp in enumerate(target_fcurve.keyframe_points):
        if i < len(source_fcurve.keyframe_points):
            kp.interpolation = source_fcurve.keyframe_points[i].interpolation
            
    target_fcurve.update()

def mirror_shape_driver_logic(self, context, driver_obj, driven_obj, source_key_name, target_key_name, invert_values=False):
    """Specific logic for mirroring Shape Key drivers"""
    key_data = driven_obj.data.shape_keys
    if not key_data or not key_data.animation_data:
        return False, "No driver found on current shape key"
        
    source_path = f'key_blocks["{source_key_name}"].value'
    source_fcurve = None
    for fc in key_data.animation_data.drivers:
        if fc.data_path == source_path:
            source_fcurve = fc
            break
            
    if not source_fcurve:
        return False, f"No driver on {source_key_name}"
    
    # Create new driver on target key
    target_path = f'key_blocks["{target_key_name}"].value'
    
    # Remove existing driver if any
    try:
        key_data.driver_remove(target_path)
    except:
        pass
        
    target_fcurve = key_data.driver_add(target_path)
    copy_driver_to_fcurve(source_fcurve, target_fcurve, invert_values)
    
    return True, "Success"
