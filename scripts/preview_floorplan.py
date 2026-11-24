#!/usr/bin/env python3
"""Render a top-down floor-plan preview (PNG) straight from the composed USD twin."""
import os
from pxr import Usd, UsdGeom, Gf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "usd", "DroneFactory.usd")
OUT = os.path.join(ROOT, "usd", "floorplan_preview.png")

COLORS = {
    "assembly_station": "#e8873a", "workstation": "#e8873a",
    "conveyor_system": "#3a7bd5", "conveyor": "#3a7bd5",
    "amr_fleet": "#2bb3a3", "amr": "#2bb3a3",
    "warehouse": "#8a63d2", "storage_rack": "#8a63d2",
    "outbound_shipping": "#d24d7b",
    "test_cell": "#4dd275",
    "robot_arm": "#f2c14e",
}

def wbounds(cache, prim):
    r = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    if r.IsEmpty():
        return None
    mn, mx = r.GetMin(), r.GetMax()
    return mn[0], mn[1], mx[0]-mn[0], mx[1]-mn[1]

def main():
    stage = Usd.Stage.Open(STAGE)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])

    fig, ax = plt.subplots(figsize=(14, 9))
    fig.patch.set_facecolor("#0e1116"); ax.set_facecolor("#0e1116")

    # building shell
    ax.add_patch(Rectangle((-40,-25), 80, 50, fill=False, ec="#5a6472", lw=2))
    ax.add_patch(Rectangle((-40,-25), 80, 50, fc="#161b22", ec="none", zorder=0))

    seen_labels = set()
    for p in stage.Traverse():
        sc = p.GetAttribute("semantic:class")
        if not (sc.IsValid() and sc.HasAuthoredValue()):
            continue
        cls = sc.Get()
        if cls not in COLORS:
            continue
        b = wbounds(cache, p)
        if not b:
            continue
        x,y,w,h = b
        # skip the giant floor/aggregate prims
        if w > 55 or h > 40:
            continue
        lbl = cls if cls not in seen_labels else None
        seen_labels.add(cls)
        ax.add_patch(Rectangle((x,y), w, h, fc=COLORS[cls], ec="white",
                               lw=0.4, alpha=0.85, zorder=3, label=lbl))

    # spine flow arrow (station 1 -> 5)
    ax.add_patch(FancyArrow(-30,0,58,0, width=0.3, head_width=1.6, head_length=2.5,
                            fc="#f2c14e", ec="none", alpha=0.5, zorder=2, length_includes_head=True))
    for i,(x,name) in enumerate([(-24,"1 Frame"),(-12,"2 Avionics"),(0,"3 Propulsion"),
                                 (12,"4 Power/Payload"),(24,"5 QA/Flight")]):
        ax.text(x, 5.2, name, color="white", ha="center", va="bottom", fontsize=9, zorder=5)

    ax.text(-36,-20,"INBOUND\nWAREHOUSE", color="#b79be6", fontsize=9, fontweight="bold")
    ax.text(30, 12,"OUTBOUND\nSHIPPING", color="#e88bad", fontsize=9, fontweight="bold", ha="center")
    ax.text(0,-14,"AMR LOGISTICS LOOP", color="#5fd4c7", fontsize=8, ha="center")
    ax.text(-31,18,"MEZZANINE / ENG. OFFICES", color="#9aa4b2", fontsize=8)

    ax.set_title("Swarmy — North Georgia Plant  |  OpenUSD Digital Twin (top-down)",
                 color="white", fontsize=14, pad=14)
    ax.set_xlim(-45,45); ax.set_ylim(-30,30); ax.set_aspect("equal")
    ax.tick_params(colors="#5a6472")
    for s in ax.spines.values(): s.set_color("#2a3038")
    leg = ax.legend(loc="lower right", framealpha=0.15, fontsize=8, labelcolor="white")
    plt.tight_layout()
    plt.savefig(OUT, dpi=130, facecolor=fig.get_facecolor())
    print("wrote", OUT)

if __name__ == "__main__":
    main()
