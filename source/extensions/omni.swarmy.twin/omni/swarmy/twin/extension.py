"""
Swarmy Factory Twin — Omniverse Kit extension.

On startup it opens the OpenUSD digital twin of Swarmy's North Georgia Plant,
frames the review camera, and adds a "Swarmy Twin" menu with actions for:
  * Open / reload the twin stage
  * Toggle the production-line process animation (drones flowing along the conveyor)
  * Highlight a selected assembly station and print its aif:core semantics

Dependency-light so it runs in a stock Kit viewport app on a local RTX
workstation (USD Composer, or the bundled swarmy.twin.kit app).
"""
import os
import carb
import omni.ext
import omni.usd
import omni.kit.menu.utils as menu_utils
from omni.kit.menu.utils import MenuItemDescription

try:
    from omni.kit.viewport.utility import get_active_viewport
except Exception:  # pragma: no cover - viewport optional in tests
    get_active_viewport = None

from pxr import UsdGeom, Gf

EXT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DEFAULT_STAGE = os.path.join(EXT_ROOT, "usd", "DroneFactory.usd")

# X positions (meters) of the five stations along the conveyor spine.
STATION_X = [-24.0, -12.0, 0.0, 12.0, 24.0]


class SwarmyTwinExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str):
        carb.log_info("[omni.swarmy.twin] startup")
        self._ext_id = ext_id
        self._animating = False
        self._sub = None

        settings = carb.settings.get_settings()
        self._stage_path = settings.get("exts/omni.swarmy.twin/stage_path") or DEFAULT_STAGE
        if not os.path.isabs(self._stage_path):
            self._stage_path = os.path.normpath(os.path.join(EXT_ROOT, self._stage_path))

        self._build_menu()
        self.open_twin()

    def on_shutdown(self):
        carb.log_info("[omni.swarmy.twin] shutdown")
        self._stop_animation()
        menu_utils.remove_menu_items(self._menu, "Swarmy Twin")

    # ------------------------------------------------------------------ menu
    def _build_menu(self):
        self._menu = [
            MenuItemDescription(name="Open / Reload Twin", onclick_fn=lambda: self.open_twin()),
            MenuItemDescription(name="Toggle Process Animation", onclick_fn=lambda: self.toggle_animation()),
            MenuItemDescription(name="Frame Review Camera", onclick_fn=lambda: self._frame_camera()),
            MenuItemDescription(name="Print Selected Semantics", onclick_fn=lambda: self.print_selected_semantics()),
        ]
        menu_utils.add_menu_items(self._menu, "Swarmy Twin")

    # ------------------------------------------------------------------ stage
    def open_twin(self):
        if not os.path.exists(self._stage_path):
            carb.log_error(f"[swarmy] twin stage not found: {self._stage_path}")
            return
        omni.usd.get_context().open_stage(self._stage_path)
        carb.log_info(f"[swarmy] opened {self._stage_path}")
        self._frame_camera()

    def _frame_camera(self):
        if get_active_viewport is None:
            return
        vp = get_active_viewport()
        stage = omni.usd.get_context().get_stage()
        if stage and stage.GetPrimAtPath("/World/ReviewCamera"):
            try:
                vp.camera_path = "/World/ReviewCamera"
            except Exception as e:
                carb.log_warn(f"[swarmy] could not set camera: {e}")

    # ------------------------------------------------------------- animation
    def toggle_animation(self):
        if self._animating:
            self._stop_animation()
        else:
            self._start_animation()

    def _start_animation(self):
        import omni.kit.app
        self._animating = True
        app = omni.kit.app.get_app()
        self._sub = app.get_update_event_stream().create_subscription_to_pop(
            self._on_update, name="swarmy_flow")
        carb.log_info("[swarmy] process animation ON")

    def _stop_animation(self):
        self._animating = False
        self._sub = None

    def _on_update(self, e):
        """Advance every conveyor-borne drone along +X, wrapping at the outbound end."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return
        dt = e.payload.get("dt", 1 / 60.0) if hasattr(e, "payload") else 1 / 60.0
        speed = 2.0  # m/s visualization speed
        for prim in stage.Traverse():
            if not prim.GetName().startswith("wip_"):
                continue
            xf = UsdGeom.Xformable(prim)
            for op in xf.GetOrderedXformOps():
                if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                    v = op.Get()
                    if v is None:
                        continue
                    nx = v[0] + speed * dt
                    if nx > 32.0:
                        nx = -30.0
                    op.Set(Gf.Vec3d(nx, v[1], v[2]))
                    break

    # ------------------------------------------------------------- semantics
    def print_selected_semantics(self):
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        paths = ctx.get_selection().get_selected_prim_paths()
        if not paths:
            carb.log_warn("[swarmy] nothing selected")
            return
        for p in paths:
            prim = stage.GetPrimAtPath(p)
            if not prim:
                continue
            cls = prim.GetAttribute("semantic:class")
            cd = prim.GetCustomData().get("aif:core", {})
            carb.log_info(f"[swarmy] {p}  class={cls.Get() if cls else None}  aif:core={cd}")
