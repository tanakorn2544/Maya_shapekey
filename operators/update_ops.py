import bpy
import urllib.request
import urllib.error
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
            # Create SSL context
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # 1. Try LATEST RELEASE endpoint
            req = urllib.request.Request(GITHUB_API_URL)
            req.add_header('User-Agent', 'Blender-Addon-Updater')
            
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        tag_name = data.get("tag_name", "v0.0")
                        download_url = data.get("zipball_url", "")
                        
                        self._apply_update_info(context, tag_name, download_url)
                        return {'FINISHED'}
                        
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print("[MayaShapeKeys] Releases/Latest not found (404). Falling back to Tags...")
                    # 2. Key error on 'latest', so try TAGS endpoint
                    TAGS_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/tags"
                    
                    req_tags = urllib.request.Request(TAGS_URL)
                    req_tags.add_header('User-Agent', 'Blender-Addon-Updater')
                    
                    with urllib.request.urlopen(req_tags, context=ctx, timeout=10) as response_tags:
                        if response_tags.status == 200:
                             data_tags = json.loads(response_tags.read().decode())
                             if data_tags and isinstance(data_tags, list):
                                 latest = data_tags[0]
                                 tag_name = latest.get("name", "v0.0")
                                 download_url = latest.get("zipball_url", "")
                                 
                                 self._apply_update_info(context, tag_name, download_url)
                                 self.report({'INFO'}, f"Found Tag: {tag_name}")
                                 self.report({'INFO'}, f"Found Tag: {tag_name}")
                                 return {'FINISHED'}
                             else:
                                 print(f"[MayaShapeKeys] Tags response is empty or invalid: {data_tags}")
                                 self.report({'WARNING'}, "GitHub found no tags/releases.")
                        else:
                             print(f"[MayaShapeKeys] Tags Endpoint returned status: {response_tags.status}")
                else:
                    raise e
                    
        except Exception as e:
            print(f"[MayaShapeKeys] Update Check Failed: {e}")
            self.report({'ERROR'}, f"Update Check Failed: {e}")
            
        return {'FINISHED'}

    def _apply_update_info(self, context, tag_name, download_url):
        addon_name = __package__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences
        prefs.latest_version_str = tag_name
        prefs.download_url = download_url
        print(f"[MayaShapeKeys] Found Version: {tag_name}, URL: {download_url}")

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
