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
    from projects.mot.polarizations import beams as polarized_beams

    # This entry point is only called in a fresh factory-startup subprocess.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    frames = options["frames"]
    result = eval_str(
        "(do (require '[projects.mot.scene :as mot] '[fawltypoly.api.v1 :as fp] "
        "'[fawltypoly.quantum-optics.api.v1 :as qo]) (mot/show! "
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

    axis_colors = [(0.95, 0.12, 0.22), (0.08, 0.65, 0.95), (0.56, 0.22, 1.0)]
    material = eval_str('(qo/gaussian-cooling-material! "Gaussian cooling light" {})')
    volume = objects['beam-volume']
    volume.data.materials.clear()
    volume.data.materials.append(material)
    visibility(volume, 4)
    activation = material.node_tree.nodes['Gaussian emission'].inputs['Emission Strength']
    for time, value in [(0, 0), (4, 0), (5, 0.16), (DURATION, 0.16)]:
        activation.default_value = value
        activation.keyframe_insert(data_path='default_value', frame=frame(time))
    for axis in range(3):
        for sign in (-1, 1):
            obj = objects[f"beam/{axis}/{sign}"]
            # Keep addressable apparatus geometry as wire guides. The single
            # Gaussian field supplies all rendered light, without cylinder caps.
            obj.hide_render = True
            obj.hide_viewport = True
            obj['mot.beam-proxy'] = True
            visibility(objects[f"beam-direction/{axis}/{sign}"], 4)

    for beam in polarized_beams():
        prefix = f'polarization/{beam.axis}/{beam.source_side}'
        for part in ('ring', 'rotation', 'field'):
            visibility(objects[f'{prefix}/{part}'], 4)
        field = objects[f'{prefix}/field']
        field['mot.polarization-k'] = beam.direction
        field['mot.polarization-real'] = [v.real for v in beam.jones]
        field['mot.polarization-imag'] = [v.imag for v in beam.jones]
        field['mot.polarization-helicity'] = beam.helicity
        samples = []
        previous = None
        for f in range(1, frames + 1):
            time = (f - 1) / (frames - 1) * DURATION
            phase = math.tau * 0.5 * max(0, time - 4)
            rotation = Vector(beam.field(phase)).to_track_quat('Z', 'Y').to_euler()
            if previous is not None:
                rotation.make_compatible(previous)
            samples.append((f, None, tuple(rotation), None))
            previous = rotation.copy()
        bake_transforms(field, samples)

    # Magnetic field is represented schematically, never as an inward B field.
    for name, obj in objects.items():
        if name.startswith("gradient/"):
            visibility(obj, 11)
            bake_transforms(obj, [(frame(t), None, None, (s, s, s))
                                 for t, s in [(0, 0.001), (11, 0.001), (12, 1), (20, 1)]])
    copper = materials[keyword("copper")]
    bsdf = next(n for n in copper.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    # Bare copper reflects the studio lights; current does not make it glow.
    bsdf.inputs['Emission Strength'].default_value = 0
    anisotropy = bsdf.inputs.get('Anisotropic IOR Level')
    if anisotropy is not None:
        anisotropy.default_value = 0.3
    tree = copper.node_tree
    grain = tree.nodes.new('ShaderNodeTexNoise')
    grain.name = 'Fine copper grain'
    grain.inputs['Scale'].default_value = 180
    grain.inputs['Detail'].default_value = 2
    bump = tree.nodes.new('ShaderNodeBump')
    bump.name = 'Copper microfinish'
    bump.inputs['Strength'].default_value = 0.08
    bump.inputs['Distance'].default_value = 0.005
    tree.links.new(grain.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

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
    axis_ink = [emission(f"Legend {'XYZ'[i]}", color) for i, color in enumerate(axis_colors)]

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
        text(f"{'XYZ'[axis]} pair", 4.7, 1.9 - axis * 0.30, 0.17, axis_ink[axis], start=4)
    text("red-detuned light\ncolours identify axes", 4.7, 0.82, 0.13, muted, start=4)
    text("B = 0", 0.65, -0.10, 0.16, mint, start=11)
    text("gradient guides", 4.7, -0.12, 0.15, mint, start=11)
    text("not force arrows", 4.7, -0.37, 0.13, muted, start=11)

    text('POLARIZATION / LAB XYZ', -6.1, 1.55, 0.17, start=4)
    for row, beam in enumerate(polarized_beams()):
        text(beam.label, -6.1, 1.12 - row * 0.42, 0.155, axis_ink[beam.axis], start=4)
    text('E(t) = Re[ε exp(-iωt)]', -6.1, -1.60, 0.14, muted, start=4)
    text('E rotation slowed for visibility', -6.1, -1.86, 0.13, muted, start=4)
    text('Type-I example; B ∝ (x,y,-2z)', -6.1, -2.12, 0.12, muted, start=4)

    text('LAB FRAME', 4.7, -0.92, 0.14, muted, start=4)
    compass_origin = target + right * 5.1 - up * 1.85 + toward * 8
    compass_mesh = eval_str('(fp/arrow {:length 0.65 :shaft-radius 0.015 :head-radius 0.055 :head-length 0.14})')
    for axis, label in enumerate('XYZ'):
        direction = Vector(tuple(1 if i == axis else 0 for i in range(3)))
        data = bpy.data.meshes.new(f'Lab {label} arrow')
        data.from_pydata(list(compass_mesh.val_at(keyword('vertices'))), [],
                         list(compass_mesh.val_at(keyword('faces'))))
        data.materials.append(axis_ink[axis])
        arrow = bpy.data.objects.new(f'Lab +{label}', data)
        presentation.objects.link(arrow)
        arrow.location = compass_origin
        arrow.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
        arrow['mot.lab-axis'] = label
        visibility(arrow, 4)
        offset = direction * 0.80
        text(label.lower(), 5.1 + offset.dot(right), -1.85 + offset.dot(up),
             0.16, axis_ink[axis], start=4, align='CENTER')

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
    world = scene.world.node_tree
    world.nodes.clear()
    camera_background = world.nodes.new('ShaderNodeBackground')
    camera_background.name = 'Dark camera background'
    camera_background.inputs['Color'].default_value = (0.008, 0.014, 0.03, 1)
    camera_background.inputs['Strength'].default_value = 0.35
    studio = world.nodes.new('ShaderNodeBackground')
    studio.name = 'Neutral studio reflections'
    studio.inputs['Color'].default_value = (0.11, 0.11, 0.11, 1)
    studio.inputs['Strength'].default_value = 0.7
    ray = world.nodes.new('ShaderNodeLightPath')
    mix = world.nodes.new('ShaderNodeMixShader')
    output = world.nodes.new('ShaderNodeOutputWorld')
    world.links.new(ray.outputs['Is Camera Ray'], mix.inputs[0])
    world.links.new(studio.outputs[0], mix.inputs[1])
    world.links.new(camera_background.outputs[0], mix.inputs[2])
    world.links.new(mix.outputs[0], output.inputs['Surface'])
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = options["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 24
    scene.cycles.volume_step_rate = 0.5
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
