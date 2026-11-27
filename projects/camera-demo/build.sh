#!/bin/bash
# Rebuild a camera-demo scene from scratch (run from anywhere): build.sh [demo|coverage]
# The .blend is deleted first: running a build script on top of a saved build would duplicate the set and cast.
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); S=${1:-demo}
B="$R/projects/camera-demo/$([ "$S" = demo ] && echo scene || echo "$S").blend"
rm -f "$B"
/home/user/blender-shorts/.venv/bin/python "$R/tools/bl.py" run "$R/projects/camera-demo/$S.py" --blend "$B" --save
