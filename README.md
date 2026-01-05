# Maya-Style Shape Key System (Blender Addon)
**Author:** Korn Sensei  
**Version:** 1.5  
**Blender Compatibility:** 4.0+

## Overview
This addon brings a **Maya-like Set Driven Key (SDK)** workflow to Blender, designed specifically for rigging and facial animation. It simplifies the process of driving shape keys with bone transforms or object properties, offering a familiar UI for users transitioning from Maya or those who prefer a more direct "Driver/Driven" approach.

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
*   **Driven Object**: Select the mesh and the specific Shape Key you want to drive.
*   **Key Driver**: Creates a driver curve relationship.
    *   Set the Driver to a value (e.g., Jaw Open = 1.0).
    *   Set the Shape Key to a value (e.g., Mouth Open = 1.0).
    *   Click **Key Driver** to insert a point on the curve.

### 2. Shape Editor
A dedicated list view and toolkit for managing shape keys.
*   **Enhanced List**: Displays Shape Key Name, Value, and a "Driver" icon if a driver is present.
*   **Load as Driven**: Quickly load any shape key from the list into the "Driven" slot with a single click.

### 3. Creation Tools
*   **Create New**: Easily create named shape keys.
*   **Combo / Corrective Shapes**: Create a new shape key driven by the interaction of two other shapes (e.g., `MouthUp` * `Smile` = `SmileCorrective`).
*   **In-Between Shapes**: Create corrective shapes that trigger at specific values of a parent shape (e.g., a roadmap for eyelid deformation).

### 4. Smart Mirroring
*   **Mirror Shape & Driver**: The ultimate time-saver.
    *   Takes an existing Shape Key (e.g., `Smile_L`).
    *   Creates the geometric mirror (`Smile_R`).
    *   **Automatically mirrors the Driver**:
        *   Flips Bone targets (`Jaw_L` -> `Jaw_R`).
        *   Supports standard naming conventions: `.L/.R`, `_L/_R`, `.l/.r`, `_l/_r`.
        *   **Topology Mirror**: Option to use topological mirroring for non-symmetrical posed meshes.

### 5. Asymmetry / Split Tools
New workflow for asymmetrical meshes or complex sculpting.
*   **Create Asym Shape**:
    *   Creates a new shape key and **automatically enables X-Mirror and Topology Mirror** on your mesh.
    *   Allows symmetric sculpting on asymmetrical geometry.
*   **Split Active Shape L/R**:
    *   Takes a completed shape key.
    *   Automatically generates Left/Right masks based on the X-axis.
    *   Splits the shape into two separate keys (e.g. `Mouth_L`, `Mouth_R`).

## Usage Workflow
1.  **Select your Mesh**.
2.  Open the **N-Panel (Sidebar)** in the 3D Viewport and find the **Maya Shape Keys** tab.
3.  **Set the Driver**: Select your Armature, pick a bone, and click the Eyedropper.
4.  **Create a Shape**: Type a name in "Create New" and click Create.
5.  ** sculpt your shape**.
6.  **Key it**:
    *   Move the bone to the activation point.
    *   Dial up the shape key.
    *   Click **Key Driver**.
7.  **Mirror**: Click **Mirror Shape & Driver** to instantly create the opposite side setup.

## Workflow: Asymmetrical Character
1.  Click **Create Asym Shape**.
2.  Sculpt your expression (e.g. a Smile) on BOTH sides at once (thanks to auto-topology mirror).
3.  When finished, click **Split Active Shape L/R**.
4.  The addon creates `AsymShape_L` and `AsymShape_R` for you.
5.  Set Drivers for these new split shapes as usual.
