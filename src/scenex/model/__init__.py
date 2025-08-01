"""Model module for SceneX."""

from cmap import Color, Colormap  # re-export

from ._base import EventedBase, objects
from .canvas import Canvas
from .layout import Layout
from .nodes.camera import Camera, CameraType
from .nodes.image import Image, InterpolationMode
from .nodes.node import AnyNode, Node
from .nodes.points import Points, ScalingMode, SymbolName
from .nodes.scene import Scene
from .transform import Transform
from .view import BlendMode, View

__all__ = [
    "AnyNode",
    "BlendMode",
    "Camera",
    "CameraType",
    "Canvas",
    "Color",
    "Colormap",
    "EventedBase",
    "Image",
    "InterpolationMode",
    "Layout",
    "Node",
    "Points",
    "ScalingMode",
    "Scene",
    "SymbolName",
    "Transform",
    "View",
    "objects",
]

for obj in list(globals().values()):
    if isinstance(obj, type) and issubclass(obj, EventedBase):
        obj.__module__ = __name__
        obj.model_rebuild()
