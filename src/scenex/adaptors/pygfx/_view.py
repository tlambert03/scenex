from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, cast

import pygfx

from scenex.adaptors.base import ViewAdaptor

from ._adaptor_registry import get_adaptor

if TYPE_CHECKING:
    from cmap import Color

    from scenex import model

    from . import _camera, _canvas, _scene


BLENDING_MAP = {
    "default": "default",
    "opaque": "opaque",
    "alpha": "ordered1",
    "additive": "additive",
}


class View(ViewAdaptor):
    """View interface for pygfx Backend.

    A view combines a scene and a camera to render a scene (onto a canvas).
    """

    _pygfx_scene: pygfx.Scene
    _pygfx_cam: pygfx.Camera

    def __init__(self, view: model.View, **backend_kwargs: Any) -> None:
        canvas_adaptor = cast("_canvas.Canvas", get_adaptor(view.canvas))
        wgpu_canvas = canvas_adaptor._snx_get_native()
        self._renderer = pygfx.renderers.WgpuRenderer(wgpu_canvas)

        self._snx_set_scene(view.scene)
        self._snx_set_camera(view.camera)
        self._snx_set_blending(view.blending)

    def _snx_get_native(self) -> pygfx.Viewport:
        return pygfx.Viewport(self._renderer)

    def _snx_set_blending(self, arg: model.BlendMode) -> None:
        self._renderer.blend_mode = BLENDING_MAP.get(arg, "default")

    def _snx_set_visible(self, arg: bool) -> None:
        pass

    def _snx_set_scene(self, scene: model.Scene) -> None:
        self._scene_adaptor = cast("_scene.Scene", get_adaptor(scene))
        self._pygfx_scene = self._scene_adaptor._pygfx_node

    def _snx_set_camera(self, cam: model.Camera) -> None:
        self._cam_adaptor = cast("_camera.Camera", get_adaptor(cam))
        self._pygfx_cam = self._cam_adaptor._pygfx_node
        self._cam_adaptor.pygfx_controller.register_events(self._renderer)

    def _draw(self) -> None:
        renderer = self._renderer
        renderer.render(self._pygfx_scene, self._pygfx_cam)
        renderer.request_draw()

    def _snx_set_position(self, arg: tuple[float, float]) -> None:
        warnings.warn(
            "set_position not implemented for pygfx", RuntimeWarning, stacklevel=2
        )

    def _snx_set_size(self, arg: tuple[float, float] | None) -> None:
        warnings.warn(
            "set_size not implemented for pygfx", RuntimeWarning, stacklevel=2
        )

    def _snx_set_background_color(self, color: Color | None) -> None:
        colors = (color.rgba,) if color is not None else ()
        background = pygfx.Background(None, material=pygfx.BackgroundMaterial(*colors))
        self._pygfx_scene.add(background)

    def _snx_set_border_width(self, arg: float) -> None:
        warnings.warn(
            "set_border_width not implemented for pygfx", RuntimeWarning, stacklevel=2
        )

    def _snx_set_border_color(self, arg: Color | None) -> None:
        warnings.warn(
            "set_border_color not implemented for pygfx", RuntimeWarning, stacklevel=2
        )

    def _snx_set_padding(self, arg: int) -> None:
        warnings.warn(
            "set_padding not implemented for pygfx", RuntimeWarning, stacklevel=2
        )

    def _snx_set_margin(self, arg: int) -> None:
        warnings.warn(
            "set_margin not implemented for pygfx", RuntimeWarning, stacklevel=2
        )
