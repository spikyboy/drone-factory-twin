#!/usr/bin/env python3
"""
generate_factory.py
===================
Procedurally builds an OpenUSD digital twin of a U.S. drone-manufacturing
facility -- "Swarmy - North Georgia Plant" -- organised the way an NVIDIA
Omniverse DSX / SimReady factory twin is structured:

    usd/DroneFactory.usd            <- root interface (sublayer stack + stage metadata)
    usd/assets/prototypes.usd       <- reusable component library (class prims, self-contained materials)
    usd/layers/building.usd         <- architectural shell + structural steel + site
    usd/layers/layout.usd           <- production line: 5 assembly stations on a spine
    usd/layers/equipment.usd        <- robots, conveyors, AMRs, storage, test cells
    usd/layers/lighting.usd         <- UsdLux rig (dome + high-bay area lights)
    usd/layers/semantics.usd        <- non-destructive aif:core / semantic metadata

Everything is self-contained procedural geometry (primitives + capsules/cones/
spheres, no external asset downloads), so the stage composes and renders
anywhere OpenUSD is available and opens directly in Omniverse USD Composer / Kit
on an RTX workstation.
"""

from pxr import Usd, UsdGeom, UsdLux, UsdShade, UsdPhysics, Sdf, Gf
import os, math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
USD_DIR = os.path.join(ROOT, "usd")
LAYER_DIR = os.path.join(USD_DIR, "layers")
ASSET_DIR = os.path.join(USD_DIR, "assets")

M = 1.0  # meters per unit

# ---- branding / facility identity -----------------------------------------
FACILITY = {
    "facility_name": "Swarmy - North Georgia Plant",
    "operator": "Swarmy Inc.",
    "location": "Gainesville, Georgia, USA",
    "region": "North Georgia",
    "product": "Swarmy S-1 sUAS",
    "product_mfr": "Swarmy",
    "product_model": "S-1 Scout",
    "compliance": "NDAA Section 848 (Blue UAS) domestic sourcing",
    "footprint_m2": "4000",
    "annual_capacity_units": "18000",
}

# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def new_stage(path, up="Z"):
    stage = Usd.Stage.CreateNew(path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z if up == "Z" else UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, M)
    stage.SetMetadata("kilogramsPerUnit", 1.0)
    return stage


def xform(stage, path, t=None, r=None, s=None):
    xf = UsdGeom.Xform.Define(stage, path)
    if t is not None: xf.AddTranslateOp().Set(Gf.Vec3d(*t))
    if r is not None: xf.AddRotateXYZOp().Set(Gf.Vec3f(*r))
    if s is not None: xf.AddScaleOp().Set(Gf.Vec3f(*s))
    return xf


def _place(prim, t, r, s):
    if t is not None: prim.AddTranslateOp().Set(Gf.Vec3d(*t))
    if r is not None: prim.AddRotateXYZOp().Set(Gf.Vec3f(*r))
    if s is not None: prim.AddScaleOp().Set(Gf.Vec3f(*s))


def _finish(prim, color, mat):
    if color is not None:
        prim.GetDisplayColorAttr().Set([Gf.Vec3f(*color)])
    if mat is not None:
        UsdShade.MaterialBindingAPI(prim).Bind(mat)


def cube(stage, path, size=1.0, t=None, r=None, s=None, color=None, mat=None):
    c = UsdGeom.Cube.Define(stage, path)
    c.GetSizeAttr().Set(size)
    h = size / 2.0
    c.GetExtentAttr().Set([(-h, -h, -h), (h, h, h)])
    _place(c, t, r, s); _finish(c, color, mat)
    return c


def cylinder(stage, path, radius=0.5, height=1.0, axis="Z", t=None, r=None, s=None, color=None, mat=None):
    cy = UsdGeom.Cylinder.Define(stage, path)
    cy.GetRadiusAttr().Set(radius); cy.GetHeightAttr().Set(height); cy.GetAxisAttr().Set(axis)
    _set_axis_extent(cy, radius, height, axis)
    _place(cy, t, r, s); _finish(cy, color, mat)
    return cy


def capsule(stage, path, radius=0.2, height=1.0, axis="Z", t=None, r=None, s=None, color=None, mat=None):
    cp = UsdGeom.Capsule.Define(stage, path)
    cp.GetRadiusAttr().Set(radius); cp.GetHeightAttr().Set(height); cp.GetAxisAttr().Set(axis)
    _set_axis_extent(cp, radius, height, axis, cap=True)
    _place(cp, t, r, s); _finish(cp, color, mat)
    return cp


def cone(stage, path, radius=0.3, height=0.6, axis="Z", t=None, r=None, s=None, color=None, mat=None):
    cn = UsdGeom.Cone.Define(stage, path)
    cn.GetRadiusAttr().Set(radius); cn.GetHeightAttr().Set(height); cn.GetAxisAttr().Set(axis)
    _set_axis_extent(cn, radius, height, axis)
    _place(cn, t, r, s); _finish(cn, color, mat)
    return cn


def sphere(stage, path, radius=0.3, t=None, r=None, s=None, color=None, mat=None):
    sp = UsdGeom.Sphere.Define(stage, path)
    sp.GetRadiusAttr().Set(radius)
    sp.GetExtentAttr().Set([(-radius,-radius,-radius),(radius,radius,radius)])
    _place(sp, t, r, s); _finish(sp, color, mat)
    return sp


def _set_axis_extent(prim, radius, height, axis, cap=False):
    half = height / 2.0 + (radius if cap else 0.0)
    r = radius
    if axis == "X":
        ext = [(-half, -r, -r), (half, r, r)]
    elif axis == "Y":
        ext = [(-r, -half, -r), (r, half, r)]
    else:
        ext = [(-r, -r, -half), (r, r, half)]
    prim.GetExtentAttr().Set(ext)


