"""The Complainer cast: MPFB specs + flat colours. build(names) creates rigs parked at (0, -100, 0).
Used by storyboard.py (all five) and by face tests that only need one or two people."""
import cast

CAST = {
    "INF": dict(gender=1, age=0.4, height=0.6, weight=0.45, skin="young_caucasian_male2", hair="cortu_short_messy_hair",
                clothes=["elvs_hooded_sweat_jacket1", "punkduck_male_classic_jeans", "culturalibre_sneakers"],
                colors={"hooded": "ff4fa3", "jeans": "1b1b1b", "sneakers": "f5f5f5"}),
    "CLK": dict(gender=1, age=0.38, height=0.55, weight=0.42, skin="young_asian_male", hair="short02",
                clothes=["elvs_male_shirt_tie_tucked1", "mindfront_male_trousers_1", "mindfront_shoes_oxford_male"],
                colors={"shirt": "f2f2f2", "trousers": "232323", "oxford": "111111"}),
    "F1": dict(gender=1, age=0.35, height=0.6, weight=0.5, skin="young_african_male", hair="short04",
               clothes=["elvs_male_logo_tshirt1", "cortu_cargo_pants", "punkduck_tennis_shoes"],
               colors={"tshirt": "1aa6a6", "cargo": "6b6b4a", "tennis": "ffffff"}),
    "F2": dict(gender=0, age=0.35, height=0.48, weight=0.42, skin="young_caucasian_female", hair="ponytail01",
               clothes=["punkduck_v_neck_top", "punkduck_female_tight_jeans", "punkduck_tennis_shoes"],
               colors={"v_neck": "ffd54f", "jeans": "6d8fc7", "tennis": "ffffff"}),
    "MGR": dict(gender=1, age=0.72, height=0.5, weight=0.62, skin="middleage_caucasian_male", hair="short01",
                clothes=["elvs_male_shirt_untucked_bd1", "elvs_male_trouser", "mindfront_shoes_oxford_male"],
                colors={"shirt": "b3cde0", "trouser": "55585e", "oxford": "111111"}),
}
CAST["GST"] = dict(gender=0, age=0.62, height=0.45, weight=0.55, skin="middleage_caucasian_female", hair="ponytail01",   # background guest
                  clothes=["punkduck_v_neck_top", "punkduck_female_tight_jeans", "punkduck_tennis_shoes"],
                  colors={"v_neck": "2f3f6b", "jeans": "c9b79c", "tennis": "f0f0f0"})
SKIN = {"GST": "e6b9a0", "INF": "e8b89a", "CLK": "d9a77e", "F1": "6b4330", "F2": "f0c7aa", "MGR": "e3b294"}


def lin(h):
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


STORY = ["INF", "CLK", "F1", "F2", "MGR"]   # the story cast; background extras are built on request


def build(names=None):
    rigs = {}
    for name in names or STORY:
        c = dict(CAST[name]); colors = c.pop("colors")
        body, rig = cast.human(name, **c)
        for o in rig.children_recursive:
            if o.type != "MESH": continue
            nm = o.name.lower()
            col = next((v for k, v in colors.items() if k in nm), None)
            if col is None:
                col = SKIN[name] if ("body" in nm or "teeth" in nm or "tongue" in nm) else ("222222" if ("eye" in nm or "hair" in nm or "short" in nm or "ponytail" in nm or "messy" in nm) else "ffffff")
                if "high-poly" in nm: col = "f5f5f5"
            for sl in o.material_slots:
                if sl.material: sl.material.diffuse_color = (*lin(col), 1)
        rig.location = (0, -100, 0)
        rigs[name] = rig
    return rigs
