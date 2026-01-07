import bpy

from .driver_ops import (
    BSETUP_OT_LoadDriver,
    BSETUP_OT_UpdateDriverValue,
    BSETUP_OT_SnapDriverToValue,
    BSETUP_OT_LoadDriven,
    BSETUP_OT_AddDriverKey,
    BSETUP_OT_SetChannel,
    BSETUP_OT_MirrorDriver,
)

from .pose_ops import (
    BSETUP_OT_MirrorPoseDriver,
    BSETUP_OT_RemovePoseDriver,
    BSETUP_OT_SelectDrivenBones,
)

from .shape_ops import (
    BSETUP_OT_AddComboShape,
    BSETUP_OT_CreateNamedShape,
    BSETUP_OT_CreateInBetween,
    BSETUP_OT_SplitShape,
    BSETUP_OT_CreateAsymShape,
    BSETUP_OT_MirrorShapeAndDriver,
)

from .update_ops import (
    BSETUP_OT_CheckForUpdates,
    BSETUP_OT_UpdateAddon,
)

classes = (
    BSETUP_OT_LoadDriver,
    BSETUP_OT_UpdateDriverValue,
    BSETUP_OT_SnapDriverToValue,
    BSETUP_OT_LoadDriven,
    BSETUP_OT_AddDriverKey,
    BSETUP_OT_RemovePoseDriver,
    BSETUP_OT_MirrorPoseDriver,
    BSETUP_OT_SelectDrivenBones,
    BSETUP_OT_AddComboShape,
    BSETUP_OT_CreateNamedShape,
    BSETUP_OT_CreateInBetween,
    BSETUP_OT_SetChannel,
    BSETUP_OT_MirrorDriver,
    BSETUP_OT_MirrorShapeAndDriver,
    BSETUP_OT_SplitShape,
    BSETUP_OT_CreateAsymShape,
    BSETUP_OT_CheckForUpdates,
    BSETUP_OT_UpdateAddon,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
