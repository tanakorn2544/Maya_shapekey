import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
import mathutils

# Try importing numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

class DrawHUD:
    def __init__(self):
        self.handler_px = None
        self.handler_view = None
        
        # Cache of INDICES (not coords) of affected triangles
        self.cache_obj = None
        self.cache_key = None
        self.cache_mode = None
        
        # We store indices of the loop triangles that need highlighting
        self.cache_affected_tri_indices = [] # Numpy array or list of ints
        
    def draw_callback_px(self):
        """Draw the HUD in the 3D Viewport (2D Text/Overlay)"""
        context = bpy.context
        if not context or not context.scene:
            return
            
        props = context.scene.maya_shape_keys
        if not props.show_hud:
            return

        font_id = 0
        pixel_size = context.preferences.system.pixel_size
        font_size = int(16 * pixel_size) 
        line_height = int(font_size * 1.5)
        padding = int(10 * pixel_size)
        x_pos = int(20 * pixel_size)
        y_pos = int(60 * pixel_size)
        color_label = (0.2, 0.8, 0.2, 1.0) 
        color_text = (0.9, 0.9, 0.9, 1.0) 
        color_bg = (0.05, 0.05, 0.05, 0.7) 
        
        params = []
        
        def get_side(name):
            if not name: return None
            n = name.lower()
            if n.endswith("_l") or n.endswith(".l") or n.endswith("-l") or "left" in n: return 'L'
            if n.endswith("_r") or n.endswith(".r") or n.endswith("-r") or "right" in n: return 'R'
            return None
            
        driver_side = None
        driven_side = None
        
        if props.driver_target:
            params.append(("Driver:", props.driver_target.name, None))
            if props.driver_bone:
                params.append(("  Bone:", props.driver_bone, None))
                driver_side = get_side(props.driver_bone)
            else:
                 driver_side = get_side(props.driver_target.name)
            path = props.driver_data_path
            if len(path) > 25: path = "..." + path[-22:]
            params.append(("  Path:", path, None))
            params.append(("  Val:", f"{props.driver_value:.3f}", None))
        else:
            params.append(("Driver:", "None", None))
        params.append(("", "", None)) 
        
        if props.driven_object:
            params.append(("Driven:", props.driven_object.name, None))
            if props.driven_type == 'KEY':
                params.append(("  Key:", props.driven_key, None))
                driven_side = get_side(props.driven_key)
                val_color = None
                if abs(props.driven_value - 1.0) > 0.001:
                    val_color = (1.0, 0.2, 0.2, 1.0)
                params.append(("  Val:", f"{props.driven_value:.3f}", val_color))
            else:
                 params.append(("  Type:", "Pose/Bone", None))
        else:
            params.append(("Driven:", "None", None))
            
        if driver_side and driven_side and driver_side != driven_side:
            params.append(("WARNING:", "Side Mismatch!", (1.0, 0.0, 0.0, 1.0)))
        params.append(("", "", None))
        params.append(("Interpolation:", props.driver_interpolation, None))
        
        blf.size(font_id, font_size)
        max_width = 0
        total_height = 0
        for label, val, _ in params:
            line_w = 0
            if label:
                w, _ = blf.dimensions(font_id, str(label))
                line_w += w
            if val:
                w, _ = blf.dimensions(font_id, str(val))
                line_w += w + (10 * pixel_size)
            if line_w > max_width: max_width = line_w
            if not label and not val: total_height += line_height / 2
            else: total_height += line_height
                 
        rect_x = x_pos - padding
        rect_y = y_pos - padding
        rect_w = max_width + (padding * 2)
        rect_h = total_height + (padding * 2)
        
        gpu.state.blend_set('ALPHA')
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {
            "pos": ((rect_x, rect_y), (rect_x + rect_w, rect_y), (rect_x + rect_w, rect_y + rect_h), (rect_x, rect_y + rect_h))
        }, indices=((0, 1, 2), (2, 3, 0)))
        shader.bind()
        shader.uniform_float("color", color_bg)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

        curr_y = y_pos
        for label, val, color_override in reversed(params):
            blf.position(font_id, x_pos, curr_y, 0)
            if label:
                if color_override and label.startswith("WARNING"): blf.color(font_id, *color_override)
                else: blf.color(font_id, *color_label)
                blf.draw(font_id, str(label))
            if val:
                if label:
                    width, _ = blf.dimensions(font_id, str(label))
                    val_x = x_pos + width + (10 * pixel_size)
                else: val_x = x_pos
                blf.position(font_id, val_x, curr_y, 0)
                if color_override: blf.color(font_id, *color_override)
                else: blf.color(font_id, *color_text)
                blf.draw(font_id, str(val))
            if not label and not val: curr_y += line_height / 2
            else: curr_y += line_height

    def draw_callback_view(self):
        """Draw 3D Highlights (Bone, Driven Area)"""
        context = bpy.context
        if not context or not context.scene: return
        props = context.scene.maya_shape_keys
        if not props.show_hud: return
        
        # Prepare Colors
        # Driver: Cyan (default) with 0.8 alpha
        driver_rgb = props.highlight_color_driver if hasattr(props, "highlight_color_driver") else (0.0, 1.0, 1.0)
        driver_color = (driver_rgb[0], driver_rgb[1], driver_rgb[2], 0.8)
        
        # Driven: Orange (default) with 0.4 alpha
        driven_rgb = props.highlight_color_driven if hasattr(props, "highlight_color_driven") else (1.0, 0.5, 0.0)
        driven_color = (driven_rgb[0], driven_rgb[1], driven_rgb[2], 0.4)
        
        # 1. Driver Bone
        if props.driver_target:
            obj = props.driver_target
            if obj.type == 'ARMATURE' and props.driver_bone:
                pb = obj.pose.bones.get(props.driver_bone)
                if pb:
                    p1 = obj.matrix_world @ pb.head
                    p2 = obj.matrix_world @ pb.tail
                    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                    gpu.state.blend_set('ALPHA')
                    gpu.state.line_width_set(3.0)
                    gpu.state.depth_test_set('NONE') 
                    
                    batch = batch_for_shader(shader, 'LINES', {"pos": [p1, p2]})
                    shader.bind()
                    shader.uniform_float("color", driver_color)
                    batch.draw(shader)
                    
                    gpu.state.point_size_set(10)
                    batch_pt = batch_for_shader(shader, 'POINTS', {"pos": [p1]})
                    batch_pt.draw(shader)
                    
                    gpu.state.depth_test_set('LESS')
                    gpu.state.line_width_set(1.0)
                    gpu.state.point_size_set(1.0)
                    gpu.state.blend_set('NONE')
            else:
                loc = obj.matrix_world.translation
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                gpu.state.blend_set('ALPHA')
                gpu.state.depth_test_set('NONE')
                gpu.state.point_size_set(10)
                batch = batch_for_shader(shader, 'POINTS', {"pos": [loc]})
                shader.bind()
                shader.uniform_float("color", driver_color) 
                batch.draw(shader)
                gpu.state.depth_test_set('LESS')
                gpu.state.point_size_set(1.0)
                gpu.state.blend_set('NONE')

        # 2. Driven Shape Key (Evaluated Mesh)
        if props.driven_object and props.driven_type == 'KEY' and props.driven_key:
            obj = props.driven_object
            key_name = props.driven_key
            
            # Check for update needs
            needs_update = False
            if (self.cache_obj != obj or self.cache_key != key_name): needs_update = True
            if self.cache_mode != obj.mode: needs_update = True
            if HAS_NUMPY and obj.mode in {'EDIT', 'SCULPT'}: needs_update = True
            
            if needs_update:
                self.update_cache(obj, key_name, props.driver_target)
            
            # Draw if we have affected triangles
            if len(self.cache_affected_tri_indices) > 0:
                depsgraph = context.evaluated_depsgraph_get()
                eval_obj = obj.evaluated_get(depsgraph)
                eval_mesh = eval_obj.data
                
                if len(eval_mesh.vertices) != len(obj.data.vertices):
                    return 

                world_coords = []
                
                if HAS_NUMPY:
                    count_v = len(eval_mesh.vertices)
                    count_t = len(eval_mesh.loop_triangles)
                    if count_v > 0 and count_t > 0:
                        raw_coords = np.empty(count_v * 3, dtype=np.float32)
                        eval_mesh.vertices.foreach_get("co", raw_coords)
                        all_verts = raw_coords.reshape(-1, 3)
                        
                        tri_indices = np.empty(count_t * 3, dtype=np.int32)
                        eval_mesh.loop_triangles.foreach_get("vertices", tri_indices)
                        tri_indices = tri_indices.reshape(-1, 3)
                        
                        target_tri_indices = tri_indices[self.cache_affected_tri_indices]
                        target_coords = all_verts[target_tri_indices]
                        
                        mw = obj.matrix_world
                        mat = np.array(mw, dtype=np.float32)
                        
                        flat_coords = target_coords.reshape(-1, 3)
                        ones = np.ones((len(flat_coords), 1), dtype=np.float32)
                        coords_4d = np.hstack((flat_coords, ones))
                        world_coords_np = coords_4d @ np.array(mw.transposed())
                        world_coords = world_coords_np[:, :3].tolist()
                else:
                    mw = obj.matrix_world
                    verts = eval_mesh.vertices
                    tris = eval_mesh.loop_triangles
                    for tri_idx in self.cache_affected_tri_indices:
                        if tri_idx < len(tris):
                           t = tris[tri_idx]
                           for v_idx in t.vertices:
                               world_coords.append(mw @ verts[v_idx].co)

                if world_coords:
                    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                    gpu.state.blend_set('ALPHA')
                    
                    gpu.state.depth_test_set('NONE')
                    gpu.state.face_culling_set('BACK')
                    
                    batch = batch_for_shader(shader, 'TRIS', {"pos": world_coords})
                    shader.bind()
                    shader.uniform_float("color", driven_color) 
                    batch.draw(shader)
                    
                    gpu.state.face_culling_set('NONE')
                    gpu.state.blend_set('NONE')
                    gpu.state.depth_test_set('LESS')
                    
        # 3. Driven Pose (Bones)
        if props.driven_object and props.driven_type == 'POSE' and props.driven_object.type == 'ARMATURE':
            obj = props.driven_object
            # Find selected bones (even if object not active, selection state persists)
            # We want to use 'pb.bone.select' which mirrors the edit/pose selection
            
            lines = []
            points = []
            
            if obj.pose and obj.pose.bones:
                for pb in obj.pose.bones:
                    # Check selection: pb.bone.select is reliable for Pose Mode selection
                    if pb.bone.select:
                        p1 = obj.matrix_world @ pb.head
                        p2 = obj.matrix_world @ pb.tail
                        lines.append(p1)
                        lines.append(p2)
                        points.append(p1)
            
            if lines:
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                gpu.state.blend_set('ALPHA')
                gpu.state.line_width_set(3.0)
                gpu.state.depth_test_set('NONE')
                
                batch = batch_for_shader(shader, 'LINES', {"pos": lines})
                shader.bind()
                shader.uniform_float("color", driven_color)
                batch.draw(shader)
                
                gpu.state.point_size_set(10)
                batch_pt = batch_for_shader(shader, 'POINTS', {"pos": points})
                batch_pt.draw(shader)
                
                gpu.state.depth_test_set('LESS')
                gpu.state.line_width_set(1.0)
                gpu.state.point_size_set(1.0)
                gpu.state.blend_set('NONE')

    def update_cache(self, obj, key_name, driver_obj_ref=None):
        self.cache_obj = obj
        self.cache_key = key_name
        self.cache_mode = obj.mode
        self.cache_affected_tri_indices = []
        
        if not obj or obj.type != 'MESH' or not obj.data.shape_keys: return
            
        kb = obj.data.shape_keys.key_blocks
        if key_name not in kb: return
        key_block = kb[key_name]
        basis_block = kb[0] 
        if key_block.relative_key: basis_block = key_block.relative_key
            
        if len(obj.data.vertices) > 500000: return
             
        threshold = 0.00001
        threshold_sq = threshold * threshold
        
        # --- Side Filtering Logic ---
        filter_side = None # None, 'L', 'R'
        name_lower = key_name.lower()
        if name_lower.endswith("_l") or name_lower.endswith(".l") or "_l_" in name_lower or "left" in name_lower:
            filter_side = 'L'
        elif name_lower.endswith("_r") or name_lower.endswith(".r") or "_r_" in name_lower or "right" in name_lower:
            filter_side = 'R'
            
        # Determine polarity
        # Default: X > 0 is Left, X < 0 is Right (Standard Blender Armature)
        # But we verify against Driver Bone if possible
        polarity = 1.0 # Multiplier for X. If 1, +X is Left. If -1, -X is Left.
        
        if driver_obj_ref and driver_obj_ref.type == 'ARMATURE':
            # Try to find a bone that clearly indicates side
            check_bone = None
            if driver_obj_ref.pose.bones:
                for pb in driver_obj_ref.pose.bones:
                    pb_name = pb.name.lower()
                    if pb_name.endswith("_l") or pb_name.endswith(".l"):
                        if pb.head.x < -0.001: polarity = -1.0 
                        else: polarity = 1.0 
                        break
                    if pb_name.endswith("_r") or pb_name.endswith(".r"):
                        if pb.head.x > 0.001: polarity = -1.0 
                        else: polarity = 1.0 
                        break

        # Filter Mask Function
        if HAS_NUMPY:
            count = len(obj.data.vertices)
            basis_arr = np.empty(count * 3, dtype=np.float32)
            key_arr = np.empty(count * 3, dtype=np.float32)
            
            basis_block.data.foreach_get("co", basis_arr)
            key_block.data.foreach_get("co", key_arr)
            
            basis_vec = basis_arr.reshape(-1, 3)
            key_vec = key_arr.reshape(-1, 3)
            
            diff = key_vec - basis_vec
            dist_sq = np.einsum('ij,ij->i', diff, diff) 
            
            # 1. Movement Mask
            moved_mask = dist_sq > threshold_sq
            
            # 2. Side Mask (if needed)
            if filter_side:
                basis_x = basis_vec[:, 0]
                center_tolerance = 0.001
                if filter_side == 'L':
                    if polarity > 0: side_mask = basis_x > -center_tolerance
                    else: side_mask = basis_x < center_tolerance
                else: # 'R'
                    if polarity > 0: side_mask = basis_x < center_tolerance
                    else: side_mask = basis_x > -center_tolerance
                    
                moved_mask = np.logical_and(moved_mask, side_mask)
            
            if not np.any(moved_mask):
                return
                
            try:
                obj.data.calc_loop_triangles()
            except: pass
            
            num_tris = len(obj.data.loop_triangles)
            if num_tris == 0: return

            tri_verts = np.empty(num_tris * 3, dtype=np.int32)
            obj.data.loop_triangles.foreach_get("vertices", tri_verts)
            tri_verts = tri_verts.reshape(-1, 3)
            
            tri_mask = np.any(moved_mask[tri_verts], axis=1)
            self.cache_affected_tri_indices = np.where(tri_mask)[0]
            
        else:
            threshold_sq = threshold * threshold
            moved_indices = set()
            
            check_side = False
            is_positive_left = (polarity > 0)
            target_is_left = (filter_side == 'L')
            
            for i, v in enumerate(key_block.data):
                 b_co = basis_block.data[i].co
                 if (v.co - b_co).length_squared > threshold_sq:
                     # Check Side
                     valid = True
                     if filter_side:
                         bx = b_co.x
                         if target_is_left:
                             if is_positive_left: 
                                 if bx < -0.001: valid = False
                             else:
                                 if bx > 0.001: valid = False
                         else:
                             if is_positive_left:
                                 if bx > 0.001: valid = False
                             else:
                                 if bx < -0.001: valid = False
                     
                     if valid:
                         moved_indices.add(i)
            
            if not moved_indices: return
                
            try: obj.data.calc_loop_triangles()
            except: pass 
            
            affected = []
            for i, tri in enumerate(obj.data.loop_triangles):
                 v0, v1, v2 = tri.vertices
                 if v0 in moved_indices or v1 in moved_indices or v2 in moved_indices:
                     affected.append(i)
            self.cache_affected_tri_indices = affected
        
    def add_handler(self):
        if self.handler_px is None:
            self.handler_px = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (), 'WINDOW', 'POST_PIXEL')
        if self.handler_view is None:
            self.handler_view = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_view, (), 'WINDOW', 'POST_VIEW')
        self.tag_redraw()

    def remove_handler(self):
        if self.handler_px is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.handler_px, 'WINDOW')
            self.handler_px = None
        if self.handler_view is not None:
             bpy.types.SpaceView3D.draw_handler_remove(self.handler_view, 'WINDOW')
             self.handler_view = None
        self.tag_redraw()

    def tag_redraw(self):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

hud_instance = DrawHUD()

def add_handler():
    hud_instance.add_handler()

def remove_handler():
    hud_instance.remove_handler()

def toggle_hud_update(self, context):
    if self.show_hud:
        add_handler()
    else:
        remove_handler()
