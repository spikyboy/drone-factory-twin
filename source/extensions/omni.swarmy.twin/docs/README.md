# omni.swarmy.twin

Omniverse Kit extension that loads and drives the **Swarmy — North Georgia Plant**
OpenUSD digital twin (layout & process-visualization focus).

## What it does
- Auto-opens `usd/DroneFactory.usd` on startup and frames the review camera.
- Adds a **Swarmy Twin** menu:
  - *Open / Reload Twin*
  - *Toggle Process Animation* — flows the work-in-progress drones along the conveyor spine.
  - *Frame Review Camera*
  - *Print Selected Semantics* — dumps the `semantic:class` + `aif:core:*` metadata of the selected prim to the console.

## Configuration
`exts."omni.swarmy.twin".stage_path` — path to the twin's root USD (relative to
the app file or absolute). Defaults to the repo's `usd/DroneFactory.usd`.

## Requirements
Kit 106.0+ / USD Composer 2024+ with an RTX GPU.