def pbr_material(stage, path, color, rough=0.5, metal=0.0, opacity=1.0):
    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, path + "/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rough)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metal)
    if opacity < 1.0:
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def add_semantics(prim, sem_class, extra=None):
    prim.CreateAttribute("semantic:class", Sdf.ValueTypeNames.Token).Set(sem_class)
    cd = {"semantics": {"class": sem_class}}
    if extra:
        cd["aif:core"] = extra
        for k, v in extra.items():
            prim.CreateAttribute(f"aif:core:{k}", Sdf.ValueTypeNames.String).Set(str(v))
    prim.SetCustomData(cd)


def add_collider(prim, rigid=False, mass=None):
    UsdPhysics.CollisionAPI.Apply(prim.GetPrim())
    if rigid:
        UsdPhysics.RigidBodyAPI.Apply(prim.GetPrim())
    if mass is not None:
        UsdPhysics.MassAPI.Apply(prim.GetPrim()).GetMassAttr().Set(mass)


# material palette: key -> (color, roughness, metallic[, opacity])
MAT_SPEC = {
    "steel":  ((0.55, 0.57, 0.60), 0.35, 1.0),
    "darksteel": ((0.22, 0.23, 0.26), 0.45, 0.9),
    "safety": ((0.95, 0.75, 0.05), 0.6, 0.0),
    "robot":  ((0.92, 0.40, 0.06), 0.4, 0.2),
    "carbon": ((0.07, 0.07, 0.09), 0.3, 0.1),
    "rubber": ((0.09, 0.09, 0.11), 0.9, 0.0),
    "panel":  ((0.80, 0.82, 0.85), 0.5, 0.1),
    "glass":  ((0.55, 0.75, 0.85), 0.05, 0.0, 0.28),
    "amr":    ((0.10, 0.42, 0.82), 0.4, 0.3),
    "swarmy": ((0.05, 0.62, 0.55), 0.4, 0.2),   # Swarmy teal brand
    "hivis":  ((0.95, 0.45, 0.05), 0.7, 0.0),
    "skin":   ((0.80, 0.62, 0.50), 0.7, 0.0),
    "denim":  ((0.20, 0.28, 0.45), 0.8, 0.0),
    "red":    ((0.80, 0.10, 0.10), 0.5, 0.0),
    "green":  ((0.10, 0.65, 0.25), 0.5, 0.0),
    "screen": ((0.10, 0.15, 0.22), 0.15, 0.0),
    "carton": ((0.72, 0.55, 0.35), 0.85, 0.0),
    "wood":   ((0.55, 0.40, 0.24), 0.8, 0.0),
}


# ---------------------------------------------------------------------------
# 1. PROTOTYPE LIBRARY  (reusable, instanceable component definitions)
# ---------------------------------------------------------------------------

