# Maya-Style Shape Key System (Blender Addon)
**Author:** Korn Sensei  
**Version:** 1.8  
**Blender Compatibility:** 4.0+

## Overview
This addon brings a **Maya-like Set Driven Key (SDK)** workflow to Blender, designed specifically for rigging and facial animation. It simplifies the process of driving shape keys **and bone poses** with other bone transforms or object properties, offering a familiar UI for users transitioning from Maya or those who prefer a more direct "Driver/Driven" approach.

## Installation
1. Download the `maya_shape_keys` folder.
2. Place the folder into your Blender Addons directory:
   - **Windows:** `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\`
   - **Mac/Linux:** `~/.config/blender/<version>/scripts/addons/`
3. Open Blender, go to **Preferences > Add-ons**.
4. Search for "Maya-Style Shape Key System" and enable it.

## Features

### 1. Set Driven Key Panel
The core "Driver/Key" workflow.
*   **Driver Object**: Select the object (and Bone) that controls the animation.
    *   **Quick Assign**: Use the Eyedropper button to instantly load the selected object as the driver.
*   **Quick Channels**: One-click buttons to set the driver path to standard transforms (Location X/Y/Z, Rotation, Scale).
*   **Driven Settings**:
    *   **Driven Object**: Select the mesh or armature to drive.
    *   **Type Toggle**: Switch between **Shape Key** and **Pose** driving.
*   **Key Driver**: Creates a driver curve relationship.
    *   **Shape Key Mode**: Select a shape key and key it at a specific value.
    *   **Pose Mode**: Select **multiple bones** and drive their **Location, Rotation, or Scale** simultaneously.
*   **Interpolation Control**:
    *   Choose between **Linear**, **Smooth (Bezier)**, or **Step (Constant)** interpolation for your driver curves directly from the panel.

### 2. Live Visualization System (HUD)
A powerful new overlay system to visualize your rigging relationships directly in the 3D Viewport.
*   **Toggle**: Click the **"Show HUD"** button at the top of the panel to enable/disable.
*   **Driven Highlight**:
    *   Highlights the **Evaluated Mesh** faces affected by the current shape key.
    *   **Live Updates**: Updates in real-time during Sculpt or Edit mode (optimized with Numpy).
    *   **Smart Side Filtering**: Automatically filters the highlight to Left/Right sides if the shape key name contains `_L`, `_R`, `.L`, `.R`, ensuring clean visualization for mirrored shapes.
    *   **X-Ray Overlay**: Draws cleanly over the mesh without Z-fighting or clipping.
    *   **Ghosting Fix**: Correctly follows the deformed (rigged) mesh, ensuring the highlight sticks to the character.
*   **Driver Highlight**:
    *   Draws a visual line and point on the Driver Bone/Object, making it easy to see what is driving the deformation.
*   **Custom Colors**:
    *   Click the **Gear Icon** in the panel header to open the settings.
    *   Customize both **Driver Color** (Default: Cyan) and **Driven Color** (Default: Orange) to your liking.

### 3. Bone Driving (Pose Mode)
Drive armature bones directly, similar to driving shape keys.
*   **Select Bones**: Select the bones you want to drive in the viewport.
*   **Choose Channels**: Toggle `Loc`, `Rot`, or `Scale` in the UI to determine which attributes to drive.
*   **Batch Keying**: Clicking "Key Driver" applies the driver to all selected bones for the active channels.
*   **Remove Driver**: Select bones and click "Remove" to delete drivers for the active channels.
*   **Mirror Pose Driver**:
    *   Select driven bones on one side (e.g. `Finger.L`).
    *   Click **Mirror** to replicate the driver to the opposite side (`Finger.R`).
    *   **Smart Flipping**: Automatically flips the **Driver Target** too (e.g. if `Ctrl.L` drives `Finger.L`, then `Ctrl.R` will drive `Finger.R`). Supports complex naming (`L_Bone`, `.L`, `Left`, etc.).

### 4. Shape Editor
A dedicated list view and toolkit for managing shape keys.
*   **Enhanced List**: Displays Shape Key Name, Value, and a "Driver" icon if a driver is present.
*   **Load as Driven**: Quickly load any shape key from the list into the "Driven" slot with a single click.

### 5. Creation Tools
*   **Create New**: Easily create named shape keys.
*   **Combo / Corrective Shapes**: Create a new shape key driven by the product of two other shapes (e.g., `MouthUp` * `Smile` = `SmileCorrective`).
*   **In-Between Shapes**: Create corrective shapes that trigger at specific values of a parent shape (e.g., a roadmap for eyelid deformation).

### 6. Smart Mirroring
*   **Mirror Shape & Driver**: The ultimate time-saver.
    *   Takes an existing Shape Key (e.g., `Smile_L`).
    *   Creates the geometric mirror (`Smile_R`).
    *   **Automatically mirrors the Driver**:
        *   Flips Bone targets (`Jaw_L` -> `Jaw_R`).
        *   Supports standard naming conventions: `.L/.R`, `_L/_R`, `L_/R_`, `Left/Right`.
        *   **Topology Mirror**: Option to use topological mirroring for non-symmetrical posed meshes.

### 7. Asymmetry / Split Tools
New workflow for asymmetrical meshes or complex sculpting.
*   **Create Asym Shape**:
    *   **Name Field**: Enter a name to customize your new shape key (default: `AsymShape`).
    *   Creates a new shape key and **automatically enables X-Mirror and Topology Mirror** on your mesh.
    *   Allows symmetric sculpting on asymmetrical geometry.
*   **Split Active Shape L/R**:
    *   Takes a completed shape key.
    *   Automatically generates Left/Right masks based on the X-axis.
    *   Splits the shape into two separate keys (e.g. `Mouth_L`, `Mouth_R`).

## Usage Workflow
1.  **Select your Mesh or Armature**.
2.  Open the **N-Panel (Sidebar)** in the 3D Viewport and find the **Maya Shape Keys** tab.
3.  **Set the Driver**: Select your Armature, pick a bone, and click the Eyedropper.
4.  **Create a Shape** (if Mesh) or **Select Bones** (if Armature).
5.  **Enable HUD**: Click "Show HUD" to visualize the driver and driven areas. Check colors via the Gear icon.
6.  **Key it**:
    *   Move the driver bone to the activation point.
    *   Dial up the shape key OR pose the driven bones.
    *   Click **Key Driver**.
7.  **Mirror**: Click **Mirror** to instantly create the opposite side setup.

## Optimization Notes
This addon utilizes `numpy` (if installed in your Blender environment) for highly accelerated geometry calculations in the HUD. If `numpy` is not available, it safely falls back to standard Python, though highlighting on high-poly meshes (>100k verts) may be slower. The HUD automatically disabled for meshes > 500k vertices to prevent freezing.
