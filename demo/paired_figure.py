"""Presentation preset for demo.circular; invoked by render_amps.py --layout paired."""


def render(output, samples, field_case=None):
    import json
    import math
    import bpy
    from mathutils import Vector
    from basilisp_blender.eval import eval_str
    from basilisp.lang.keyword import keyword

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    # Batch field comparisons share one factory-startup process. Remove unused
    # render data between cases; native compass templates have a fake user.
    for blocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
        for block in list(blocks):
            if block.users == 0:
                blocks.remove(block)
    metadata = None
    if field_case is None:
        eval_str("(do (require '[demo.circular :as demo]) (demo/show! {:theta-segments 40 :phi-segments 64 :field-direction [1 1 0.6]}))")
    else:
        metadata = eval_str(f"""(do (require '[fawltypoly.vmag :as vmag] '[fawltypoly.scene :as scene])
          (let [spec (vmag/scene-spec {json.dumps(field_case)} {{:theta-segments 32 :phi-segments 64}})]
            (scene/ensure-scene! spec) (:vmag spec)))""")
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Paired rings camera")
    camera = bpy.data.objects.new("Paired rings camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    target = Vector((0, 0, 0.2))
    camera.location = (10, -14, 12)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 15.8
    rotation = camera.rotation_euler.to_quaternion()
    right = rotation @ Vector((1, 0, 0))
    up = rotation @ Vector((0, 1, 0))
    forward = rotation @ Vector((0, 0, 1))
    annotations = bpy.data.collections.new("Paired rings annotations")
    scene.collection.children.link(annotations)

    def ink(name, rgba):
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        emission = nodes.new("ShaderNodeEmission")
        emission.inputs["Color"].default_value = rgba
        out = nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(emission.outputs["Emission"], out.inputs["Surface"])
        return material

    dark = ink("Label ink", (0.025, 0.035, 0.05, 1))
    red = ink("Field label", (0.55, 0.015, 0.015, 1))

    def text(label, position, size=0.19, material=dark):
        data = bpy.data.curves.new(label, "FONT")
        data.body = label
        data.size = size
        data.align_x = "CENTER"
        data.align_y = "CENTER"
        obj = bpy.data.objects.new(label, data)
        annotations.objects.link(obj)
        obj.location = position
        obj.rotation_euler = camera.rotation_euler
        data.materials.append(material)

    def screen_text(label, x, y, size=0.19):
        text(label, target + right * x + up * y + forward * 9, size)

    if metadata is None:
        title, subtitle = "PAIRED OPTICAL AND ATOMIC AMPS", "Outer: optical    |    Inner: atomic    |    Matching azimuths around B"
        caption = "Illustrative spin-1 states; no magnetic-response simulation."
        field_direction = Vector((1, 1, 0.6)).normalized()
    else:
        params = metadata.val_at(keyword("params"))
        polar = math.degrees(params.val_at(keyword("Bpolar")))
        azimuth = math.degrees(params.val_at(keyword("Bazimuth")))
        bmag = params.val_at(keyword("Bmag"))
        intensity = params.val_at(keyword("int1"))
        title = f"VMAG AMPS: B POLAR ANGLE {polar:g} deg"
        subtitle = f"B = {bmag:g} G, azimuth {azimuth:g} deg | each beam {intensity:g} mW/cm^2 | outer: optical, inner: atomic"
        normalization = ("Ground population retained." if metadata.val_at(keyword("normalization")) == keyword("ground-population")
                         else "Conditioned on the ground manifold.")
        caption = f"SEIT steady state, 87Rb F=1 -> F'=0. Lab frame: beam along +z. {normalization}"
        field_direction = Vector(metadata.val_at(keyword("field-direction")))
    screen_text(title, 0, 4.7, 0.33)
    screen_text(subtitle, 0, 4.25, 0.18)
    field_tip = field_direction * 1.4
    text("B", field_tip + right * 0.3 + up * 0.2 + forward * 0.3, 0.3, red)
    for i in range(8):
        angle = 2 * math.pi * i / 8
        position = Vector((6.35 * math.cos(angle), 6.35 * math.sin(angle), 0))
        text(f"{i * 45} deg", position + forward * 9, 0.18)

    stops = eval_str("(do (require '[fawltypoly.color :as color]) (color/colormap-stops :viridis))")
    for i in range(128):
        x = (i + 0.5) / 128 * 31
        index = min(30, int(x))
        weight = x - index
        rgba = [(1 - weight) * a + weight * b for a, b in zip(stops[index][1], stops[index + 1][1])]
        left, right_edge = -2.4 + i / 128 * 4.8, -2.4 + (i + 1) / 128 * 4.8
        vertices = [target + right * x + up * y + forward * 9
                    for x, y in [(left, -4.35), (right_edge, -4.35),
                                 (right_edge, -4.23), (left, -4.23)]]
        data = bpy.data.meshes.new(f"Legend {i}")
        data.from_pydata(vertices, [], [(0, 1, 2, 3)])
        obj = bpy.data.objects.new(f"Legend {i}", data)
        annotations.objects.link(obj)
        data.materials.append(ink(f"Legend color {i}", rgba))
    screen_text("Local radius r = 1.2 P", -4.05, -4.29, 0.18)
    for value in (0, 0.3, 0.6, 0.9, 1.2):
        screen_text(f"{value:g}", -2.4 + value / 1.2 * 4.8, -4.59, 0.16)
    screen_text(caption, 0, -5.05, 0.17)

    for name, location, power in [("Key", (-4, -6, 9), 1800), ("Fill", (6, 2, 7), 1400)]:
        data = bpy.data.lights.new(name, "AREA")
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
        data.energy = power
        data.size = 8
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.8, 0.85, 0.9, 1)
    background.inputs["Strength"].default_value = 0.45
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix(".blend")))
    bpy.ops.render.render(write_still=True)
