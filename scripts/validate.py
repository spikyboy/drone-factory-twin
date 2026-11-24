#!/usr/bin/env python3
"""Headless validation of the composed DroneFactory stage."""
import os, sys
from pxr import Usd, UsdGeom, UsdLux, UsdShade, Gf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "usd", "DroneFactory.usd")

def main():
    stage = Usd.Stage.Open(STAGE)
    if not stage:
        print("FAIL: stage did not open"); sys.exit(1)

    counts = {}
    sems, lights, mats = 0, 0, 0
    prims = 0
    for p in stage.Traverse():
        prims += 1
        t = p.GetTypeName()
        counts[t] = counts.get(t, 0) + 1
        if p.GetAttribute("semantic:class").IsValid() and p.GetAttribute("semantic:class").HasAuthoredValue():
            sems += 1
        if p.IsA(UsdLux.LightAPI) or "Light" in str(t):
            lights += 1
        if p.IsA(UsdShade.Material):
            mats += 1

    print("Stage up-axis   :", UsdGeom.GetStageUpAxis(stage))
    print("Meters per unit :", UsdGeom.GetStageMetersPerUnit(stage))
    print("Sublayers       :", len(stage.GetRootLayer().subLayerPaths))
    print("Total prims     :", prims)
    print("Semantic prims  :", sems)
    print("Lights          :", lights)
    print("Materials       :", mats)

    # world bounding box (checks geometry actually composed with transforms)
    bbox = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    wb = bbox.ComputeWorldBound(stage.GetPseudoRoot()).ComputeAlignedRange()
    print("World bounds min:", tuple(round(v,1) for v in wb.GetMin()))
    print("World bounds max:", tuple(round(v,1) for v in wb.GetMax()))

    # facility metadata check
    world = stage.GetPrimAtPath("/World")
    cd = world.GetCustomData().get("aif:core", {})
    print("Facility        :", cd.get("facility_name"), "|", cd.get("location"))
    print("Compliance      :", cd.get("compliance"))

    assert prims > 100, "expected a populated stage"
    assert sems >= 20, "expected many semantic labels"
    assert lights >= 5, "expected a lighting rig"
    assert wb.GetMax()[0] > 30, "expected an ~80m-wide building"
    print("\nVALIDATION PASSED ✓")

if __name__ == "__main__":
    main()
