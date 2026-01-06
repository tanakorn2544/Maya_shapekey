import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
import traceback

class DrawHUD:
    def __init__(self):
        self.handler = None
        
    def draw_callback_px(self):
        """Draw the HUD in the 3D Viewport"""
        context = bpy.context
        if not context or not context.scene:
            return
            
        props = context.scene.maya_shape_keys
        if not props.show_hud:
            return

        font_id = 0
        
        # Scaling based on system pixel size
        pixel_size = context.preferences.system.pixel_size
        font_size = int(16 * pixel_size) 
        line_height = int(font_size * 1.5)
        padding = int(10 * pixel_size)
        
        # Position: Bottom Left with padding
        x_pos = int(20 * pixel_size)
        y_pos = int(60 * pixel_size)
        
        # Colors
        color_label = (0.2, 0.8, 0.2, 1.0) # Green
        color_text = (0.9, 0.9, 0.9, 1.0) # White
        color_bg = (0.05, 0.05, 0.05, 0.7) # Dark Transparent Background
        
        # Prepare content pairs: (Label, Value, ColorOverride)
        params = []
        
        # Helper for side detection
        def get_side(name):
            if not name: return None
            n = name.lower()
            if n.endswith("_l") or n.endswith(".l") or n.endswith("-l") or "left" in n:
                return 'L'
            if n.endswith("_r") or n.endswith(".r") or n.endswith("-r") or "right" in n:
                return 'R'
            return None
            
        driver_side = None
        driven_side = None
        
        # 1. Header / Driver
        if props.driver_target:
            params.append(("Driver:", props.driver_target.name, None))
            
            # Check Side on Bone
            if props.driver_bone:
                params.append(("  Bone:", props.driver_bone, None))
                driver_side = get_side(props.driver_bone)
            else:
                 driver_side = get_side(props.driver_target.name)
            
            # Shorten path if needed
            path = props.driver_data_path
            if len(path) > 25:
                path = "..." + path[-22:]
            params.append(("  Path:", path, None))
            params.append(("  Val:", f"{props.driver_value:.3f}", None))
        else:
            params.append(("Driver:", "None", None))
            
        params.append(("", "", None)) # Spacer
        
        # 2. Driven
        if props.driven_object:
            params.append(("Driven:", props.driven_object.name, None))
            if props.driven_type == 'KEY':
                params.append(("  Key:", props.driven_key, None))
                driven_side = get_side(props.driven_key)
                
                # Check Value == 1.0
                val_color = None
                if abs(props.driven_value - 1.0) > 0.001:
                    val_color = (1.0, 0.2, 0.2, 1.0) # Red warning
                    
                params.append(("  Val:", f"{props.driven_value:.3f}", val_color))
            else:
                 params.append(("  Type:", "Pose/Bone", None))
        else:
            params.append(("Driven:", "None", None))
            
        # Side Mismatch Check
        if driver_side and driven_side and driver_side != driven_side:
            params.append(("WARNING:", "Side Mismatch!", (1.0, 0.0, 0.0, 1.0)))
            
        params.append(("", "", None))
        params.append(("Interpolation:", props.driver_interpolation, None))
        
        # --- Drawing Logic ---
        blf.size(font_id, font_size)
        
        # Calculate Dimensions for Background
        max_width = 0
        total_height = 0
        
        # Filter empty lines for height calc, but keep them for spacing
        for label, val, _ in params:
            line_w = 0
            if label:
                w, _ = blf.dimensions(font_id, str(label))
                line_w += w
            if val:
                w, _ = blf.dimensions(font_id, str(val))
                line_w += w + (10 * pixel_size) # spacing
                
            if line_w > max_width:
                max_width = line_w
                
            if not label and not val:
                 total_height += line_height / 2
            else:
                 total_height += line_height
                 
        # Draw Background Box
        # List is drawn bottom-to-top.
        # y_pos is the starting BOTTOM y.
        # Top y is y_pos + total_height.
        
        rect_x = x_pos - padding
        rect_y = y_pos - padding
        rect_w = max_width + (padding * 2)
        rect_h = total_height + (padding * 2)
        
        gpu.state.blend_set('ALPHA')
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {
            "pos": (
                (rect_x, rect_y), 
                (rect_x + rect_w, rect_y), 
                (rect_x + rect_w, rect_y + rect_h), 
                (rect_x, rect_y + rect_h)
            )
        }, indices=((0, 1, 2), (2, 3, 0)))
        shader.bind()
        shader.uniform_float("color", color_bg)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

        # Draw Text
        curr_y = y_pos
        
        # We iterate reversed because we built the list Top-to-Bottom, 
        # but we are drawing from bottom-left anchor UPWARDS?
        # WAIT. If I draw at y_pos and increment y, I am drawing UP.
        # So the FIRST item drawn (at bottom) should be the LAST item in the list?
        # NO.
        # If I want:
        #  Line 1 (Top)
        #  Line 2
        #  Line 3 (Bottom)
        
        # If I start at y=60 and go UP, then:
        # y=60: Line 3
        # y=80: Line 2
        # y=100: Line 1
        
        # So yes, I should iterate REVERSED (Last item first).
        
        for label, val, color_override in reversed(params):
            # Draw Label
            blf.position(font_id, x_pos, curr_y, 0)
            
            if label:
                # Use override for label if provided
                if color_override and label.startswith("WARNING"):
                     blf.color(font_id, *color_override)
                else:
                     blf.color(font_id, *color_label)
                blf.draw(font_id, str(label))
                
            # Draw Value (offset)
            if val:
                # Calculate width of label
                if label:
                    width, _ = blf.dimensions(font_id, str(label))
                    val_x = x_pos + width + (10 * pixel_size)
                else:
                    val_x = x_pos
                
                blf.position(font_id, val_x, curr_y, 0)
                
                if color_override:
                    blf.color(font_id, *color_override)
                else:
                    blf.color(font_id, *color_text)
                    
                blf.draw(font_id, str(val))
            
            # Increment Y
            if not label and not val:
                 curr_y += line_height / 2
            else:
                curr_y += line_height

    def add_handler(self):
        if self.handler is None:
            self.handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (), 'WINDOW', 'POST_PIXEL')
            self.tag_redraw()

    def remove_handler(self):
        if self.handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.handler, 'WINDOW')
            self.handler = None
            self.tag_redraw()

    def tag_redraw(self):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

# Global Instance
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
