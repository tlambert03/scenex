from __future__ import annotations

from typing import Any

import numpy as np
import pytest

import scenex as snx

EXPECT_REPR = """
Scene
    ├── Image
    ├── Image
    ├── Points
    └── Camera
""".strip()


def _obj_name(obj: Any) -> str:
    # normalize all cameras to "Camera"
    if "camera" in (name := f"{obj.__class__.__name__}").lower():
        return "Camera"
    return name


def _child_names(obj: Any) -> list[str]:
    """Get the names of the children of a obj."""
    return [_obj_name(child) for child in obj.children]


def test_basic_view(basic_view: snx.View) -> None:
    snx.show(basic_view)
    assert isinstance(repr(basic_view), str)
    assert isinstance(basic_view.model_dump(), dict)
    assert isinstance(basic_view.model_dump_json(), str)
    assert snx.util.tree_repr(basic_view.scene, node_repr=_obj_name) == EXPECT_REPR
    ary = basic_view.render()
    assert isinstance(ary, np.ndarray)


@pytest.mark.parametrize("backend", ["pygfx"])
def test_view_tree_matches_native(basic_view: snx.View, backend: str) -> None:
    """Test that the structure of the tree generated by the model matches the
    structure of the tree generated by the native backend."""
    basic_view._get_adaptor(backend=backend, create=True)

    model_tree = snx.util.tree_dict(basic_view.scene, obj_name=_obj_name)
    native_scene = basic_view.scene._get_native(backend=backend)
    view_tree = snx.util.tree_dict(native_scene, obj_name=_obj_name)
    assert isinstance(view_tree, dict)
    assert model_tree == view_tree


@pytest.mark.parametrize("backend", ["pygfx"])
def test_changing_parent_updates_adaptor(backend: str) -> None:
    """Test that changing the parent of a model object works, and emits events."""
    # create a scene and a view
    scene1 = snx.Scene()
    scene2 = snx.Scene()
    img1 = snx.Image(data=np.random.randint(0, 255, (10, 10), dtype=np.uint8))
    img2 = snx.Image(data=np.random.randint(0, 255, (10, 10), dtype=np.uint8))

    scene1_native = scene1._get_native(backend=backend, create=True)
    scene2_native = scene2._get_native(backend=backend, create=True)

    # nothing is in any scene yet
    assert "Image" not in {_obj_name(x) for x in scene2_native.children}
    assert "Image" not in {_obj_name(x) for x in scene1_native.children}

    # set img1's parent to scene1
    img1.parent = scene1
    # this should add img1 to scene1's children
    assert img1.parent is scene1
    assert img1 in scene1.children
    # make sure the native scene has updated as well
    assert "Image" in _child_names(scene1_native)

    # set img2's parent to scene2
    scene2.add_child(img2)
    assert img2.parent is scene2
    assert img2 in scene2.children
    # make sure the native scene has updated as well
    assert "Image" in _child_names(scene2_native)

    # move img1 to scene2
    scene2.add_child(img1)
    assert img1.parent is scene2
    assert img1 in scene2.children
    assert img1 not in scene1.children
    # make sure the native scene has updated as well
    assert _child_names(scene1_native).count("Image") == 0
    assert _child_names(scene2_native).count("Image") == 2

    scene2.remove_child(img2)
    assert img2.parent is None
    assert img2 not in scene2.children
    # make sure the native scene has updated as well
    assert _child_names(scene2_native).count("Image") == 1

    # manually set img1.parent to None
    img1.parent = None
    assert img1.parent is None
    assert img1 not in scene2.children
    # make sure the native scene has updated as well
    assert _child_names(scene2_native).count("Image") == 0
