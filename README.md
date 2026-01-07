# Maya-Style Shape Key System (v2.3)

Enhanced Shape Key system for Blender 4.0+. This addon replicates the powerful "Set Driven Key" workflow from Maya, allowing you to drive Shape Keys or Bone Poses using Driver Bones with ease.

## Features

- **Set Driven Keys (Maya Style)**: Select Driver Bone -> Select Driven Object/Bone -> "Key Driver". It automatically sets up the driver, variables, and curves.
- **Pose Drivers (Action Constraints)**: Drive entire bone poses (Location, Rotation, Scale) using Action Constraints.
- **Action Stacking & Naming**:
    - **Stack Actions**: Apply multiple drivers to a single bone.
    - **Naming**: Give custom names to your actions (e.g., "JawOpen", "HeadTilt") to keep organized.
    - **Stack List Panel**: See all active SDK actions on a bone, remove used ones, or select all bones using a specific action.
- **Mirroring**:
    - **Mirror Drivers**: Instantly mirror setups from Left to Right (e.g., EyePuff.L -> EyePuff.R).
    - **Mirror Shapes**: Create asymmetrical shape keys and mirror them.
- **Visual HUD**:
    - **Viewport Overlay**: Shows which bone is the active Driver and what it is driving.
    - **Customizable**: Adjust Font Size, Line Width, and Colors in the "HUD Settings" panel (Gear icon).
- **Shape Key Tools**:
    - **Combo Shapes**: Easily create corrective shapes (e.g., "Smile + Blink").
    - **In-Between Shapes**: Create breakdown shapes at specific values.
    - **Split Shapes**: Split a shape key into Left/Right halves (vertex group based).

## Installation

1. Download the `maya_shape_keys.zip` file.
2. In Blender, go to **Edit > Preferences > Add-ons**.
3. Click **Install...** and select the zip file.
4. Enable the add-on by checking the box.

## Tutorial / How-To

### 1. Basic Shape Key Driving
1. Go to **Pose Mode**. Select your **Driver Bone** (e.g., a controller).
2. Shift-Select your **Mesh** (the one with shape keys).
3. In the Sidebar (N-Panel) > **Maya Shape Keys**:
    - Click **Load Driver** (if not auto-loaded).
    - Checks "Shape Key" mode.
    - Select the **Shape Key** you want to drive from the dropdown.
    - Move your bone to the "Active" position.
    - Set the **Value** slider to 1.0 (or desired value).
    - Click **Key Driver**.
    - Result: Moving the bone now drives the shape key!

### 2. Driving Bone Poses (Action Constraints)
1. Select your **Driver Bone**.
2. Shift-Select the **Armature** you want to drive (can be the same armature).
3. Switch the panel fast-toggle to **Pose** mode.
4. Select the **Driven Bone(s)** (the bones that should move).
5. **Action Name** (Optional): Type a name like "LegBend" to label this setup.
6. Enable channels: **Loc**, **Rot**, or **Scale**.
7. Move the Driver Bone to the trigger position.
8. Pose the Driven Bones to their target state.
9. Click **Key Driver**.
10. **Result**: The driver bone now controls that pose!

### 3. Managing Stacked Actions
If you apply multiple pose drivers to a bone, they stack up.
- Look at the **"Active SDK Stack"** list in the panel.
- You will see items like `JawOpen`, `Smile`, etc.
- **Remove**: Click the **X** button to remove just that specific link.
- **Select**: Click the **Cursor Icon** to select ALL bones that share that action name.

### 4. Mirroring
1. Select the bones you already set up (Left side).
2. Click **Mirror**.
3. The addon attempts to find the symmetrical bone (L -> R) and automatically mirrors the Action Constraint and Driver logic.

### 5. HUD Customization
1. Click the small **Gear Icon** in the panel header.
2. Use the **HUD Settings** popover to adjust:
   - **Font Size**: Make text readable.
   - **Line Width**: Make the highlight lines thicker/thinner.
   - **Colors**: Change the driver/driven highlight colors.

---
**Created by Korn Sensei**
