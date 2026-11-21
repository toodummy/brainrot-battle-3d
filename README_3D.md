# Brainrot Battle 3D (pilot fork)

Separate fork of Brainrot Battle to test real 3D fighters. The original 2D game (toodummy/brainrot-battle) is untouched.

- Play: home screen → **⚔ 3D FIGHT: SHARK vs OMEGA** (quick match, best of 3, SWAP FIGHTERS after the match).
- Models: `models/shark.glb`, `models/boss.glb` (Draco-compressed, rigged, 18 keyframed clips each).
- Viewer / turntable: `viewer.html?m=shark` or `viewer.html?m=boss&spin` (buttons play each clip).

## How it works
- `tools/shark.py`, `tools/boss.py`: headless Blender 4.2 scripts that build each fighter procedurally (metaball sculpt → voxel remesh → smooth, boolean mouth, conforming glasses/belly shells, procedural brain folds), add a humanoid armature with automatic weights, and export GLB.
- `tools/anims.py`: shared animation library (IK-based poses) for idle, walk, walk_back, dash, jab, cross, kick, uppercut, block, hit, launched, knockdown, getup, jump, airkick, airsmash, special, victory. Any humanoid with the same bone names reuses it.
- `three3d.js`: Three.js renderer under the existing 2D effects/HUD canvas. Off-axis camera keeps the fight plane pixel-aligned with the 2D effects while looking down ~9° at the stage. Toon shading + outlines + rim light, shadows, neon floor, arena backdrop. Game states drive an animation state machine with crossfades; attacks are time-synced to the move's startup/active/recovery.

Rebuild a model: `blender -b -P tools/shark.py -- models/shark.glb`
