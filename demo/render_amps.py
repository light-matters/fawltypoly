"""Render a labelled AMPS comparison in a separate factory-startup Blender.

Usage: poetry run python demo/render_amps.py --output dist/amps-comparison.png
Poetry's Python major/minor version must match Blender's. A .blend file is saved
alongside the PNG. This does not change a Blender session that is already open.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]


def render(output, samples, layout="comparison", field_case="polar-45"):
    if layout in ("paired", "vmag"):
        from paired_figure import render as render_paired
        if layout == "paired":
            return render_paired(output, samples)
        cases = ("polar-0", "polar-45", "polar-90") if field_case == "all" else (field_case,)
        for case in cases:
            target = output.with_name(f"{output.stem}-{case}{output.suffix}") if field_case == "all" else output
            render_paired(target, samples, field_case=case)
        return
    import bpy
    from mathutils import Vector
    from basilisp_blender.eval import eval_str

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    eval_str("(do (require '[demo.amps :as demo]) (demo/show! {:theta-segments 64 :phi-segments 96}))")
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Figure camera")
    camera = bpy.data.objects.new("Figure camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    target = Vector((0, 0, 0.45))
    camera.location = (0, -12, 8)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 11.8
    rotation = camera.rotation_euler.to_quaternion()
    right = rotation @ Vector((1, 0, 0))
    up = rotation @ Vector((0, 1, 0))
    forward = rotation @ Vector((0, 0, 1))

    def ink(name, color):
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        emission = nodes.new("ShaderNodeEmission")
        emission.inputs["Color"].default_value = (*color, 1)
        emission.inputs["Strength"].default_value = 1
        out = nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(emission.outputs["Emission"], out.inputs["Surface"])
        return material

    dark = ink("Annotation ink", (0.025, 0.035, 0.05))
    muted = ink("Guide axes", (0.25, 0.3, 0.36))
    guides = bpy.data.collections.new("Figure annotations")
    scene.collection.children.link(guides)

    def text(label, position, size=0.18, material=dark, align="CENTER"):
        data = bpy.data.curves.new(label, "FONT")
        data.body = label
        data.align_x = align
        data.align_y = "CENTER"
        data.size = size
        obj = bpy.data.objects.new(label, data)
        guides.objects.link(obj)
        obj.location = position
        obj.rotation_euler = camera.rotation_euler
        data.materials.append(material)
        return obj

    def screen_text(label, x, y, size=0.18):
        return text(label, target + right * x + up * y + forward * 5, size)

    def line(label, points):
        data = bpy.data.curves.new(label, "CURVE")
        data.dimensions = "3D"
        data.bevel_depth = 0.008
        data.bevel_resolution = 1
        spline = data.splines.new("POLY")
        spline.points.add(len(points) - 1)
        for point, value in zip(spline.points, points):
            point.co = (*value, 1)
        obj = bpy.data.objects.new(label, data)
        guides.objects.link(obj)
        data.materials.append(muted)

    # Guides are diagram overlays: move them towards the orthographic camera
    # without changing their projected positions, keeping origins visible.
    for x in (-3.2, 0, 3.2):
        origin = Vector((x, 0, 0)) + forward * 5
        line("X guide", [origin + Vector((-1.3, 0, 0)), origin + Vector((1.45, 0, 0))])
        line("Z guide", [origin + Vector((0, 0, -0.85)), origin + Vector((0, 0, 2.25))])
        text("x", origin + Vector((1.6, 0, 0)), 0.15, muted)
        text("z", origin + Vector((0, 0, 2.42)), 0.15, muted)
        text("O", origin + right * 0.12 - up * 0.15, 0.14, muted)
        # A tick marks one Blender unit on each positive axis.
        for axis in (Vector((1, 0, 0)), Vector((0, 0, 1))):
            point = origin + axis
            tick = up * 0.05 if axis.x else right * 0.05
            line("Unit tick", [point - tick, point + tick])

    screen_text("SPIN-1 ANGULAR MOMENTUM PROBABILITY SURFACES", 0, 2.45, 0.29)
    screen_text("Same scale: r = 2 P(theta, phi)    |    O: angular origin    |    axis ticks: 1 unit", 0, 2.05, 0.18)
    for x, title, state, formula in [
        (-3.2, "UNPOLARIZED", "rho = I / 3", "P = 1 / 3"),
        (0, "STRETCHED", "state |1, 1>", "P = cos(theta / 2)^4"),
        (3.2, "ALIGNED", "state |1, 0>", "P = sin(theta)^2 / 2"),
    ]:
        screen_text(title, x, -1.45, 0.22)
        screen_text(state, x, -1.77, 0.19)
        screen_text(formula, x, -2.08, 0.18)
    # Use exactly the shader ramp's linear RGB interpolation for the legend.
    stops = eval_str("(do (require '[fawltypoly.color :as color]) (color/colormap-stops :viridis))")
    for i in range(256):
        x = (i + 0.5) / 256 * 31
        index = min(30, int(x))
        weight = x - index
        rgba = [(1 - weight) * a + weight * b
                for a, b in zip(stops[index][1], stops[index + 1][1])]
        material = ink(f"Colorbar {i}", rgba[:3])
        left = -2.5 + i / 256 * 5
        right_edge = -2.5 + (i + 1) / 256 * 5
        vertices = [target + right * x + up * y + forward * 5
                    for x, y in [(left, -2.5), (right_edge, -2.5),
                                 (right_edge, -2.38), (left, -2.38)]]
        data = bpy.data.meshes.new(f"Colorbar {i}")
        data.from_pydata(vertices, [], [(0, 1, 2, 3)])
        obj = bpy.data.objects.new(f"Colorbar {i}", data)
        guides.objects.link(obj)
        data.materials.append(material)
    screen_text("Viridis: local radius r", -3.85, -2.44, 0.16)
    for value in (0, 0.5, 1, 1.5, 2):
        screen_text(f"{value:g}", -2.5 + value / 2 * 5, -2.69, 0.15)
    screen_text("P: probability of maximal projection along (theta, phi). Theta is measured from +z.",
                0, -3.03, 0.16)

    for label, location, energy, size in [
        ("Key", (-3, -4, 7), 900, 6), ("Fill", (5, 1, 5), 600, 5),
    ]:
        data = bpy.data.lights.new(label, "AREA")
        light = bpy.data.objects.new(label, data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
        data.energy = energy
        data.size = size
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.8, 0.85, 0.9, 1)
    background.inputs["Strength"].default_value = 0.45
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix(".blend")))
    bpy.ops.render.render(write_still=True)


def main():
    if "--" in sys.argv:
        site, version, output, samples, layout, field_case = sys.argv[sys.argv.index("--") + 1:]
        if version != f"{sys.version_info.major}.{sys.version_info.minor}":
            raise RuntimeError("Poetry and Blender must use the same Python major/minor version")
        sys.path[:0] = [str(ROOT), site, str(Path(__file__).resolve().parent)]
        render(Path(output), int(samples), layout, field_case)
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", choices=("comparison", "paired", "vmag"), default="comparison")
    parser.add_argument("--field-case", choices=("polar-0", "polar-45", "polar-90", "all"), default="polar-45")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--samples", type=int, default=32)
    args = parser.parse_args()
    if args.output is None:
        args.output = ROOT / f"dist/amps-{args.layout}.png"
    if args.samples < 1:
        parser.error("--samples must be positive")
    if args.output.suffix.lower() != ".png":
        parser.error("--output must end in .png")
    return subprocess.run(
        ["blender", "--background", "--factory-startup", "--python-exit-code", "1",
         "--python", str(Path(__file__).resolve()), "--", sysconfig.get_paths()["purelib"],
         f"{sys.version_info.major}.{sys.version_info.minor}", str(args.output.resolve()), str(args.samples), args.layout, args.field_case],
        cwd=ROOT, env=dict(os.environ, ALSOFT_DRIVERS="null"), check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
