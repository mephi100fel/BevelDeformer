# BevelDeformer

Small Blender playground repo for lattice-based deformation tools.

## Layout

- `assets/Wall_Test.blend` — test scene
- `scripts/Deform.py` — lattice point reset/shift/conditional scale
- `scripts/Latice.py` — create a lattice per selected mesh and add a Lattice modifier
- `addon/` — reserved for turning the scripts into a Blender add-on later

## How to test

1. Open `assets/Wall_Test.blend` in Blender.
2. Go to **Scripting** workspace (or open the Text Editor).
3. Open a script from `scripts/` and press **Run Script**.

Notes:
- These scripts use `bpy`, so they must be run inside Blender.
