"""View model and controller classes."""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import Field, PrivateAttr, computed_field

from ._base import EventedModel, SupportsVisibility
from .layout import Layout
from .nodes.camera import Camera
from .nodes.scene import Scene

if TYPE_CHECKING:
    from cmap import Color

    from .canvas import Canvas

logger = logging.getLogger(__name__)


class View(EventedModel):
    """A rectangular area on a canvas that displays a scene, with a camera.

    A canvas can have one or more views. Each view has a single scene (i.e. a
    scene graph of nodes) and a single camera. The camera defines the view
    transformation.  This class just exists to associate a single scene and
    camera.
    """

    scene: Scene = Field(default_factory=Scene)
    camera: Camera = Field(default_factory=Camera)
    layout: Layout = Field(default_factory=Layout, frozen=True)

    visible: bool = Field(default=True, description="Whether the view is visible.")

    _canvas: Canvas | None = PrivateAttr(None)

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook for the model."""
        super().model_post_init(__context)
        self.camera.parent = self.scene

    @computed_field  # type: ignore
    @property
    def canvas(self) -> Canvas:
        """The canvas that the view is on.

        If one hasn't been created/assigned, a new one is created.
        """
        if (canvas := self._canvas) is None:
            from .canvas import Canvas

            self.canvas = canvas = Canvas()
        return canvas

    @canvas.setter
    def canvas(self, value: Canvas) -> None:
        self._canvas = value
        self._canvas.views.append(self)

    def show(self) -> Canvas:
        """Show the view.

        Convenience method for showing the canvas that the view is on.
        If no canvas exists, a new one is created.
        """
        canvas = self.canvas
        canvas.show()
        return self.canvas


# -------------------- Controller ABC --------------------

_VT = TypeVar("_VT", bound="View", covariant=True)

# TODO: decide whether all the layout stuff goes here...


class ViewController(SupportsVisibility[_VT]):
    """Protocol defining the interface for a View adaptor."""

    @abstractmethod
    def _vis_set_camera(self, arg: Camera) -> None: ...
    @abstractmethod
    def _vis_set_scene(self, arg: Scene) -> None: ...
    @abstractmethod
    def _vis_set_position(self, arg: tuple[float, float]) -> None: ...
    @abstractmethod
    def _vis_set_size(self, arg: tuple[float, float] | None) -> None: ...
    @abstractmethod
    def _vis_set_background_color(self, arg: Color | None) -> None: ...
    @abstractmethod
    def _vis_set_border_width(self, arg: float) -> None: ...
    @abstractmethod
    def _vis_set_border_color(self, arg: Color | None) -> None: ...
    @abstractmethod
    def _vis_set_padding(self, arg: int) -> None: ...
    @abstractmethod
    def _vis_set_margin(self, arg: int) -> None: ...

    def _vis_set_layout(self, arg: Layout) -> None:
        pass
