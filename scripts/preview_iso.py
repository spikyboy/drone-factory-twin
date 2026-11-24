#!/usr/bin/env python3
"""Axonometric (3D) massing preview rendered from the composed USD twin.

No GPU required. It FLATTENS the stage (expanding instances), then draws every
geometry leaf's world-space bounding box as a shaded box, coloured by its nearest
semantic ancestor (or by structural role for the building steel). This surfaces
the full massing: columns, roof trusses, racks, conveyor, robots and drones.
"""
import os
from pxr import Usd, UsdGeom
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "usd", "DroneFactory.usd")
OUT = os.path.join(ROOT, "usd", "isometric_preview.png")

SEM_COLOR = {
    "assembly_station": "#e8873a", "workstation": "#e8873a", "robot_arm": "#f2c14e",
    "conveyor": "#3a7bd5", "conveyor_system": "#3a7bd5",
    "amr": "#2bb3a3", "amr_fleet": "#2bb3a3",
    "storage_rack": "#8a63d2", "warehouse": "#8a63d2", "outbound_shipping": "#d24d7b",
    "test_cell": "#4dd275", "product_drone": "#12c9b0",
    "operator": "#f25c54", "mezzanine": "#aab4c2", "dock_door": "#7d8794",
    "safety_railing": "#c9a227",
}
# path-based fallbacks (structure has no per-prim semantics)
def path_color(path):
    s = str(path)
    if "/Structure/truss" in s: return "#5a6470"
    if "/Structure/col" in s or "/Structure/purlin" in s: return "#6b7480"
    if "/Services" in s: return "#454d57"
    if "/DockDoor" in s: return "#7d8794"
    if "/win_" in s or "/glass" in s or "net" in s: return "#5fa8c7"
    return None

SKIP = ("/Slab", "/Roof", "/wall_", "/FloorZones", "/FloorMarkings", "/ZoneAsm")


def faces(mn, mx):
    x0,y0,z0 = mn; x1,y1,z1 = mx
    v = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
         (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    return [[v[0],v[1],v[2],v[3]],[v[4],v[5],v[6],v[7]],
            [v[0],v[1],v[5],v[4]],[v[2],v[3],v[7],v[6]],
            [v[1],v[2],v[6],v[5]],[v[0],v[3],v[7],v[4]]]


def ancestor_sem(prim):
    p = prim
    while p and p.GetPath() != p.GetPath().GetParentPath():
        a = p.GetAttribute("semantic:class")
        if a and a.HasAuthoredValue():
            return a.Get()
        p = p.GetParent()
    return None


def main():
    stage = Usd.Stage.Open(STAGE)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    # include geometry that lives inside instanceable references
    predicate = Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)

    fig = plt.figure(figsize=(16, 9))
    fig.patch.set_facecolor("#0e1116")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0e1116")

    # floor as a wireframe outline only (a solid face wrecks matplotlib depth sort)
    fx = [-40,40,40,-40,-40]; fy = [-25,-25,25,25,-25]
    ax.plot(fx, fy, [0]*5, color="#39424e", linewidth=1.0)

    boxes = []   # (depthkey, facecolor, faces)
    drawn = {}
    for prim in stage.Traverse(predicate):
        if not prim.IsA(UsdGeom.Gprim):
            continue
        path = prim.GetPath()
        if any(k in str(path) for k in SKIP):
            continue
        r = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if r.IsEmpty():
            continue
        mn, mx = list(r.GetMin()), list(r.GetMax())
        if (mx[0]-mn[0]) > 60 or (mx[1]-mn[1]) > 45:
            continue
        sem = ancestor_sem(prim)
        color = SEM_COLOR.get(sem) or path_color(path) or "#3a4049"
        if sem in SEM_COLOR:
            drawn[sem] = SEM_COLOR[sem]
        depth = mn[0] + mn[1]      # painter's order for -58 azim view
        boxes.append((depth, color, faces(mn, mx)))

    for _, color, fc in sorted(boxes, key=lambda b: b[0]):
        ax.add_collection3d(Poly3DCollection(fc, facecolor=color, edgecolor="#0e1116",
                                             linewidths=0.15, alpha=0.96))

    ax.set_xlim(-40,40); ax.set_ylim(-25,25); ax.set_zlim(0,12)
    ax.set_box_aspect((80,50,30), zoom=1.25)
    ax.view_init(elev=42, azim=-50)
    ax.set_axis_off()
    fig.suptitle("Swarmy — North Georgia Plant   ·   OpenUSD Digital Twin (axonometric massing)",
                 color="white", fontsize=16, y=0.955)

    handles = [plt.Line2D([0],[0], marker="s", color="none", markerfacecolor=c,
                          markersize=11, label=k.replace("_"," "))
               for k,c in sorted(drawn.items())]
    handles.append(plt.Line2D([0],[0], marker="s", color="none", markerfacecolor="#6b7480",
                              markersize=11, label="structural steel"))
    fig.legend(handles=handles, loc="lower center", framealpha=0.1, fontsize=9,
               labelcolor="white", ncol=6, bbox_to_anchor=(0.5, 0.02))
    fig.subplots_adjust(left=0.0, right=1.0, top=0.98, bottom=0.06)
    plt.savefig(OUT, dpi=135, facecolor=fig.get_facecolor())
    print("wrote", OUT, "|", len(boxes), "boxes")


if __name__ == "__main__":
    main()
