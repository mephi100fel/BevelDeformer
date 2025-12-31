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

## Troubleshooting

### "File written by newer Blender binary" / read-only state

If Blender opens `assets/Wall_Test.blend` with a warning like "File written by newer Blender binary", it may switch into a read-only state.
In that mode, Python UI class registration can fail with errors like:

- `register_class(...): can't run in readonly state ...`

Fix: open the scene with a Blender version that is the same or newer than the version that saved the file, then run the scripts again.

### Running the correct script version

If your `.blend` contains embedded Text blocks with older script copies, make sure you open and run the files from the `scripts/` folder.
