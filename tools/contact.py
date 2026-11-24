"""Contact sheet: $PY contact.py out.png cols img1.png img2.png ...  (nearest 2x, labelled by order)"""
import sys, os, numpy as np, bpy
out, cols, paths = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
tiles = []
for p in paths:
    im = bpy.data.images.load(os.path.abspath(p)); w, h = im.size
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(h, w, 4)
    a = np.repeat(np.repeat(a, 2, 0), 2, 1); tiles.append(a)
th, tw = tiles[0].shape[:2]; rows = (len(tiles) + cols - 1) // cols; g = 4
sheet = np.ones((rows * (th + g), cols * (tw + g), 4), np.float32) * [0.3, 0.3, 0.3, 1]
for i, t in enumerate(tiles):
    r, c = divmod(i, cols); y = (rows - 1 - r) * (th + g); x = c * (tw + g)
    sheet[y:y + th, x:x + tw] = t[:th, :tw]
H, W = sheet.shape[:2]
img = bpy.data.images.new("sheet", W, H); img.pixels.foreach_set(sheet.astype(np.float32).ravel())
img.filepath_raw = os.path.abspath(out); img.file_format = "PNG"; img.save(); print("wrote", out)
