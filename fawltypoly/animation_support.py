"""Blender implementation of the public, data-driven animation helpers."""

import math
import bpy


def action_curves(obj):
    """Only the object's own slot, on both legacy and layered Blender actions."""
    animation = obj.animation_data
    if animation is None or animation.action is None:
        return []
    action = animation.action
    if hasattr(action, "layers") and len(action.layers):
        if animation.action_slot is None:
            return []
        curves = []
        for layer in action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(animation.action_slot)
                if bag is not None:
                    curves.extend(bag.fcurves)
        return curves
    return list(action.fcurves) if hasattr(action, "fcurves") else []


def bake_transforms(obj, samples, interpolation="LINEAR"):
    """Replace the supplied transform channels; leave other animation untouched.

    Samples are (frame, location-or-None, rotation-or-None, scale-or-None).
    Validate the entire track before mutation. No handlers or drivers are needed
    to play or render the resulting .blend file.
    """
    samples = list(samples)
    if interpolation not in {"LINEAR", "CONSTANT", "BEZIER"}:
        raise ValueError("Interpolation must be LINEAR, CONSTANT, or BEZIER")
    if not samples:
        raise ValueError("A transform track must contain at least one sample")
    previous = -math.inf
    paths = ("location", "rotation_euler", "scale")
    channels = set()
    normalized = []
    for frame, *values in samples:
        if (isinstance(frame, bool) or not isinstance(frame, (int, float))
                or not math.isfinite(frame) or frame <= previous or len(values) != 3):
            raise ValueError("Frames must be finite and strictly increasing")
        previous = frame
        row = []
        for path, value in zip(paths, values):
            if value is not None:
                value = tuple(value)
                if len(value) != 3 or not all(
                    isinstance(x, (int, float)) and not isinstance(x, bool)
                    and math.isfinite(x) for x in value
                ):
                    raise ValueError("Transforms must be finite XYZ triples")
                channels.add(path)
            row.append(value)
        if all(value is None for value in row):
            raise ValueError("Each sample needs a transform")
        normalized.append((frame, row))
    if "rotation_euler" in channels and obj.rotation_mode != "XYZ":
        raise ValueError("Rotation tracks require XYZ Euler rotation mode")
    if obj.animation_data and obj.animation_data.action and obj.animation_data.action.users > 1:
        obj.animation_data.action = obj.animation_data.action.copy()
    # Delete keys via Blender's public API, which supports both action layouts.
    for curve in action_curves(obj):
        if curve.data_path in channels:
            path, index = curve.data_path, curve.array_index
            frames = [point.co.x for point in curve.keyframe_points]
            for frame in frames:
                obj.keyframe_delete(data_path=path, index=index, frame=frame)
    for frame, values in normalized:
        for path, value in zip(paths, values):
            if value is not None:
                setattr(obj, path, value)
                obj.keyframe_insert(data_path=path, frame=frame, group="FawltyPoly transforms")
    for curve in action_curves(obj):
        if curve.data_path in channels:
            for point in curve.keyframe_points:
                point.interpolation = interpolation
    return obj


def share_mesh(source, targets):
    """Explicitly share a prototype's mesh, materials and shading with targets."""
    targets = list(targets)
    if any(not isinstance(obj, bpy.types.Object) or obj.type != "MESH"
           for obj in [source, *targets]):
        raise ValueError("Mesh sharing requires mesh objects")
    for obj in targets:
        old = obj.data
        obj.data = source.data
        if old.users == 0:
            bpy.data.meshes.remove(old)
    return targets
