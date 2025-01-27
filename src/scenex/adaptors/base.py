from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from psygnal import EmissionInfo

    from scenex import model


logger = logging.getLogger(__name__)

TNative = TypeVar("TNative")  # type representing a backend object
TModel = TypeVar("TModel", bound="model.EventedBase", covariant=True)
TNode = TypeVar("TNode", bound="model.Node", covariant=True)
TCamera = TypeVar("TCamera", bound="model.Camera", covariant=True)
TImage = TypeVar("TImage", bound="model.Image", covariant=True)
TPoints = TypeVar("TPoints", bound="model.Points", covariant=True)
TCanvas = TypeVar("TCanvas", bound="model.Canvas", covariant=True)
TView = TypeVar("TView", bound="model.View", covariant=True)


class Adaptor(ABC, Generic[TModel, TNative]):
    """ABC for backend adaptor classes.

    An adaptor converts model change events into into native calls for the given
    backend.
    """

    GETTER_METHOD = "_snx_get_{name}"
    SETTER_METHOD = "_snx_set_{name}"

    @abstractmethod
    def __init__(self, obj: TModel) -> None:
        """All backend adaptor objects receive the object they are adapting."""

    @abstractmethod
    def _snx_get_native(self) -> TNative:
        """Return the native object for the ."""

    def handle_event(self, info: EmissionInfo) -> None:
        """Receive info from psygnal callback and convert to adaptor call."""
        signal_name = info.signal.name

        try:
            name = self.SETTER_METHOD.format(name=signal_name)
            setter = getattr(self, name)
        except AttributeError as e:
            logger.exception(e)
            return

        event_name = f"{type(self).__name__}.{signal_name}"
        logger.debug(f"{event_name}={info.args} emitting to backend")

        try:
            setter(info.args[0])
        except Exception as e:
            logger.exception(e)


# --------------------------------------------------------------------------------
# NB: this whole thing could be replaced with a simple dynamic lookup.
# this is an experiment in type safety and IDE support.


class SupportsVisibility(Adaptor[TModel, TNative]):
    """Protocol for objects that support visibility (show/hide)."""

    @abstractmethod
    def _snx_set_visible(self, arg: bool) -> None:
        """Set the visibility of the object."""


class NodeAdaptor(SupportsVisibility[TNode, TNative]):
    """Backend interface for a Node."""

    @abstractmethod
    def _snx_set_name(self, arg: str) -> None: ...
    @abstractmethod
    def _snx_set_parent(self, arg: model.Node | None) -> None: ...
    # @abstractmethod
    # def _snx_set_children(self, arg: list[Node]) -> None: ...
    @abstractmethod
    def _snx_set_opacity(self, arg: float) -> None: ...
    @abstractmethod
    def _snx_set_order(self, arg: int) -> None: ...
    @abstractmethod
    def _snx_set_interactive(self, arg: bool) -> None: ...
    @abstractmethod
    def _snx_set_transform(self, arg: model.Transform) -> None: ...
    @abstractmethod
    def _snx_add_node(self, node: model.Node) -> None: ...

    @abstractmethod
    def _snx_block_updates(self) -> None:
        """Block future updates until `unblock_updates` is called."""

    @abstractmethod
    def _snx_unblock_updates(self) -> None:
        """Unblock updates after `block_updates` was called."""

    @abstractmethod
    def _snx_force_update(self) -> None:
        """Force an update to the node."""

    def _snx_set_node_type(self, arg: str) -> None:
        """Set the node type."""
        # this is a no-op, but is required for the serializer
        pass


class CameraAdaptor(NodeAdaptor[TCamera, TNative]):
    """Protocol for a backend camera adaptor object."""

    @abstractmethod
    def _snx_set_type(self, arg: model.CameraType) -> None: ...
    @abstractmethod
    def _snx_set_zoom(self, arg: float) -> None: ...
    @abstractmethod
    def _snx_set_center(self, arg: tuple[float, ...]) -> None: ...
    @abstractmethod
    def _snx_set_range(self, margin: float) -> None: ...


class ImageAdaptor(NodeAdaptor[TImage, TNative]):
    """Protocol for a backend Image adaptor object."""

    @abstractmethod
    def _snx_set_data(self, arg: NDArray) -> None: ...
    @abstractmethod
    def _snx_set_cmap(self, arg: model.Colormap) -> None: ...
    @abstractmethod
    def _snx_set_clims(self, arg: tuple[float, float] | None) -> None: ...
    @abstractmethod
    def _snx_set_gamma(self, arg: float) -> None: ...
    @abstractmethod
    def _snx_set_interpolation(self, arg: model.InterpolationMode) -> None: ...


class PointsAdaptor(NodeAdaptor[TPoints, TNative]):
    """Protocol for a backend Image adaptor object."""

    @abstractmethod
    def _snx_set_coords(self, coords: NDArray) -> None: ...
    @abstractmethod
    def _snx_set_size(self, size: float) -> None: ...
    @abstractmethod
    def _snx_set_face_color(self, face_color: model.Color) -> None: ...
    @abstractmethod
    def _snx_set_edge_color(self, edge_color: model.Color) -> None: ...
    @abstractmethod
    def _snx_set_edge_width(self, edge_width: float) -> None: ...
    @abstractmethod
    def _snx_set_symbol(self, symbol: str) -> None: ...
    @abstractmethod
    def _snx_set_scaling(self, scaling: str) -> None: ...
    @abstractmethod
    def _snx_set_antialias(self, antialias: float) -> None: ...


class CanvasAdaptor(SupportsVisibility[TCanvas, TNative]):
    """Protocol defining the interface for a Canvas adaptor."""

    @abstractmethod
    def _snx_set_width(self, arg: int) -> None: ...
    @abstractmethod
    def _snx_set_height(self, arg: int) -> None: ...
    @abstractmethod
    def _snx_set_background_color(self, arg: model.Color | None) -> None: ...
    @abstractmethod
    def _snx_set_title(self, arg: str) -> None: ...
    @abstractmethod
    def _snx_close(self) -> None: ...
    @abstractmethod
    def _snx_render(self) -> NDArray: ...
    @abstractmethod
    def _snx_add_view(self, view: model.View) -> None: ...

    def _snx_set_views(self, views: list[model.View]) -> None:
        pass

    def _snx_get_ipython_mimebundle(
        self, *args: Any, **kwargs: Any
    ) -> dict | tuple[dict, dict] | Any:
        return NotImplemented


# TODO: decide whether all the layout stuff goes here...


class ViewAdaptor(SupportsVisibility[TView, TNative]):
    """Protocol defining the interface for a View adaptor."""

    @abstractmethod
    def _snx_set_blending(self, arg: model.BlendMode) -> None: ...
    @abstractmethod
    def _snx_set_camera(self, arg: model.Camera) -> None: ...
    @abstractmethod
    def _snx_set_scene(self, arg: model.Scene) -> None: ...
    @abstractmethod
    def _snx_set_position(self, arg: tuple[float, float]) -> None: ...
    @abstractmethod
    def _snx_set_size(self, arg: tuple[float, float] | None) -> None: ...
    @abstractmethod
    def _snx_set_background_color(self, arg: model.Color | None) -> None: ...
    @abstractmethod
    def _snx_set_border_width(self, arg: float) -> None: ...
    @abstractmethod
    def _snx_set_border_color(self, arg: model.Color | None) -> None: ...
    @abstractmethod
    def _snx_set_padding(self, arg: int) -> None: ...
    @abstractmethod
    def _snx_set_margin(self, arg: int) -> None: ...

    def _snx_set_layout(self, arg: model.Layout) -> None:
        pass
