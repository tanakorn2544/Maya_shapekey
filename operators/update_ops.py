import bpy
import urllib.request
import json
import ssl
import os
import zipfile
import shutil
from bpy.props import StringProperty, BoolProperty

# Repo Details
REPO_OWNER = "tanakorn2544"
REPO_NAME = "Maya_shapekey"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def get_current_version(context):
    # Helper to get version from bl_info (stored in __init__)
    # We can access it via the module if needed, or passes as prop
    # But easiest is often hardcoded or parsed from package
    # For now, we rely on what's passed or stored in preferences
    return context.preferences.addons[__package__.split('.')[0]].preferences.version_info

class BSETUP_OT_CheckForUpdates(bpy.types.Operator):
    """Check for updates from GitHub"""
    bl_idname = "bsetup.check_for_updates"
    bl_label = "Check for Updates"
    bl_description = "Check GitHub for the latest release"
    
    def execute(self, context):
        print(f"[MayaShapeKeys] Checking for updates from {GITHUB_API_URL}...")
        
        try:
            # Create SSL context (sometimes needed for Blender's Python)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(GITHUB_API_URL)
            req.add_header('User-Agent', 'Blender-Addon-Updater')
            
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    # Check if list (from tags) or dict (from release)
                    if isinstance(data, list):
                         if not data:
                             self.report({'WARNING'}, "No tags/releases found.")
                             return {'CANCELLED'}
                         data = data[0] # Take first (latest)
                         tag_name = data.get("name", "v0.0") # Tags use 'name', Releases 'tag_name' usually
                         download_url = data.get("zipball_url", "")
                    else:
                         tag_name = data.get("tag_name", "v0.0")
                         download_url = data.get("zipball_url", "")

                    if not download_url:
                        # Fallback for assets if zipball is empty?
                        pass

                    # Store in Preferences
                    addon_name = __package__.split('.')[0]
                    prefs = context.preferences.addons[addon_name].preferences
                    
                    prefs.latest_version_str = tag_name
                    prefs.download_url = download_url
                    
                    print(f"[MayaShapeKeys] Latest: {tag_name}, URL: {prefs.download_url}")
                    self.report({'INFO'}, f"Latest Version: {tag_name}")
                    return {'FINISHED'}

            # If we reached here without returning, something unexpected happened or non-200
            
        except urllib.error.HTTPError as e:
            if e.code == 404 and "releases/latest" in GITHUB_API_URL:
                 print("[MayaShapeKeys] No 'Latest Release' found. Falling back to Tags...")
                 # Try Tags Endpoint
                 TAGS_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/tags"
                 
                 try:
                     ctx = ssl.create_default_context()
                     ctx.check_hostname = False
                     ctx.verify_mode = ssl.CERT_NONE
                     
                     req = urllib.request.Request(TAGS_URL)
                     req.add_header('User-Agent', 'Blender-Addon-Updater')
                     
                     with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                         if response.status == 200:
                             data = json.loads(response.read().decode())
                             if data and isinstance(data, list):
                                 latest_tag = data[0]
                                 tag_name = latest_tag.get("name", "v0.0")
                                 download_url = latest_tag.get("zipball_url", "")
                                 
                                 addon_name = __package__.split('.')[0]
                                 prefs = context.preferences.addons[addon_name].preferences
                                 prefs.latest_version_str = tag_name
                                 prefs.download_url = download_url
                                 
                                 self.report({'INFO'}, f"Latest Tag: {tag_name}")
                                 return {'FINISHED'}
                         
                 except Exception as e2:
                     print(f"Tags Method Failed: {e2}")
            
            self.report({'ERROR'}, f"Update Check Failed: {e}")
                    
        except Exception as e:
            print(f"[MayaShapeKeys] Update Check Failed: {e}")
            self.report({'ERROR'}, f"Update Check Failed: {e}")
            
        return {'FINISHED'}

class BSETUP_OT_UpdateAddon(bpy.types.Operator):
    """Download and Install the latest version"""
    bl_idname = "bsetup.update_addon"
    bl_label = "Update Now"
    bl_description = "Download and install the latest version. Blender will need restart."
    
    def execute(self, context):
        addon_name = __package__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences
        url = prefs.download_url
        
        if not url:
            self.report({'ERROR'}, "No update URL found. Check for updates first.")
            return {'CANCELLED'}
        
        print(f"[MayaShapeKeys] Downloading update from {url}...")
        
        try:
            # 1. Download Zip
            params = bpy.app.tempdir
            if not params: params = os.path.dirname(__file__) # fallback
            
            zip_path = os.path.join(params, f"{REPO_NAME}_update.zip")
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Blender-Addon-Updater')
            
            with urllib.request.urlopen(req, context=ctx, timeout=30) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                
            # 2. Install (Standard Blender Method)
            # This overwrites the existing folder if named correctly
            bpy.ops.preferences.addon_install(overwrite=True, filepath=zip_path)
            
            # 3. Cleanup
            try: os.remove(zip_path)
            except: pass
            
            self.report({'INFO'}, "Update Installed! Please Restart Blender.")
            
            # Reset Prefs
            prefs.update_available = False
            
        except Exception as e:
            self.report({'ERROR'}, f"Update Failed: {e}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

classes = (
    BSETUP_OT_CheckForUpdates,
    BSETUP_OT_UpdateAddon,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