def build_prototypes():
    path = os.path.join(ASSET_DIR, "prototypes.usd")
    stage = new_stage(path)
    stage.SetDefaultPrim(UsdGeom.Scope.Define(stage, "/Prototypes").GetPrim())
    proto = "/Prototypes"

    # Materials live INSIDE each prototype subtree so bindings survive referencing.
    _mat_cache = {}
    def M_(root, key):
        ck = (root, key)
        if ck not in _mat_cache:
            spec = MAT_SPEC[key]
            color, rough, metal = spec[0], spec[1], spec[2]
            op = spec[3] if len(spec) > 3 else 1.0
            _mat_cache[ck] = pbr_material(stage, f"{root}/Looks/{key.capitalize()}", color, rough, metal, op)
        return _mat_cache[ck]

    class _Mats:
        def __init__(self, root): self.root = root
        def __getitem__(self, k): return M_(self.root, k)

    # ============================ ROBOT ARM (articulated, 6-axis) ===========
    P = proto + "/RobotArm"; m = _Mats(P)
    arm = xform(stage, P); arm.GetPrim().SetInstanceable(True)
    cylinder(stage, P+"/pedestal", 0.42, 0.20, t=(0,0,0.10), mat=m["darksteel"])
    cube(stage, P+"/pedestal_guard", 1.0, t=(0,0,0.02), s=(1.0,1.0,0.04), mat=m["safety"])
    cylinder(stage, P+"/base", 0.34, 0.42, t=(0,0,0.41), mat=m["robot"])
    sphere(stage, P+"/j_shoulder", 0.30, t=(0,0,0.66), mat=m["darksteel"])
    # upper arm (tilted back a bit), elbow, forearm reaching forward over bench
    capsule(stage, P+"/link_upper", 0.16, 0.85, axis="Z", t=(0.05,0,1.12), r=(0,18,0), mat=m["robot"])
    sphere(stage, P+"/j_elbow", 0.20, t=(0.42,0,1.55), mat=m["darksteel"])
    capsule(stage, P+"/link_fore", 0.125, 0.85, axis="Z", t=(0.95,0,1.62), r=(0,78,0), mat=m["robot"])
    sphere(stage, P+"/j_wrist", 0.14, t=(1.42,0,1.72), mat=m["darksteel"])
    capsule(stage, P+"/link_wrist", 0.10, 0.22, axis="X", t=(1.60,0,1.72), mat=m["robot"])
    # gripper: palm + 2 fingers
    cube(stage, P+"/grip_palm", 1.0, t=(1.78,0,1.72), s=(0.10,0.22,0.14), mat=m["steel"])
    cube(stage, P+"/grip_f1", 1.0, t=(1.86,0.09,1.72), s=(0.14,0.04,0.10), mat=m["darksteel"])
    cube(stage, P+"/grip_f2", 1.0, t=(1.86,-0.09,1.72), s=(0.14,0.04,0.10), mat=m["darksteel"])
    # dressing / cable pack along the forearm
    capsule(stage, P+"/cable", 0.04, 0.7, axis="Z", t=(0.9,0.16,1.6), r=(0,78,0), mat=m["carbon"])
    add_semantics(arm.GetPrim(), "robot_arm",
                  {"manufacturer": "FANUC", "model": "M-20iD/25", "axes": "6", "payload_kg": "25", "reach_m": "1.83", "asset_version": "2.0"})

    # ============================ CONVEYOR SEGMENT (roller, 2 m) ============
    P = proto + "/ConveyorSegment"; m = _Mats(P)
    conv = xform(stage, P); conv.GetPrim().SetInstanceable(True)
    for side in (-0.42, 0.42):
        cube(stage, P+f"/rail_{'p' if side>0 else 'n'}", 1.0, t=(0,side,0.56), s=(2.0,0.08,0.18), mat=m["steel"])
    # rollers across the width
    nx = 9
    for i in range(nx):
        x = -0.9 + i*(1.8/(nx-1))
        cylinder(stage, P+f"/roller_{i}", 0.055, 0.80, axis="Y", t=(x,0,0.57), mat=m["darksteel"])
    # legs + cross brace + drive motor
    for lx in (-0.85, 0.85):
        for ly in (-0.42, 0.42):
            cube(stage, P+f"/leg_{'p' if lx>0 else 'n'}_{'p' if ly>0 else 'n'}", 1.0,
                 t=(lx,ly,0.28), s=(0.07,0.07,0.56), mat=m["steel"])
    cube(stage, P+"/motor", 1.0, t=(0.9,0.5,0.45), s=(0.22,0.18,0.22), mat=m["swarmy"])
    add_semantics(conv.GetPrim(), "conveyor",
                  {"manufacturer": "Dorner", "model": "3200-Series", "type": "roller", "speed_m_s": "0.25", "asset_version": "2.0"})

    # ============================ WORKSTATION ==============================
    P = proto + "/Workstation"; m = _Mats(P)
    stn = xform(stage, P); stn.GetPrim().SetInstanceable(True)
    cube(stage, P+"/bench", 1.0, t=(0,0,0.90), s=(2.4,1.1,0.08), mat=m["panel"])
    for sx in (-1.05,1.05):
        for sy in (-0.45,0.45):
            cube(stage, P+f"/leg_{'p' if sx>0 else 'n'}_{'p' if sy>0 else 'n'}", 1.0,
                 t=(sx,sy,0.45), s=(0.07,0.07,0.90), mat=m["steel"])
    # pegboard tool wall + tools
    cube(stage, P+"/pegboard", 1.0, t=(0,0.52,1.55), s=(2.2,0.05,1.0), mat=m["swarmy"])
    for i,tx in enumerate((-0.8,-0.5,-0.2)):
        capsule(stage, P+f"/tool_{i}", 0.03, 0.22, axis="Z", t=(tx,0.46,1.55), mat=m["darksteel"])
    cube(stage, P+"/tool_box", 1.0, t=(0.6,0.42,1.5), s=(0.5,0.12,0.3), mat=m["red"])
    # dual monitors on a stand
    cube(stage, P+"/mon_arm", 1.0, t=(-0.7,0.4,1.35), s=(0.05,0.05,0.5), mat=m["darksteel"])
    for i,mx in enumerate((-0.95,-0.45)):
        cube(stage, P+f"/monitor_{i}", 1.0, t=(mx,0.36,1.55), s=(0.42,0.03,0.28), r=(8,0,0), mat=m["screen"])
    # parts bins
    for i,bx in enumerate((0.2,0.55,0.9)):
        cube(stage, P+f"/bin_{i}", 1.0, t=(bx,-0.2,1.0), s=(0.28,0.4,0.14),
             mat=(m["safety"] if i%2 else m["amr"]))
    # task light + anti-fatigue mat + stool
    capsule(stage, P+"/tasklight", 0.03, 0.5, axis="X", t=(-0.3,0.1,1.9), mat=m["steel"])
    cube(stage, P+"/mat", 1.0, t=(0,-1.0,0.02), s=(1.6,0.7,0.03), mat=m["rubber"])
    cylinder(stage, P+"/stool_seat", 0.20, 0.06, t=(0,-1.0,0.55), mat=m["darksteel"])
    cylinder(stage, P+"/stool_post", 0.04, 0.5, t=(0,-1.0,0.28), mat=m["steel"])
    add_semantics(stn.GetPrim(), "workstation",
                  {"manufacturer": "Bosch Rexroth", "model": "ActiveAssist", "asset_version": "2.0"})

    # ============================ STORAGE RACK =============================
    P = proto + "/StorageRack"; m = _Mats(P)
    rack = xform(stage, P); rack.GetPrim().SetInstanceable(True)
    for sx in (-1.35,1.35):
        for sy in (-0.55,0.55):
            cube(stage, P+f"/post_{'p' if sx>0 else 'n'}_{'p' if sy>0 else 'n'}", 1.0,
                 t=(sx,sy,2.0), s=(0.10,0.10,4.0), mat=m["safety"])
    import_hash = 0
    for lvl,z in enumerate((0.55,1.85,3.15)):
        # beams front/back
        for by in (-0.55,0.55):
            cube(stage, P+f"/beam_{lvl}_{'p' if by>0 else 'n'}", 1.0, t=(0,by,z), s=(2.8,0.08,0.10), mat=m["safety"])
        cube(stage, P+f"/deck_{lvl}", 1.0, t=(0,0,z-0.03), s=(2.75,1.15,0.03), mat=m["steel"])
        # cartons of varying size / color
        for j,cx in enumerate((-0.95,-0.3,0.35,0.95)):
            hgt = 0.35 + 0.12*((j+lvl)%3)
            col = ["carton","swarmy","amr","carton"][(j+lvl)%4]
            cube(stage, P+f"/carton_{lvl}_{j}", 1.0, t=(cx,0,z+hgt/2+0.02),
                 s=(0.55,0.85,hgt), mat=m[col])
    add_semantics(rack.GetPrim(), "storage_rack",
                  {"manufacturer": "Steel King", "model": "SK-2000", "levels": "3", "asset_version": "2.0"})

    # ============================ AMR (sensored) ===========================
    P = proto + "/AMR"; m = _Mats(P)
    amr = xform(stage, P); amr.GetPrim().SetInstanceable(True)
    cube(stage, P+"/chassis", 1.0, t=(0,0,0.20), s=(1.10,0.68,0.26), mat=m["amr"])
    cube(stage, P+"/chassis_top", 1.0, t=(0,0,0.36), s=(0.95,0.6,0.08), mat=m["darksteel"])
    cube(stage, P+"/deck", 1.0, t=(0,0,0.42), s=(1.0,0.62,0.04), mat=m["steel"])
    # lidar pucks at diagonal corners + status light bar + e-stop
    for cx,cy in ((0.5,0.30),(-0.5,-0.30)):
        cylinder(stage, P+f"/lidar_{'p' if cx>0 else 'n'}", 0.07, 0.09, t=(cx,cy,0.34), mat=m["carbon"])
    capsule(stage, P+"/statusbar", 0.03, 0.5, axis="Y", t=(0,0,0.45), mat=m["swarmy"])
    cylinder(stage, P+"/estop", 0.05, 0.05, t=(0.45,0,0.47), mat=m["red"])
    for wx in (-0.4,0.4):
        for wy in (-0.33,0.33):
            cylinder(stage, P+f"/wheel_{'p' if wx>0 else 'n'}_{'p' if wy>0 else 'n'}",
                     0.13, 0.08, axis="Y", t=(wx,wy,0.13), mat=m["rubber"])
    for cx in (-0.5,0.5):   # casters
        sphere(stage, P+f"/caster_{'p' if cx>0 else 'n'}", 0.06, t=(cx,0,0.06), mat=m["darksteel"])
    add_semantics(amr.GetPrim(), "amr",
                  {"manufacturer": "MiR", "model": "MiR250", "payload_kg": "250", "sensors": "2x safety lidar", "asset_version": "2.0"})

    # ============================ PRODUCT DRONE (Swarmy S-1) ===============
    P = proto + "/Drone"; m = _Mats(P)
    dr = xform(stage, P); dr.GetPrim().SetInstanceable(True)
    cube(stage, P+"/body", 1.0, t=(0,0,0), s=(0.34,0.30,0.10), mat=m["carbon"])
    sphere(stage, P+"/canopy", 0.16, t=(0.02,0,0.06), s=(1.0,0.9,0.55), mat=m["swarmy"])
    arms = [(0.30,0.30),(-0.30,0.30),(-0.30,-0.30),(0.30,-0.30)]
    for i,(ax,ay) in enumerate(arms):
        ang = math.degrees(math.atan2(ay,ax))
        capsule(stage, P+f"/arm_{i}", 0.028, 0.42, axis="X", t=(ax/2,ay/2,0), r=(0,0,ang), mat=m["carbon"])
        cylinder(stage, P+f"/motor_{i}", 0.045, 0.055, t=(ax,ay,0.03), mat=m["darksteel"])
        cone(stage, P+f"/bell_{i}", 0.045, 0.04, t=(ax,ay,0.07), mat=m["steel"])
        # two-blade prop
        for b,br in enumerate((0,90)):
            cube(stage, P+f"/prop_{i}_{b}", 1.0, t=(ax,ay,0.10), s=(0.34,0.03,0.006), r=(0,0,br), mat=m["panel"])
        # landing leg
        capsule(stage, P+f"/leg_{i}", 0.012, 0.12, axis="Z", t=(ax*0.7,ay*0.7,-0.10), r=(ay*18,-ax*18,0), mat=m["darksteel"])
    # front camera gimbal + antenna
    sphere(stage, P+"/gimbal", 0.05, t=(0.14,0,-0.07), mat=m["darksteel"])
    cone(stage, P+"/lens", 0.03, 0.05, axis="X", t=(0.20,0,-0.07), r=(0,90,0), mat=m["screen"])
    capsule(stage, P+"/antenna", 0.006, 0.12, axis="Z", t=(-0.14,0,0.10), mat=m["darksteel"])
    add_semantics(dr.GetPrim(), "product_drone",
                  {"manufacturer": FACILITY["product_mfr"], "model": FACILITY["product_model"],
                   "class": "sUAS", "config": "quad-X", "mtow_kg": "2.4", "asset_version": "2.0"})

    # ============================ FLIGHT-TEST CELL =========================
    P = proto + "/TestCell"; m = _Mats(P)
    cage = xform(stage, P); cage.GetPrim().SetInstanceable(True)
    for sx in (-3,3):
        for sy in (-3,3):
            cube(stage, P+f"/post_{'p' if sx>0 else 'n'}_{'p' if sy>0 else 'n'}", 1.0,
                 t=(sx,sy,2.0), s=(0.10,0.10,4.0), mat=m["safety"])
    # top frame beams
    for sy in (-3,3):
        cube(stage, P+f"/topbeam_{'p' if sy>0 else 'n'}", 1.0, t=(0,sy,4.0), s=(6.0,0.08,0.08), mat=m["safety"])
    for sx in (-3,3):
        cube(stage, P+f"/topbeam_x_{'p' if sx>0 else 'n'}", 1.0, t=(sx,0,4.0), s=(0.08,6.0,0.08), mat=m["safety"])
    # translucent net walls + roof
    for sy,tag in ((-3,"s"),(3,"n")):
        cube(stage, P+f"/net_{tag}", 1.0, t=(0,sy,2.0), s=(6.0,0.02,4.0), mat=m["glass"])
    for sx,tag in ((-3,"w"),(3,"e")):
        cube(stage, P+f"/net_{tag}", 1.0, t=(sx,0,2.0), s=(0.02,6.0,4.0), mat=m["glass"])
    cube(stage, P+"/net_top", 1.0, t=(0,0,4.0), s=(6.0,6.0,0.02), mat=m["glass"])
    cylinder(stage, P+"/pad", 1.2, 0.03, t=(0,0,0.02), mat=m["swarmy"])
    add_semantics(cage.GetPrim(), "test_cell",
                  {"manufacturer": "Swarmy", "model": "FlightTest-6x6", "asset_version": "2.0"})

    # ============================ OPERATOR (posed technician) ==============
    P = proto + "/Operator"; m = _Mats(P)
    opr = xform(stage, P); opr.GetPrim().SetInstanceable(True)
    for lx in (-0.11,0.11):
        capsule(stage, P+f"/leg_{'p' if lx>0 else 'n'}", 0.09, 0.65, axis="Z", t=(lx,0,0.45), mat=m["denim"])
    capsule(stage, P+"/torso", 0.16, 0.45, axis="Z", t=(0,0,1.15), mat=m["hivis"])
    for ax in (-0.22,0.22):
        capsule(stage, P+f"/arm_{'p' if ax>0 else 'n'}", 0.05, 0.5, axis="Z", t=(ax,0.05,1.15), r=(20,0,0), mat=m["hivis"])
    sphere(stage, P+"/head", 0.12, t=(0,0,1.62), mat=m["skin"])
    sphere(stage, P+"/hardhat", 0.135, t=(0,0,1.68), s=(1.0,1.0,0.6), mat=m["safety"])
    add_semantics(opr.GetPrim(), "operator", {"role": "assembly_technician", "ppe": "hi-vis + hard hat"})

    stage.GetRootLayer().Save()
    return path


