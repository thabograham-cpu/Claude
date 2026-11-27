---
name: hotel-location-kit
description: Persistent, walkable 3D hotel location ("The Grand Aurelia") and the modular kit behind it, for headless Blender stories. One world frame connects the street and facade, entrance, lobby with reception desk, seating, plants, chandelier and signage, the elevator lobby with standard and VIP cars (animatable doors), the stairwell up nine floors, corridors with guest-room doors, suite 901 and a pet store on the same street. It includes procedural non-plastic materials (marble, wood, carpet, plaster, pavers), practical and sun/sky lighting, EEVEE quality settings, set origins for shot coordinates, camera containment (no clipping through walls) and walk-route checks. Use for any scene set in a hotel, lobby, corridor, stairwell or elevator, or when building another persistent interior from the same kit.
license: MIT
metadata:
  version: "1.0.0"
  domain: blender
  role: specialist
  triggers: hotel, lobby, reception desk, elevator, VIP elevator, stairwell, corridor, hallway, guest room, suite, luggage trolley, environment, set, location, persistent environment, world coordinates, exterior, street, facade
  related-skills: environment-artist, set-dressing, lighting, camera-cinematography, character-acting-director
---

# Hotel location kit (headless)

| Piece | Where |
|---|---|
| Kit and layout: materials, `MB` mesh builder, `wall` / `room` / `door` / `elevator`, furniture, plants, lights, signs, `grand_aurelia()`, checks | `tools/hotelkit.py` |
| Environment preview: routes check plus nine review stills | `projects/hotel/preview.py` |
| Production use | `projects/complainer/storyboard.py` (sets) → `scene.py` |

## The building (world metres, Z up, the street is on −Y)
| Area | Where | Notes |
|---|---|---|
| Street | y < −7.25 | Sidewalk pavers, curb, road with markings and crosswalk, streetlights, tree pits. Neighbouring buildings line both sides; the far side is at y = −24. |
| Facade and entrance | y = −7.25 | Limestone with brass-framed storefront glass. The 2.9 m open entrance sits under a canopy lettered "THE GRAND AURELIA", with a red carpet, topiaries and the AURELIA blade sign. |
| Lobby | x −7..7, y −7..5, 5 m high | The parts are listed below. |
| Elevator lobby | x 7.25..10.6 | Standard car at y 0.2 and VIP car (brass, "VIP ONLY", stanchions) at y 2.5. The cars are 1.8 m deep. |
| Stairwell | x −11.3..−7.5 | Switchback flights of 10 risers (0.18 × 0.3). Floor k is at z = 3.6k (1, M, 2…9 signs). The door is on the lobby's west wall. |
| Floors 4 and 9 | z 14.4 / 32.4 | Corridor C1 (stair door → elevator lobby) and corridor C2 (north), with numbered doors. C2 ends at ROOM 404 on floor 4 and at the suite door on floor 9. |
| Suite 901 | floor 9, y 7.25..14 | Window cut through the north facade, onto a night city. |
| Pet store | x 20.5..29.5 | Same street as the hotel. Display window, door, lit interior with shelves. |

**The lobby in detail:**
- **Floor:** marble tiles with grout, a dark border band and a medallion under the chandelier.
- **Walls:** plaster with walnut wainscot panels, chair rail and crown, plus a burgundy feature wall carrying brass lettering and a key wall.
- **Ceiling:** coffered.
- **Reception desk:** fluted walnut front, marble top at 1.16 m, monitor, bell, phone and brochures. Behind it are a back counter and pendant lights.
- **Seating:** two areas, each with a sofa, two armchairs, a coffee table, a side table with lamp, a rug, a painting and sconces.
- **Columns:** two, at (±4.5, −1.5).
- **Plants:** 10.

`ORIGIN` maps each set's local shot coordinates into the world, with its floor height. For example `stairs` = (−8.5, 0.5, 0): local y climbs flight A, and `z = 0.6 y + 0.18`. So old shot lists keep working.
`ANCHORS` names marks (desk_guest, desk_clerk, elev_vip_inside, stair_bottom, hall404, suite_door…).

## Use it
```python
import hotelkit as HK
W = HK.grand_aurelia()                    # whole building + street (~3 s, ~360 objects, ~42 lights)
HK.eevee_quality(scene, samples=16)       # raytraced reflections, fast GI/AO, soft shadows, AgX
W["obj"]["desk"], W["obj"]["elevator"], W["obj"]["door404"], W["elevators"]["vip"]
HK.key_doors(W["elevators"]["vip"], frame, openness)      # 1 open .. 0 closed
pos = HK.keep_inside(cam_pos, aim_point)  # pull a camera out of walls / back inside a room volume
HK.check_routes()                         # [] = every route has floor under it and nothing in the way
cart = HK.trolley("cart", W["palette"], coll)               # brass birdcage luggage trolley
```
**Building another hotel story or interior:**
- Reuse `room(...)` (floor, ceiling, walls with openings and trim), `door(...)`, `elevator(...)`, `sofa` / `armchair` / `table` / `rug` / `plant` / `column` / `chandelier` / `sconce` / `art` / `sign`, and `material(...)` for new surfaces.
- Register every room in `ROOMS`, so cameras stay inside, and every path in `ROUTES`.

## Rules
- **One world.** Rooms connect through real openings. Walls are shared, not doubled, so faces don't z-fight. Nothing floats; there are no stage voids. Every window and doorway looks onto something: a street, buildings, a lit interior or a night city.
- **Depth.** Keep foreground, middle-ground and background layers available in every room: plants, columns, sofa backs, pendants. Moving cameras then get parallax.
- **Materials: textured, never plastic.**
  - Roughness varies around its base value. Every surface has a small bump.
  - Metals (brass, steel) sit at roughness about 0.35; marble at about 0.3; fabric and carpet at 0.9 and above.
  - Textures use world position, so nothing stretches.
- **Lighting: practicals plus sun.**
  - Chandelier, pendants, sconces, lamps, elevator cars, stair bulkheads, canopy spots and streetlights.
  - Low-energy ceiling fills only.
  - The sun and sky come in through the entrance.
  - No flat, bright overall light.
- **Cameras.**
  - Run every shot camera through `keep_inside`.
  - Shots facing a wall of the set must still find a wall, not void: check stills.
  - For overhead shots, keep the camera under the ceiling (the lobby is 5 m).
- **Walking.** `check_routes()` must return `[]` after any layout change. Door leaves swing out of the walking line, and elevator doors default to open.
- **Check stills:** `STILLS=1 $PY tools/bl.py run projects/hotel/preview.py`. Look at the exterior, the lobby both ways, the desk, the elevators, the stairwell looking up, corridor 404, the suite and the overhead view, for voids, clipping and light.

## Known limits (shortcuts)
- Only floors 4 and 9 have corridors. Other floors' stair doors are closed.
- The sky is daytime. Night lobby scenes need a per-shot sun and sky change, which isn't built yet.
- Plants are stylised leaf clusters, not scanned foliage.
