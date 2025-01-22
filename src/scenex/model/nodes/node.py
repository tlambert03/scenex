from __future__ import annotations

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, Union, cast

from pydantic import Field, SerializerFunctionWrapHandler, model_serializer

from scenex.model._base import EventedModel, SupportsVisibility
from scenex.model._evented_list import EventedList
from scenex.model.transform import Transform

if TYPE_CHECKING:
    from collections.abc import Iterator


logger = logging.getLogger(__name__)


# improve me... Read up on: https://docs.pydantic.dev/latest/concepts/unions/
AnyNode = Annotated[
    Union["Image", "Scene", "Points", "Camera"], Field(discriminator="node_type")
]


class Node(EventedModel):
    """Base class for all nodes.  Also a `Container[Node]`.

    Do not instantiate this class directly. Use a subclass.  GenericNode may
    be used in place of Node.
    """

    name: str | None = Field(default=None, description="Name of the node.")
    parent: AnyNode | None = Field(
        default=None,
        description="Parent node. If None, this node is a root node.",
        exclude=True,  # prevents recursion in serialization.
        repr=False,  # recursion is just confusing
        # TODO: maybe make children the derived field?
    )

    children: EventedList[AnyNode] = Field(default_factory=EventedList, frozen=True)
    visible: bool = Field(default=True, description="Whether this node is visible.")
    interactive: bool = Field(
        default=False, description="Whether this node accepts mouse and touch events"
    )
    opacity: float = Field(default=1.0, ge=0, le=1, description="Opacity of this node.")
    order: int = Field(
        default=0,
        ge=0,
        description="A value used to determine the order in which nodes are drawn. "
        "Greater values are drawn later. Children are always drawn after their parent",
    )
    transform: Transform = Field(
        default_factory=Transform,
        description="Transform that maps the local coordinate frame to the coordinate "
        "frame of the parent.",
    )

    # -----------------------------

    @model_serializer(mode="wrap")
    def _serialize_withnode_type(self, handler: SerializerFunctionWrapHandler) -> Any:
        # modified serializer that ensures node_type is included,
        # (e.g. even if exclude_defaults=True)
        data = handler(self)
        if node_type := getattr(self, "node_type", None):
            data["node_type"] = node_type
        return data

    # prevent direct instantiation.
    # makes it easier to use NodeUnion without having to deal with self-reference.
    def __init__(self, /, **data: Any) -> None:
        if type(self) is Node:
            raise TypeError("Node cannot be instantiated directly. Use a subclass.")
        super().__init__(**data)

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook for the model."""
        super().model_post_init(__context)
        # ensure parent is set on children
        for child in self.children:
            child.parent = cast("AnyNode", self)
        self.children.item_inserted.connect(self._on_child_inserted)

    def _on_child_inserted(self, index: int, obj: Node) -> None:
        # ensure parent is set
        self.add(obj)

    def __contains__(self, item: object) -> bool:
        """Return True if this node is an ancestor of item."""
        return item in self.children

    def add(self, node: Node) -> None:
        """Add a child node."""
        node = cast("AnyNode", node)
        node.parent = cast("AnyNode", self)
        if node not in self.children:
            logger.debug("Adding node %r to %r", node, self)
            self.children.append(node)

    # below borrowed from vispy.scene.Node

    def transform_to_node(self, other: Node) -> Transform:
        """Return Transform that maps from coordinate frame of `self` to `other`.

        Note that there must be a _single_ path in the scenegraph that connects
        the two entities; otherwise an exception will be raised.

        Parameters
        ----------
        other : instance of Node
            The other node.

        Returns
        -------
        transform : instance of ChainTransform
            The transform.
        """
        a, b = self.path_to_node(other)
        tforms = [n.transform for n in a[:-1]] + [n.transform.inv() for n in b]
        return Transform.chain(*tforms[::-1])

    def path_to_node(self, other: Node) -> tuple[list[Node], list[Node]]:
        """Return two lists describing the path from this node to another.

        Parameters
        ----------
        other : instance of Node
            The other node.

        Returns
        -------
        p1 : list
            First path (see below).
        p2 : list
            Second path (see below).

        Notes
        -----
        The first list starts with this node and ends with the common parent
        between the endpoint nodes. The second list contains the remainder of
        the path from the common parent to the specified ending node.

        For example, consider the following scenegraph::

            A --- B --- C --- D
                   \
                    --- E --- F

        Calling `D.node_path(F)` will return::

            ([D, C, B], [E, F])

        """
        my_parents = list(self.iter_parents())
        their_parents = list(other.iter_parents())
        common_parent = next((p for p in my_parents if p in their_parents), None)
        if common_parent is None:
            slf = f"{self.__class__.__name__} {id(self)}"
            nd = f"{other.__class__.__name__} {id(other)}"
            raise RuntimeError(f"No common parent between nodes {slf} and {nd}.")

        up = my_parents[: my_parents.index(common_parent) + 1]
        down = their_parents[: their_parents.index(common_parent)][::-1]
        return (up, down)

    def iter_parents(self) -> Iterator[Node]:
        """Return list of parents starting from this node.

        The chain ends at the first node with no parents.
        """
        yield self

        x = cast("AnyNode", self)
        while True:
            try:
                parent = x.parent
            except Exception:
                break
            if parent is None:
                break
            yield parent
            x = parent


# -------------------- Controller ABC --------------------

_NT = TypeVar("_NT", bound="Node", covariant=True)


class NodeAdaptor(SupportsVisibility[_NT]):
    """Backend interface for a Node."""

    @abstractmethod
    def _vis_set_name(self, arg: str) -> None: ...
    @abstractmethod
    def _vis_set_parent(self, arg: Node | None) -> None: ...
    @abstractmethod
    def _vis_set_children(self, arg: list[Node]) -> None: ...
    @abstractmethod
    def _vis_set_opacity(self, arg: float) -> None: ...
    @abstractmethod
    def _vis_set_order(self, arg: int) -> None: ...
    @abstractmethod
    def _vis_set_interactive(self, arg: bool) -> None: ...
    @abstractmethod
    def _vis_set_transform(self, arg: Transform) -> None: ...
    @abstractmethod
    def _vis_add_node(self, node: Node) -> None: ...

    @abstractmethod
    def _vis_block_updates(self) -> None:
        """Block future updates until `unblock_updates` is called."""

    @abstractmethod
    def _vis_unblock_updates(self) -> None:
        """Unblock updates after `block_updates` was called."""

    @abstractmethod
    def _vis_force_update(self) -> None:
        """Force an update to the node."""


# imports needed to resolve recursive AnyNode type
from .camera import Camera  # noqa: E402, TC001
from .image import Image  # noqa: E402, TC001
from .points import Points  # noqa: E402, TC001
from .scene import Scene  # noqa: E402, TC001

Node.model_rebuild()
