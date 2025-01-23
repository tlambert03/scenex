from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from scenex.model import adaptor_base

from ._adaptor_registry import adaptors

if TYPE_CHECKING:
    import numpy as np
    from cmap import Color
    from rendercanvas.auto import RenderCanvas

    from scenex import model

    from ._view import View


class Canvas(adaptor_base.CanvasAdaptor):
    """Canvas interface for pygfx Backend."""

    def __init__(self, canvas: model.Canvas, **backend_kwargs: Any) -> None:
        from rendercanvas.auto import RenderCanvas

        self._wgpu_canvas = RenderCanvas()
        # Qt RenderCanvas calls show() in its __init__ method, so we need to hide it
        if hasattr(self._wgpu_canvas, "hide"):
            self._wgpu_canvas.hide()

        self._wgpu_canvas.set_logical_size(canvas.width, canvas.height)
        self._wgpu_canvas.set_title(canvas.title)
        self._views = canvas.views

    def _snx_get_native(self) -> RenderCanvas:
        return self._wgpu_canvas

    def _snx_set_visible(self, arg: bool) -> None:
        # show the qt canvas we patched earlier in __init__
        if hasattr(self._wgpu_canvas, "show"):
            self._wgpu_canvas.show()
        self._wgpu_canvas.request_draw(self._draw)

    def _draw(self) -> None:
        for view in self._views:
            adaptor = cast("View", adaptors.get_adaptor(view))
            adaptor._draw()

    def _snx_add_view(self, view: model.View) -> None:
        pass
        # adaptor = cast("View", view.backend_adaptor())
        # adaptor._pygfx_cam.set_viewport(self._viewport)
        # self._views.append(adaptor)

    def _snx_set_width(self, arg: int) -> None:
        _, height = self._wgpu_canvas.get_logical_size()
        self._wgpu_canvas.set_logical_size(arg, height)

    def _snx_set_height(self, arg: int) -> None:
        width, _ = self._wgpu_canvas.get_logical_size()
        self._wgpu_canvas.set_logical_size(width, arg)

    def _snx_set_background_color(self, arg: Color | None) -> None:
        # not sure if pygfx has both a canavs and view background color...
        pass

    def _snx_set_title(self, arg: str) -> None:
        self._wgpu_canvas.set_title(arg)

    def _snx_close(self) -> None:
        """Close canvas."""
        self._wgpu_canvas.close()

    def _snx_render(
        self,
        region: tuple[int, int, int, int] | None = None,
        size: tuple[int, int] | None = None,
        bgcolor: Color | None = None,
        crop: np.ndarray | tuple[int, int, int, int] | None = None,
        alpha: bool = True,
    ) -> np.ndarray:
        """Render to screenshot."""
        from rendercanvas.offscreen import OffscreenRenderCanvas

        # not sure about this...
        w, h = self._wgpu_canvas.get_logical_size()
        canvas = OffscreenRenderCanvas(width=w, height=h, pixel_ratio=1)
        canvas.request_draw(self._draw)
        return cast("np.ndarray", canvas.draw())