# ---------------------------------------------------------------------------
# structural helpers used by the building layer
# ---------------------------------------------------------------------------

def i_column(stage, base, x, y, h, mat):
    """A simple wide-flange steel column (two flanges + web) from z=0 to z=h."""
    g = xform(stage, base, t=(x,y,0))
    cube(stage, base+"/web", 1.0, t=(0,0,h/2), s=(0.05,0.22,h), mat=mat)
    for fy in (-0.11,0.11):
        cube(stage, base+f"/flange_{'p' if fy>0 else 'n'}", 1.0, t=(0,fy,h/2), s=(0.24,0.04,h), mat=mat)
    cube(stage, base+"/baseplate", 1.0, t=(0,0,0.04), s=(0.5,0.5,0.08), mat=mat)
    return g


def roof_truss(stage, base, x, span, z_bot, depth, mat):
    """Parallel-chord truss spanning along Y at height z_bot..z_bot+depth."""
    g = xform(stage, base, t=(x,0,0))
    cube(stage, base+"/chord_bot", 1.0, t=(0,0,z_bot), s=(0.14,span,0.10), mat=mat)
    cube(stage, base+"/chord_top", 1.0, t=(0,0,z_bot+depth), s=(0.14,span,0.10), mat=mat)
    n = int(span // 2.5)
    for i in range(n+1):
        y = -span/2 + i*(span/n)
        cube(stage, base+f"/vert_{i}", 1.0, t=(0,y,z_bot+depth/2), s=(0.07,0.07,depth), mat=mat)
        if i < n:
            y2 = -span/2 + (i+0.5)*(span/n)
            L = math.hypot(span/n/2, depth)
            ang = math.degrees(math.atan2(depth, span/n/2))
            capsule(stage, base+f"/diag_{i}", 0.03, L*0.8, axis="Z",
                    t=(0,y2,z_bot+depth/2), r=(90-ang if i%2 else -(90-ang),0,0), mat=mat)
    return g


# ---------------------------------------------------------------------------
# 2. BUILDING SHELL + STRUCTURE + SITE
# ---------------------------------------------------------------------------

def build_building():
    path = os.path.join(LAYER_DIR, "building.usd")
    stage = new_stage(path)
    root = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(root.GetPrim())
    b = "/World/Building"; xform(stage, b)

    def mat(key):
        spec = MAT_SPEC[key]; color, rough, metal = spec[0], spec[1], spec[2]
        op = spec[3] if len(spec) > 3 else 1.0
        return pbr_material(stage, b+f"/Looks/{key.capitalize()}", color, rough, metal, op)
    concrete = pbr_material(stage, b+"/Looks/Concrete", (0.62,0.62,0.64), 0.85, 0.0)
    wallmat  = pbr_material(stage, b+"/Looks/Wall", (0.86,0.87,0.88), 0.7, 0.0)
    steel = mat("steel"); glass = mat("glass"); safety = mat("safety")
    swarmy = mat("swarmy"); dark = mat("darksteel")
    zone_asm = pbr_material(stage, b+"/Looks/ZoneAsm", (0.20,0.42,0.55), 0.9, 0.0)
    zone_wh  = pbr_material(stage, b+"/Looks/ZoneWh", (0.55,0.48,0.12), 0.9, 0.0)
    zone_shp = pbr_material(stage, b+"/Looks/ZoneShp", (0.16,0.40,0.22), 0.9, 0.0)
    linemat  = pbr_material(stage, b+"/Looks/Line", (0.95,0.85,0.15), 0.6, 0.0)

    W, L, H = 80.0, 50.0, 11.0
    slab = cube(stage, b+"/Slab", 1.0, t=(0,0,-0.1), s=(W,L,0.2), mat=concrete)
    add_collider(slab); add_semantics(slab.GetPrim(), "floor", {"area_m2": str(int(W*L)), "surface": "sealed_concrete"})

    # perimeter walls (leave gaps near top for clerestory)
    for name,t,s in [("wall_n",(0,L/2,4.5),(W,0.3,9.0)),("wall_s",(0,-L/2,4.5),(W,0.3,9.0)),
                     ("wall_w",(-W/2,0,4.5),(0.3,L,9.0))]:
        wl = cube(stage, b+f"/{name}", 1.0, t=t, s=s, mat=wallmat); add_collider(wl)
    # east wall split around 3 dock doors
    cube(stage, b+"/wall_e_top", 1.0, t=(W/2,0,9.5), s=(0.3,L,3.0), mat=wallmat)
    for i,dy in enumerate((-14,0,14)):
        cube(stage, b+f"/wall_e_pier_{i}", 1.0, t=(W/2,dy,4.0), s=(0.3,4.0,8.0), mat=wallmat)
    for i,dy in enumerate((-7,7,21)):   # actually place doors between piers
        pass
    # roll-up dock doors (segmented)
    for i,dy in enumerate((-7.0,7.0)):
        door = xform(stage, b+f"/DockDoor_{i}", t=(W/2-0.15,dy,0))
        for k in range(7):
            cube(stage, b+f"/DockDoor_{i}/slat_{k}", 1.0, t=(0,0,0.6+k*0.9), s=(0.06,5.0,0.85), mat=dark)
        add_semantics(door.GetPrim(), "dock_door", {"id": f"D{i+1}", "type": "roll-up"})

    # clerestory window band (all four sides, near top)
    for name,t,s in [("win_n",(0,L/2,9.6),(W,0.1,1.6)),("win_s",(0,-L/2,9.6),(W,0.1,1.6)),
                     ("win_w",(-W/2,0,9.6),(0.1,L,1.6))]:
        cube(stage, b+f"/{name}", 1.0, t=t, s=s, mat=glass)

    cube(stage, b+"/Roof", 1.0, t=(0,0,H), s=(W,L,0.2), mat=wallmat)

    # ---- structural steel: perimeter columns + interior column rows ----
    struct = xform(stage, b+"/Structure")
    add_semantics(struct.GetPrim(), "structural_steel", {"system": "wide_flange_columns + parallel_chord_trusses"})
    col_x = [-36,-27,-18,-9,0,9,18,27,36]
    for i,x in enumerate(col_x):
        for y in (-24.5,24.5):
            i_column(stage, b+f"/Structure/col_{i}_{'p' if y>0 else 'n'}", x, y, 9.6, steel)
    # roof trusses spanning across width every ~9 m
    for i,x in enumerate([-30,-18,-6,6,18,30]):
        roof_truss(stage, b+f"/Structure/truss_{i}", x, 48.0, 9.6, 1.1, steel)
    # purlins along X
    for j,y in enumerate(range(-20,21,10)):
        cube(stage, b+f"/Structure/purlin_{j}", 1.0, t=(0,y,10.7), s=(72,0.08,0.12), mat=steel)

    # ---- overhead services: cable tray + HVAC duct ----
    svc = xform(stage, b+"/Services")
    cube(stage, b+"/Services/cable_tray", 1.0, t=(0,3,9.0), s=(66,0.4,0.15), mat=dark)
    cylinder(stage, b+"/Services/hvac_duct", 0.45, 60.0, axis="X", t=(0,-8,8.6), mat=steel)
    for j,x in enumerate(range(-24,25,12)):
        cube(stage, b+f"/Services/diffuser_{j}", 1.0, t=(x,-8,8.1), s=(0.6,0.6,0.2), mat=dark)
    add_semantics(svc.GetPrim(), "building_services", {"includes": "cable_tray, HVAC"})

    # ---- floor zone paint ----
    zones = xform(stage, b+"/FloorZones")
    cube(stage, b+"/FloorZones/assembly", 1.0, t=(0,1.5,0.005), s=(62,9,0.01), mat=zone_asm)
    cube(stage, b+"/FloorZones/warehouse", 1.0, t=(-28,-19,0.005), s=(22,10,0.01), mat=zone_wh)
    cube(stage, b+"/FloorZones/shipping", 1.0, t=(32,10,0.005), s=(12,14,0.01), mat=zone_shp)
    add_semantics(zones.GetPrim(), "floor_zones", {"standard": "5S zone marking"})
    # aisle + AMR loop lines
    aisle = xform(stage, b+"/FloorMarkings")
    cube(stage, b+"/FloorMarkings/spine", 1.0, t=(0,0,0.01), s=(66,0.25,0.01), mat=linemat)
    cube(stage, b+"/FloorMarkings/amr_n", 1.0, t=(0,-14,0.01), s=(66,0.2,0.01), mat=linemat)
    cube(stage, b+"/FloorMarkings/amr_e", 1.0, t=(33,-7,0.01), s=(0.2,14,0.01), mat=linemat)
    cube(stage, b+"/FloorMarkings/amr_w", 1.0, t=(-33,-7,0.01), s=(0.2,14,0.01), mat=linemat)
    add_semantics(aisle.GetPrim(), "floor_markings", {"standard": "OSHA_aisle_marking"})

    # ---- production-line safety railing (both sides of the spine) ----
    rail = xform(stage, b+"/LineRailing")
    for sy in (-3.6,3.6):
        cube(stage, b+f"/LineRailing/rail_{'p' if sy>0 else 'n'}", 1.0, t=(0,sy,1.05), s=(60,0.04,0.05), mat=safety)
        for k in range(-30,31,3):
            cube(stage, b+f"/LineRailing/post_{'p' if sy>0 else 'n'}_{k+30}", 1.0, t=(k,sy,0.55), s=(0.05,0.05,1.05), mat=safety)
    add_semantics(rail.GetPrim(), "safety_railing", {"standard": "OSHA guardrail 1.07m"})

    # ---- mezzanine office + stairs + railing (NW corner) ----
    mez = xform(stage, b+"/Mezzanine")
    cube(stage, b+"/Mezzanine/deck", 1.0, t=(-30,18,4.0), s=(18,12,0.3), mat=concrete)
    for i in range(6):   # facade glazing
        cube(stage, b+f"/Mezzanine/glass_{i}", 1.0, t=(-39+i*3,12.1,5.3), s=(2.6,0.05,2.2), mat=glass)
    cube(stage, b+"/Mezzanine/rail", 1.0, t=(-21.2,18,4.6), s=(0.06,12,0.9), mat=steel)
    for k in range(9):   # stair treads
        cube(stage, b+f"/Mezzanine/step_{k}", 1.0, t=(-21+0.0,10-k*0.32,0.45+k*0.42), s=(2.0,0.35,0.08), mat=steel)
    add_semantics(mez.GetPrim(), "mezzanine", {"use": "engineering_offices"})

    stage.GetRootLayer().Save()
    return path


# ---------------------------------------------------------------------------
# 3. LAYOUT  (5-station drone assembly line on the central spine)
# ---------------------------------------------------------------------------

STATIONS = [
    ("Station_01_FrameAssembly", -24, "Frame & chassis build (carbon-fiber arms, central plate)"),
    ("Station_02_AvionicsPCB",   -12, "Flight-controller / ESC PCB integration & wiring"),
    ("Station_03_Propulsion",      0, "Motor & propeller installation, balancing"),
    ("Station_04_PowerPayload",   12, "Battery + camera/gimbal payload integration"),
    ("Station_05_FinalQA_Flight", 24, "Final assembly, calibration & flight test"),
]

def _ref(stage, path, proto_prim, t=None, r=None, s=None, instanceable=True):
    p = xform(stage, path, t=t, r=r, s=s)
    p.GetPrim().GetReferences().AddReference("../assets/prototypes.usd", proto_prim)
    if instanceable:
        p.GetPrim().SetInstanceable(True)
    return p


def build_layout():
    path = os.path.join(LAYER_DIR, "layout.usd")
    stage = new_stage(path)
    root = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(root.GetPrim())
    line = xform(stage, "/World/ProductionLine")
    add_semantics(line.GetPrim(), "production_line",
                  {"product": FACILITY["product"], "takt_time_s": "420", "shifts": "2",
                   "annual_capacity_units": FACILITY["annual_capacity_units"]})

    for name, x, desc in STATIONS:
        s = xform(stage, f"/World/ProductionLine/{name}", t=(x,0,0))
        add_semantics(s.GetPrim(), "assembly_station", {"station_id": name, "description": desc})
        _ref(stage, f"/World/ProductionLine/{name}/Bench", "/Prototypes/Workstation", t=(0,1.9,0))
        _ref(stage, f"/World/ProductionLine/{name}/Robot", "/Prototypes/RobotArm", t=(0,3.2,0), r=(0,0,180))
        _ref(stage, f"/World/ProductionLine/{name}/Op_A", "/Prototypes/Operator", t=(-1.6,2.0,0), r=(0,0,-90))
        _ref(stage, f"/World/ProductionLine/{name}/WIP", "/Prototypes/Drone", t=(0,1.9,1.0), s=(0.95,0.95,0.95))

    _ref(stage, "/World/ProductionLine/Station_05_FinalQA_Flight/TestCage", "/Prototypes/TestCell", t=(0,7.5,0))
    # a drone hovering inside the test cage
    _ref(stage, "/World/ProductionLine/Station_05_FinalQA_Flight/HoverTest", "/Prototypes/Drone",
         t=(0,7.5,1.6), s=(0.95,0.95,0.95), instanceable=False)
    stage.GetRootLayer().Save()
    return path


# ---------------------------------------------------------------------------
# 4. EQUIPMENT  (conveyor spine, AMR fleet, warehouse & outbound racking)
# ---------------------------------------------------------------------------

def build_equipment():
    path = os.path.join(LAYER_DIR, "equipment.usd")
    stage = new_stage(path)
    root = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(root.GetPrim())

    conv = xform(stage, "/World/ConveyorSpine")
    add_semantics(conv.GetPrim(), "conveyor_system", {"length_m": "60", "type": "roller"})
    seg, x = 0, -30.0
    while x <= 30.0:
        _ref(stage, f"/World/ConveyorSpine/seg_{seg:02d}", "/Prototypes/ConveyorSegment", t=(x,0,0))
        if seg % 4 == 0:
            d = _ref(stage, f"/World/ConveyorSpine/wip_{seg:02d}", "/Prototypes/Drone",
                     t=(x,0,0.66), s=(0.9,0.9,0.9), instanceable=False)
            add_collider(d.GetPrim(), rigid=True, mass=2.4)
        x += 2.0; seg += 1

    fleet = xform(stage, "/World/AMRFleet")
    add_semantics(fleet.GetPrim(), "amr_fleet", {"count": "4", "fleet_manager": "MiR Fleet"})
    for i,(px,py,rz) in enumerate([(-33,-14,0),(-10,-14,0),(14,-14,180),(33,-7,90)]):
        _ref(stage, f"/World/AMRFleet/amr_{i}", "/Prototypes/AMR", t=(px,py,0), r=(0,0,rz))

    wh = xform(stage, "/World/Warehouse")
    add_semantics(wh.GetPrim(), "warehouse", {"zone": "inbound_receiving", "racks": "12"})
    for row in range(2):
        for col in range(6):
            _ref(stage, f"/World/Warehouse/rack_{row}_{col}", "/Prototypes/StorageRack",
                 t=(-34 + col*3.2, -20 + row*3.0, 0))

    out = xform(stage, "/World/Outbound")
    add_semantics(out.GetPrim(), "outbound_shipping", {"zone": "packing_and_dispatch", "dock_doors": "2"})
    for col in range(3):
        _ref(stage, f"/World/Outbound/rack_{col}", "/Prototypes/StorageRack", t=(32, 6 + col*3.2, 0))
    # pallets staged at the dock
    for i,py in enumerate((-7,7)):
        cube(stage, f"/World/Outbound/pallet_{i}", 1.0, t=(37,py,0.1), s=(1.2,1.0,0.15),
             color=(0.55,0.40,0.24))
    stage.GetRootLayer().Save()
    return path


# ---------------------------------------------------------------------------
# 5. LIGHTING
# ---------------------------------------------------------------------------

def build_lighting():
    path = os.path.join(LAYER_DIR, "lighting.usd")
    stage = new_stage(path)
    root = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(root.GetPrim())
    rig = xform(stage, "/World/Lighting")

    dome = UsdLux.DomeLight.Define(stage, "/World/Lighting/Sky")
    dome.CreateIntensityAttr(650.0); dome.CreateColorAttr(Gf.Vec3f(0.9,0.94,1.0))

    n = 0
    for gx in range(-30, 31, 12):
        for gy in range(-18, 19, 10):
            r = UsdLux.RectLight.Define(stage, f"/World/Lighting/highbay_{n}")
            r.AddTranslateOp().Set(Gf.Vec3d(gx, gy, 10.2))
            r.AddRotateXYZOp().Set(Gf.Vec3f(180,0,0))
            r.CreateWidthAttr(3.0); r.CreateHeightAttr(1.2)
            r.CreateIntensityAttr(11000.0); r.CreateColorAttr(Gf.Vec3f(1.0,0.98,0.92))
            n += 1
    key = UsdLux.SphereLight.Define(stage, "/World/Lighting/TestKey")
    key.AddTranslateOp().Set(Gf.Vec3d(24,7.5,6)); key.CreateRadiusAttr(0.5)
    key.CreateIntensityAttr(45000.0); key.CreateColorAttr(Gf.Vec3f(0.3,0.85,0.75))
    add_semantics(rig.GetPrim(), "lighting_rig", {"fixtures": str(n), "type": "LED_high_bay"})
    stage.GetRootLayer().Save()
    return path


# ---------------------------------------------------------------------------
# 6. SEMANTICS  (non-destructive overlay: plant-level metadata)
# ---------------------------------------------------------------------------

def build_semantics():
    path = os.path.join(LAYER_DIR, "semantics.usd")
    stage = new_stage(path)
    root = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(root.GetPrim())
    over = stage.OverridePrim("/World")
    over.SetCustomData({"aif:core": {
        "facility_name": FACILITY["facility_name"],
        "operator": FACILITY["operator"],
        "location": FACILITY["location"],
        "region": FACILITY["region"],
        "compliance": FACILITY["compliance"],
        "footprint_m2": FACILITY["footprint_m2"],
        "product": FACILITY["product"],
        "annual_capacity_units": FACILITY["annual_capacity_units"],
        "digital_twin_schema": "SimReady / aif:core v1",
        "twin_author": "Cowork + OpenUSD generator",
    }})
    stage.GetRootLayer().Save()
    return path


# ---------------------------------------------------------------------------
# ROOT interface layer  (sublayer stack)
# ---------------------------------------------------------------------------

def build_root():
    path = os.path.join(USD_DIR, "DroneFactory.usd")
    stage = new_stage(path)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    stage.GetRootLayer().subLayerPaths = [
        "./layers/semantics.usd", "./layers/lighting.usd", "./layers/equipment.usd",
        "./layers/layout.usd", "./layers/building.usd",
    ]
    stage.SetMetadata("comment",
        f"{FACILITY['facility_name']} - OpenUSD digital twin (layout & process visualization). "
        "Root interface layer; author into a dedicated session layer in Omniverse.")
    cam = UsdGeom.Camera.Define(stage, "/World/ReviewCamera")
    cam.AddTranslateOp().Set(Gf.Vec3d(0, -72, 44)); cam.AddRotateXYZOp().Set(Gf.Vec3f(58,0,0))
    cam.GetFocalLengthAttr().Set(24.0); cam.GetClippingRangeAttr().Set(Gf.Vec2f(0.1, 100000))
    stage.GetRootLayer().Save()
    return path


if __name__ == "__main__":
    print("prototypes :", build_prototypes())
    print("building   :", build_building())
    print("layout     :", build_layout())
    print("equipment  :", build_equipment())
    print("lighting   :", build_lighting())
    print("semantics  :", build_semantics())
    print("root       :", build_root())
    print("done.")
