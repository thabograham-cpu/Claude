"""Render an animation frame range: FS=1 FE=100 $PY bl.py run render_range.py --blend scene.blend"""
import os, bpy
sc = bpy.context.scene
sc.frame_start = int(os.environ.get("FS", sc.frame_start))
sc.frame_end = int(os.environ.get("FE", sc.frame_end))
if os.environ.get("OUT"):
    sc.render.filepath = os.environ["OUT"]
sc.render.use_overwrite = False   # resumable: skips frames already on disk
sc.render.use_placeholder = True  # lets parallel workers share one range safely
bpy.ops.render.render(animation=True)
