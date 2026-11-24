"""PSX finish for a folder of native-res frames (one bpy process).
  $PY psx_batch.py in_dir out_dir [--scale 4] [--bits 5] [--grain 0.015] [--black-from N]
Frame number is parsed from the filename's trailing digits."""
import argparse, os, re, numpy as np, bpy

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--scale", type=int, default=4); ap.add_argument("--bits", type=int, default=5)
ap.add_argument("--grain", type=float, default=0.015); ap.add_argument("--black-from", type=int)
a = ap.parse_args()
os.makedirs(a.dst, exist_ok=True)
bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 - 0.5
lv = 2 ** a.bits - 1
files = sorted(f for f in os.listdir(a.src) if f.endswith(".png"))
for fn in files:
    num = int(re.findall(r"(\d+)\.png$", fn)[0])
    im = bpy.data.images.load(os.path.join(a.src, fn)); w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); bpy.data.images.remove(im)
    px = px.reshape(h, w, 4)[:, :, :3]
    if a.black_from and num >= a.black_from:
        q = np.zeros_like(px)
    else:
        g = np.random.default_rng(num).normal(0, a.grain, (h, w))[:, :, None]
        d = np.tile(bayer, (h // 4 + 1, w // 4 + 1))[:h, :w, None]
        q = np.clip(np.floor((px + g) * lv + 0.5 + d), 0, lv) / lv
    big = np.repeat(np.repeat(q, a.scale, 0), a.scale, 1); H, W = big.shape[:2]
    out = bpy.data.images.new("o", W, H)
    out.pixels.foreach_set(np.dstack([big, np.ones((H, W, 1))]).astype(np.float32).ravel())
    out.filepath_raw = os.path.join(os.path.abspath(a.dst), fn); out.file_format = "PNG"; out.save()
    bpy.data.images.remove(out)
print("processed", len(files))
