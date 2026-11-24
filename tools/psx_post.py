"""PSX finish for a rendered PNG (no PIL needed; uses bpy image IO + numpy).

  $PY psx_post.py in.png out.png [--native 320x240] [--scale 4] [--bits 5] [--grain 0.025]

Downsamples to the native resolution (box filter), quantizes to N bits/channel
with 4x4 ordered (Bayer) dithering like PS1 15-bit colour, adds light grain,
then upscales with nearest-neighbour.
"""
import argparse, os
import numpy as np
import bpy

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--native", default="320x240"); ap.add_argument("--scale", type=int, default=4)
ap.add_argument("--bits", type=int, default=5); ap.add_argument("--grain", type=float, default=0.025)
a = ap.parse_args()

img = bpy.data.images.load(os.path.abspath(a.src))
w, h = img.size
px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px)
px = px.reshape(h, w, 4)[:, :, :3]

nw, nh = (int(v) for v in a.native.split("x"))
fy, fx = h // nh, w // nw
small = px[:nh * fy, :nw * fx].reshape(nh, fy, nw, fx, 3).mean(axis=(1, 3))

levels = 2 ** a.bits - 1
bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 - 0.5
d = np.tile(bayer, (nh // 4 + 1, nw // 4 + 1))[:nh, :nw, None]
rng = np.random.default_rng(3)
small = small + rng.normal(0, a.grain, small.shape[:2])[:, :, None]
q = np.clip(np.floor(small * levels + 0.5 + d), 0, levels) / levels

big = np.repeat(np.repeat(q, a.scale, axis=0), a.scale, axis=1)
H, W = big.shape[:2]
out = bpy.data.images.new("psx_out", W, H)
out.pixels.foreach_set(np.dstack([big, np.ones((H, W, 1))]).astype(np.float32).ravel())
out.filepath_raw = os.path.abspath(a.dst); out.file_format = "PNG"; out.save()
print("wrote", out.filepath_raw, f"{W}x{H} from native {nw}x{nh}")
