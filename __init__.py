bl_info = {
    "name": "Maya-Style Shape Key System",
    "author": "Korn Sensei",
    "version": (1, 7),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Maya Shape Keys",
    "description": "Enhanced Shape Key system with Maya-like Set Driven Key functionality",
    "warning": "",
    "doc_url": "",
    "category": "Animation",
}

# Reload handling
if "bpy" in locals():
    import importlib    
    if "properties" in locals():
        importlib.reload(properties)
    if "operators" in locals():
        importlib.reload(operators)
    if "ui" in locals():
        importlib.reload(ui)
    if "hud" in locals():
        # Clean up existing handler before reload to avoid duplicates
        try:
            hud.remove_handler()
        except:
            pass
        importlib.reload(hud)
else:
    from . import properties
    from . import operators
    from . import ui
    from . import hud

import bpy
import bpy.utils.previews
import os

preview_collections = {}

def register():
    properties.register()
    operators.register()
    ui.register()
    
    # Load Icons
    pcoll = bpy.utils.previews.new()
    my_icons_dir = os.path.join(os.path.dirname(__file__), "Icons")
    
    # Load the specific file
    # We map it to a shorter name "MAIN_ICON" for easy access
    try:
        pcoll.load("MAIN_ICON", os.path.join(my_icons_dir, "f30c933f-c41f-4a8b-8848-007cecc58b39.png"), 'IMAGE')
    except Exception as e:
        print(f"BSETUP Warning: Could not load icon: {e}")
        
    preview_collections["main"] = pcoll

def unregister():
    # Remove icons first
    hud.remove_handler()
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    
    ui.unregister()
    operators.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()
