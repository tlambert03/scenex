from __future__ import annotations

import contextlib
import logging
import sys
from functools import cache
from typing import TYPE_CHECKING, Any, TypeVar, overload

from scenex import model as models
from scenex.model import adaptor_base as adpt

if TYPE_CHECKING:
    from collections.abc import Iterator

    from scenex import model
    from scenex.model._base import EventedBase

_M = TypeVar("_M", bound="model.EventedBase")


class AdaptorRegistry:
    """Weak registry for Adaptor objects.

    Each backend should subclass this and implement the `get_adaptor_class` method.
    And expose an instance of the subclass as `adaptors` in the top level of the backend
    module.
    """

    def __init__(self) -> None:
        self._objects: dict[str, adpt.Adaptor] = {}

    def all(self) -> Iterator[adpt.Adaptor]:
        """Return an iterator over all adaptors in the registry."""
        yield from self._objects.values()

    # TODO: see if this can be done better with typevars.
    # (it doesn't appear to be trivial)
    @overload
    def get_adaptor(self, obj: model.Points) -> adpt.PointsAdaptor: ...
    @overload
    def get_adaptor(self, obj: model.Image) -> adpt.ImageAdaptor: ...
    @overload
    def get_adaptor(self, obj: model.Camera) -> adpt.CameraAdaptor: ...
    @overload
    def get_adaptor(self, obj: model.Scene) -> adpt.NodeAdaptor: ...
    @overload
    def get_adaptor(self, obj: model.View) -> adpt.ViewAdaptor: ...
    @overload
    def get_adaptor(self, obj: model.Canvas) -> adpt.CanvasAdaptor: ...
    @overload
    def get_adaptor(self, obj: model.EventedBase) -> adpt.Adaptor: ...
    def get_adaptor(self, obj: _M, create: bool = True) -> adpt.Adaptor[_M, Any]:
        """Get the adaptor for the given model object, create if `create` is True."""
        if obj._model_id.hex not in self._objects:
            if not create:
                raise KeyError(f"No adaptor found for {obj!r}, and create=False")
            self._objects[obj._model_id.hex] = adaptor = self.create_adaptor(obj)
            self.initialize_adaptor(obj, adaptor)
        return self._objects[obj._model_id.hex]

    def initialize_adaptor(self, model: _M, adaptor: adpt.Adaptor) -> None:
        """Initialize the adaptor for the given model object."""
        sync_adaptor(adaptor, model)
        model.events.connect(adaptor.handle_event)

        if isinstance(model, models.Canvas):
            for view in model.views:
                self.get_adaptor(view)
        if isinstance(model, models.View):
            self.get_adaptor(model.scene)
        if isinstance(model, models.Node):
            for child in model.children:
                self.get_adaptor(child)

    def get_adaptor_class(self, obj: _M) -> type[adpt.Adaptor]:
        """Return the adaptor class for the given model object."""
        cls = type(self)
        cls_module = sys.modules[cls.__module__]
        cls_file = cls_module.__file__
        raise NotImplementedError(
            f"{cls.__name__}.get_adaptor_class not implemented in {cls_file}"
        )

    @classmethod
    def validate_adaptor_class(cls, obj: _M, adaptor_cls: type[adpt.Adaptor]) -> None:
        """Validate that the given class is a valid adaptor for the given object."""
        return _validate_adaptor_class(type(obj), adaptor_cls)

    def create_adaptor(self, model: _M) -> adpt.Adaptor[_M, Any]:
        """Create a new adaptor for the given model object."""
        adaptor_cls: type[adpt.Adaptor] = self.get_adaptor_class(model)
        self.validate_adaptor_class(model, adaptor_cls)
        adaptor = adaptor_cls(model)

        return adaptor


def _update_blocker(adaptor: adpt.Adaptor) -> contextlib.AbstractContextManager:
    if isinstance(adaptor, adpt.NodeAdaptor):

        @contextlib.contextmanager
        def blocker() -> Iterator[None]:
            adaptor._snx_block_updates()
            try:
                yield
            finally:
                adaptor._snx_unblock_updates()

        return blocker()
    return contextlib.nullcontext()


def sync_adaptor(adaptor: adpt.Adaptor, model: EventedBase) -> None:
    """Decorator to validate and cache adaptor classes."""
    with _update_blocker(adaptor):
        for field_name in model.model_fields:
            method_name = adaptor.SETTER_METHOD.format(name=field_name)
            value = getattr(model, field_name)
            try:
                vis_set = getattr(adaptor, method_name)
                vis_set(value)
            except Exception as e:
                logging.warning(
                    "Failed to set field %r on adaptor %r: %s", field_name, adaptor, e
                )
    force_update = getattr(adaptor, "_snx_force_update", lambda: None)
    force_update()


@cache
def _validate_adaptor_class(
    obj_type: type[_M], adaptor_cls: type[adpt.Adaptor]
) -> None:
    if not isinstance(adaptor_cls, type) and issubclass(adaptor_cls, adpt.Adaptor):
        raise TypeError(f"Expected an Adaptor class, got {adaptor_cls!r}")
    # TODO
