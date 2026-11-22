"""Build a self-contained Blender MOT animation and optionally render in Cycles.

Run with the same Python major/minor version as Blender; see projects/mot/README.md.
The launcher starts a separate factory-startup process, leaving open files alone.
"""

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[2]


def build(options):
    import bpy
    from mathutils import Vector
    from basilisp.lang.keyword import keyword
    from basilisp_blender.eval import eval_str
    from fawltypoly.animation_support import bake_transforms
    from projects.mot.motion import ease, DURATION

    # This entry point is only called in a fresh factory-startup subprocess.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    frames = options["frames"]
    result = eval_str(
        "(do (require '[projects.mot.scene :as mot] '[fawltypoly.api.v1 :as fp]) (mot/show! "
        f"{{:atom-count {options['atoms']} :seed {options['seed']} :frames {frames}}}))"
    )
    objects = dict(result.val_at(keyword("objects")).items())
    materials = dict(result.val_at(keyword("materials")).items())
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    scene.render.fps = options["fps"]
    scene.render.fps_base = 1
    scene["MOT educational model"] = "Authored trajectories; no force or temperature solver"
    scene["MOT units"] = "Display units; beam colours, atom sizes and time are illustrative"
    presentation = bpy.data.collections.new("MOT presentation")
    scene.collection.children.link(presentation)

    def frame(time):
        return 1 + time / DURATION * (frames - 1)

    def visibility(obj, start=0, end=DURATION + 1):
        for time, hidden in [(0, start > 0), (start, False), (end, True)]:
            if time <= DURATION:
                for path in ("hide_render", "hide_viewport"):
                    setattr(obj, path, hidden)
                    obj.keyframe_insert(data_path=path, frame=frame(time))
        from fawltypoly.animation_support import action_curves
        for curve in action_curves(obj):
            if curve.data_path in {"hide_render", "hide_viewport"}:
                for point in curve.keyframe_points:
                    point.interpolation = "CONSTANT"

    def emission(name, color, strength=1):
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        node = nodes.new("ShaderNodeEmission")
        node.inputs["Color"].default_value = (*color, 1)
        node.inputs["Strength"].default_value = strength
        output = nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(node.outputs[0], output.inputs["Surface"])
        return material

    def beam_material(name, color):
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        tree = material.node_tree
        tree.nodes.clear()
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
        # Emissive envelopes read clearly at low sample counts, without the
        # coincident volume-boundary artifacts of six intersecting media.
        light = tree.nodes.new("ShaderNodeEmission")
        light.inputs["Color"].default_value = (*color, 1)
        light.inputs["Strength"].default_value = 1
        mix = tree.nodes.new("ShaderNodeMixShader")
        strength = mix.inputs[0]
        for time, value in [(0, 0), (4, 0), (5, 0.045), (DURATION, 0.045)]:
            strength.default_value = value
            strength.keyframe_insert(data_path="default_value", frame=frame(time))
        tree.links.new(transparent.outputs[0], mix.inputs[1])
        tree.links.new(light.outputs[0], mix.inputs[2])
        tree.links.new(mix.outputs[0], output.inputs["Surface"])
        return material

    axis_colors = [(0.95, 0.12, 0.22), (0.08, 0.65, 0.95), (0.56, 0.22, 1.0)]
    for axis, color in enumerate(axis_colors):
        material = beam_material(f"Cooling light {'XYZ'[axis]}", color)
        for sign in (-1, 1):
            obj = objects[f"beam/{axis}/{sign}"]
            obj.data.materials.clear()
            obj.data.materials.append(material)
            visibility(obj, 4)
            visibility(objects[f"beam-direction/{axis}/{sign}"], 4)

    # Magnetic field is represented schematically, never as an inward B field.
    for name, obj in objects.items():
        if name.startswith("gradient/"):
            visibility(obj, 11)
            bake_transforms(obj, [(frame(t), None, None, (s, s, s))
                                 for t, s in [(0, 0.001), (11, 0.001), (12, 1), (20, 1)]])
    copper = materials[keyword("copper")]
    bsdf = next(n for n in copper.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Emission Color"].default_value = (1, 0.19, 0.035, 1)
    for time, strength in [(0, 0), (11, 0), (12, 0.45), (20, 0.45)]:
        socket = bsdf.inputs["Emission Strength"]
        socket.default_value = strength
        socket.keyframe_insert(data_path="default_value", frame=frame(time))

    camera_data = bpy.data.cameras.new("MOT camera")
    camera = bpy.data.objects.new("MOT camera", camera_data)
    presentation.objects.link(camera)
    target = Vector((0, 0, 0))
    camera.location = (10, -15, 10)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type, camera_data.ortho_scale = "ORTHO", 13.5
    scene.camera = camera
    orientation = camera.rotation_euler.to_quaternion()
    right, up, toward = (orientation @ Vector(axis) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    white = emission("Type / ivory", (0.83, 0.9, 1))
    muted = emission("Type / muted", (0.32, 0.44, 0.59))
    mint = emission("Type / field", (0.15, 0.95, 0.66))
    gold = emission("Type / atoms", (1, 0.62, 0.2))

    def text(label, x, y, size=0.18, material=white, start=0, end=DURATION + 1, align="LEFT"):
        data = bpy.data.curves.new(label, "FONT")
        data.body, data.size, data.align_x = label, size, align
        data.space_character = 1.1
        data.materials.append(material)
        obj = bpy.data.objects.new(label, data)
        presentation.objects.link(obj)
        obj.location = target + right * x + up * y + toward * 8
        obj.rotation_euler = camera.rotation_euler
        visibility(obj, start, end)
        return obj

    text("F A W L T Y P O L Y   /   A T O M I C   O P T I C S", -6.1, 3.22, 0.14, muted)
    text("Magneto-optical trapping", -6.1, 2.70, 0.39)
    text("01  FREE MOTION", -6.1, 2.25, 0.18, gold, end=4)
    text("02  LASER COOLING", -6.1, 2.25, 0.18, gold, start=4, end=11)
    text("03  COOLING + CONFINEMENT", -6.1, 2.25, 0.18, mint, start=11)
    text("Fast atoms cross the scene.\nLong strokes show rapid motion.",
         -6.1, -2.75, 0.20, start=0, end=4)
    text("Three pairs of opposing beams slow the central atoms.\nCooling reduces motion; the cloud is still spread out.",
         -6.1, -2.75, 0.20, start=4, end=11)
    text("Opposite coil currents create a magnetic-field gradient.\nTogether with the light, this produces a restoring force.",
         -6.1, -2.75, 0.20, start=11, end=16)
    text("A compact, cold cloud remains in random motion.\nA MOT localizes atoms; it does not arrange them into a lattice.",
         -6.1, -2.75, 0.20, start=16)
    text("QUALITATIVE DEMONSTRATION  /  Sizes, beam colours and timing are illustrative.",
         -6.1, -3.49, 0.13, muted)
    for i, (label, start, end) in enumerate([("MOTION", 0, 4), ("COOLING", 4, 11), ("TRAPPING", 11, 21)]):
        x = 3.8 + i * 0.85
        text(label, x, 3.20, 0.115, muted)
        text("______", x, 3.07, 0.15, gold if i < 2 else mint, start=start, end=end)
    for axis, color in enumerate(axis_colors):
        mat = emission(f"Legend {'XYZ'[axis]}", color)
        text(f"{'XYZ'[axis]} pair", 4.7, 1.9 - axis * 0.30, 0.17, mat, start=4)
    text("red-detuned light\ncolours identify axes", 4.7, 0.82, 0.13, muted, start=4)
    text("B = 0", 0.65, -0.10, 0.16, mint, start=11)
    text("gradient guides", 4.7, -0.12, 0.15, mint, start=11)
    text("not force arrows", 4.7, -0.37, 0.13, muted, start=11)

    # Opposite current-direction cues, attached to the two physical coils.
    for side in (-1, 1):
        curve = bpy.data.curves.new(f"Current arc {side}", "CURVE")
        curve.dimensions, curve.bevel_depth = "3D", 0.025
        spline = curve.splines.new("POLY")
        angles = [side * (0.35 + i / 24 * 1.6) for i in range(25)]
        points = [Vector((2.3 * math.cos(a), 2.3 * math.sin(a), side * 1.6)) for a in angles]
        spline.points.add(len(points) - 1)
        for point, xyz in zip(spline.points, points):
            point.co = (*xyz, 1)
        curve.materials.append(mint)
        arc = bpy.data.objects.new(f"Opposing current {side}", curve)
        presentation.objects.link(arc)
        visibility(arc, 11)
        # Arrowhead data comes from FawltyPoly's general geometry API.
        mesh = eval_str("(fp/arrow {:length 0.27 :shaft-radius 0.018 :head-radius 0.10 :head-length 0.20})")
        data = bpy.data.meshes.new(f"Current arrow {side}")
        data.from_pydata(list(mesh.val_at(keyword("vertices"))), [], list(mesh.val_at(keyword("faces"))))
        data.materials.append(mint)
        arrow = bpy.data.objects.new(f"Current direction {side}", data)
        presentation.objects.link(arrow)
        arrow.location = points[-1]
        arrow.rotation_euler = (points[-1] - points[-2]).to_track_quat("Z", "Y").to_euler()
        visibility(arrow, 11)

    # Velocity strokes are display aids, baked with independent object transforms.
    # Their length falls with the retimed motion; there are no frame handlers.
    trail_material = emission("Motion strokes", (0.58, 0.31, 0.075), 0.8)
    trail_mesh_spec = eval_str("(fp/cylinder {:radius 1 :depth 1 :segments 5})")
    trail_mesh = bpy.data.meshes.new("Shared velocity stroke")
    trail_mesh.from_pydata(list(trail_mesh_spec.val_at(keyword("vertices"))), [],
                          list(trail_mesh_spec.val_at(keyword("faces"))))
    trail_mesh.materials.append(trail_material)
    from projects.mot.motion import population, position
    for index, atom in enumerate(population(options["atoms"], options["seed"])):
        if not atom.captured:
            visibility(objects[f"atom/{index}"], 0, 14)
        trail = bpy.data.objects.new(f"Velocity stroke {index}", trail_mesh)
        presentation.objects.link(trail)
        samples = []
        for f in range(1, frames + 1):
            time = (f - 1) / (frames - 1) * DURATION
            current = Vector(position(atom, time))
            previous = Vector(position(atom, time - 0.055))
            delta = current - previous
            rotation = delta.to_track_quat("Z", "Y").to_euler() if delta.length > 1e-8 else (0, 0, 0)
            # Hide tiny strokes rather than cluttering the final cloud.
            thickness = 0.009 * (1 - ease(12, 16, time)) if atom.captured else 0.009
            samples.append((f, previous, rotation, (thickness, thickness, delta.length)))
        bake_transforms(trail, samples)
        visibility(trail, 0, 16 if atom.captured else 14)

    for name, location, energy, size in [
        ("Key", (1, -6, 8), 1800, 7), ("Rim", (-5, 2, 5), 2200, 5),
        ("Fill", (5, 5, -2), 1200, 5),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        light = bpy.data.objects.new(name, data)
        presentation.objects.link(light)
        light.location = location
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.008, 0.014, 0.03, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = options["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 24
    scene.render.resolution_x = options["width"]
    scene.render.resolution_y = round(options["width"] * 9 / 16)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.render.film_transparent = False
    for time, label in [(0, "01 Free motion"), (4, "02 Lasers on"), (5, "Cooling"),
                        (11, "03 Coils on"), (12, "Capture"), (16, "Localized cloud")]:
        scene.timeline_markers.new(label, frame=round(frame(time)))
    # Make the first open useful: camera view, material colours, clean overlays.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
                area.spaces.active.overlay.show_overlays = False
                area.spaces.active.shading.type = "MATERIAL"
    output = Path(options["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    directory = output.parent / f"{output.stem}-frames"
    scene.render.filepath = str(directory / "frame-")
    scene.frame_step = options["frame_step"]
    scene.frame_set(round(frame(17.5)))
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    for still in options["stills"]:
        scene.frame_set(still)
        scene.render.filepath = str(output.parent / f"{output.stem}-{still:04}.png")
        bpy.ops.render.render(write_still=True)
    if options["render_animation"]:
        directory.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(directory / "frame-")
        bpy.ops.render.render(animation=True)
    print(f"MOT animation saved: {output}", flush=True)


def main():
    if "--" in sys.argv:
        site_packages, version, encoded = sys.argv[sys.argv.index("--") + 1:]
        if version != f"{sys.version_info.major}.{sys.version_info.minor}":
            raise RuntimeError("The launcher and Blender must use matching Python major/minor versions")
        sys.path[:0] = [str(ROOT), site_packages]
        build(json.loads(encoded))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "output/mot.blend")
    parser.add_argument("--atoms", type=int, default=144)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--stills", type=int, nargs="*", default=[])
    parser.add_argument("--render-animation", action="store_true")
    parser.add_argument("--frame-step", type=int, default=1,
                        help="Render every Nth frame for a quick preview")
    args = parser.parse_args()
    if min(args.atoms, args.fps, args.samples, args.width, args.frame_step) < 1:
        parser.error("Counts, width, fps, samples and frame-step must be positive")
    if args.output.suffix.lower() != ".blend":
        parser.error("--output must end in .blend")
    options = vars(args).copy()
    options["frames"] = args.fps * 20
    if any(f < 1 or f > options["frames"] for f in args.stills):
        parser.error("Still frames must fall within the 20-second animation")
    options["output"] = str(args.output.resolve())
    return subprocess.run(
        ["blender", "--background", "--factory-startup", "--python-exit-code", "1",
         "--python", str(Path(__file__).resolve()), "--", sysconfig.get_paths()["purelib"],
         f"{sys.version_info.major}.{sys.version_info.minor}", json.dumps(options)],
        cwd=ROOT, env=dict(os.environ, ALSOFT_DRIVERS="null"), check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
