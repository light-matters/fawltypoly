"""Original poster meshes and shaders, bundled independently of the source project."""

from pathlib import Path
import math
import bpy

ASSET_PATH = Path(__file__).with_name("assets") / "compass.blend"
KEYS = {f"compass/{name}" for name in ("north", "south", "shell", "equator", "meridian")}
NEEDLE_LENGTH = 1.9902571439743042


def validate(key, opacity=None):
    if key not in KEYS:
        raise ValueError(f"Unknown bundled compass asset: {key}")
    if not ASSET_PATH.is_file():
        raise FileNotFoundError(ASSET_PATH)
    if opacity is not None and (key != "compass/shell" or not math.isfinite(opacity) or not 0 <= opacity <= 1):
        raise ValueError("Asset opacity must be 0..1 and is only supported for compass/shell")


def template(key):
    validate(key)
    for mesh in bpy.data.meshes:
        if mesh.get("fawltypoly.template") and mesh.get("fawltypoly.asset") == key:
            return mesh
    with bpy.data.libraries.load(str(ASSET_PATH), link=False) as (source, target):
        target.meshes = [name for name in source.meshes if name in KEYS]
    for mesh in target.meshes:
        mesh.use_fake_user = True
    return next(mesh for mesh in target.meshes if mesh.get("fawltypoly.asset") == key)


def apply_to(obj, key, opacity=None):
    """Preserve the object and native materials. Cache five templates per .blend."""
    validate(key, opacity)
    source = template(key)
    previous_owned = [m for m in obj.data.materials if m and m.get("fawltypoly.opacity-copy")]
    if obj.data.get("fawltypoly.asset-instance") != key:
        old = obj.data
        obj.data = source.copy()
        obj.data.use_fake_user = False
        obj.data["fawltypoly.template"] = False
        obj.data["fawltypoly.asset-instance"] = key
        if old.users == 0:
            bpy.data.meshes.remove(old)
    custom = (obj.data.materials[0] if key == "compass/shell" and opacity is not None
              and len(obj.data.materials) and obj.data.materials[0]
              and obj.data.materials[0].get("fawltypoly.opacity-copy") else None)
    obj.data.materials.clear()
    for material in source.materials:
        obj.data.materials.append(material)
    if key == "compass/shell" and opacity is not None:
        material = custom if custom is not None else source.materials[0].copy()
        material.use_fake_user = False
        material["fawltypoly.opacity-copy"] = True
        obj.data.materials[0] = material
        material.node_tree.nodes.get("Mix Shader").inputs[0].default_value = opacity
    for material in previous_owned:
        if material.users == 0:
            bpy.data.materials.remove(material)
    return obj
