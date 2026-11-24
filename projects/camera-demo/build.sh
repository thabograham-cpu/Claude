#!/bin/bash
# Rebuild scene.blend for the camera demo (run from anywhere).
set -e
R=$(cd "$(dirname "$0")/../.." && pwd)
rm -f "$R/projects/camera-demo/scene.blend"
/home/user/blender-shorts/.venv/bin/python "$R/tools/bl.py" run "$R/projects/camera-demo/demo.py" --blend "$R/projects/camera-demo/scene.blend" --save
