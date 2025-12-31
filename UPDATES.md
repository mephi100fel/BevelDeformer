# Updates Log

A lightweight running log of changes in this workspace.

## 2025-12-31

- Repo initialized; files organized into `assets/`, `scripts/`, `addon/`.
- Added Blender UI controls to scripts (Scene properties + View3D Sidebar panels + operators).
  - `scripts/Deform.py`: Deform selected lattices with sliders for scale/shift/reset.
  - `scripts/Latice.py`: Create lattice per selected mesh with controls for base resolution, locked axis resolution, and interpolation.
- Added `UPDATES.md` as a lightweight change log (we update it intentionally when making changes).
- Added read-only guard: when Blender is in read-only state, scripts avoid UI registration crashes and print a helpful message.
- Hardened `register()`/`unregister()` against read-only state to avoid crashes even if scripts are executed from embedded .blend Text blocks.
- Improved lattice creation workflow: detects existing per-mesh lattices and asks for confirmation before overwriting.
- Added a quick "Reset Selected Lattices" button to restore selected lattices to a uniform grid.
- Added "Delete Lattice" button to remove lattices for selected objects.
