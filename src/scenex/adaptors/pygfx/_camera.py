from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pygfx

from scenex.adaptors.base import CameraAdaptor

from ._adaptor_registry import get_adaptor
from ._node import Node

if TYPE_CHECKING:
    from scenex import model


class Camera(Node, CameraAdaptor):
    """Adaptor for pygfx camera."""

    _pygfx_node: pygfx.PerspectiveCamera
    pygfx_controller: pygfx.Controller

    def __init__(self, camera: model.Camera, **backend_kwargs: Any) -> None:
        self._camera_model = camera
        if camera.type == "panzoom":
            self._pygfx_node = pygfx.OrthographicCamera()
            self.pygfx_controller = pygfx.PanZoomController(self._pygfx_node)
        elif camera.type == "perspective":
            # this type ignore is because PerspectiveCamera lacks hints
            self._pygfx_node = pygfx.PerspectiveCamera(70, 4 / 3)  # pyright: ignore reportArgumentType]
            self.pygfx_controller = pygfx.OrbitController(self._pygfx_node)

        self._pygfx_node.local.scale_y = -1  # don't think this is working...
        self._snx_set_range(0.1)

    def _snx_set_zoom(self, zoom: float) -> None:
        raise NotImplementedError

    def _snx_set_center(self, arg: tuple[float, ...]) -> None:
        raise NotImplementedError

    def _snx_set_type(self, arg: model.CameraType) -> None:
        raise NotImplementedError

    def _view_size(self) -> tuple[float, float] | None:
        """Return the size of first parent viewbox in pixels."""
        raise NotImplementedError

    def update_controller(self) -> None:
        # This is called by the View Adaptor in the `_visit` method
        # ... which is in turn called by the Canvas backend adaptor's `_animate` method
        # i.e. the main render loop.
        self.pygfx_controller.update_camera(self._pygfx_node)

    def set_viewport(self, viewport: pygfx.Viewport) -> None:
        # This is used by the Canvas backend adaptor...
        # and should perhaps be moved to the View Adaptor
        self.pygfx_controller.add_default_event_handlers(viewport, self._pygfx_node)

    def _snx_set_range(self, margin: float) -> None:
        # reset camera to fit all objects
        if not (scene := self._camera_model.parent):
            print("No scene found for camera")
            return

        gfx_scene = cast("pygfx.Scene", get_adaptor(scene)._snx_get_native())
        cam = self._pygfx_node
        cam.show_object(gfx_scene)

        if (bb := gfx_scene.get_world_bounding_box()) is not None:
            width, height, _depth = np.ptp(bb, axis=0)
            if width < 0.01:
                width = 1
            if height < 0.01:
                height = 1
            cam.width = width
            cam.height = height
        cam.zoom = 1 - margin
