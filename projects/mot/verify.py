"""Verify the saved .blend in Blender without importing the generator/package."""

import math
import bpy


def verify():
    scene = bpy.context.scene
    collection = bpy.data.collections["MOT demonstration"]
    objects = {obj.get("fawltypoly.id"): obj for obj in collection.objects}
    atoms = [obj for key, obj in objects.items() if key and key.startswith("string:atom/")]
    captured = [obj for obj in atoms if int(obj.name.split()[-1]) % 5 != 0]
    assert len(atoms) > 0 and len(captured) > 0
    assert len({obj.data.as_pointer() for obj in atoms}) == 1, "Atoms should share one mesh"
    assert scene.render.engine == "CYCLES"
    assert scene.frame_start == 1 and scene.frame_end == scene.render.fps * 20
    assert len(scene.timeline_markers) == 6

    def at(time):
        scene.frame_set(round(1 + time / 20 * (scene.frame_end - 1)))
        return [tuple(obj.location) for obj in captured]

    def speed(time):
        scene.frame_set(round(1 + time / 20 * (scene.frame_end - 1)))
        before = [tuple(obj.location) for obj in captured]
        scene.frame_set(scene.frame_current + 1)
        return sum(math.dist(p, obj.location) for p, obj in zip(before, captured)) / len(captured)

    assert speed(10) < speed(2) * 0.2, "Laser stage should slow the central atoms"
    spread = lambda points: sum(sum(x * x for x in p) for p in points) / len(points)
    assert spread(at(18)) < spread(at(10)) * 0.3, "Capture should localize the cloud"
    assert speed(18) > 0, "Localized atoms should retain residual motion"
    at(2)
    assert all(objects[f"string:beam/{axis}/{sign}"].hide_render
               for axis in range(3) for sign in (-1, 1))
    at(8)
    polarized = [obj for obj in collection.objects if 'mot.polarization-k' in obj]
    if polarized:
        from mathutils import Vector
        assert len(polarized) == 6
        for obj in polarized:
            k = Vector(obj['mot.polarization-k'])
            real = Vector(obj['mot.polarization-real'])
            imag = Vector(obj['mot.polarization-imag'])
            assert abs(real.length_squared + imag.length_squared - 1) < 1e-6
            assert abs(real.dot(k)) < 1e-6 and abs(imag.dot(k)) < 1e-6
            assert abs(2 * real.cross(imag).dot(k) - obj['mot.polarization-helicity']) < 1e-6
            assert not obj.hide_render
            direction = obj.rotation_euler.to_matrix() @ Vector((0, 0, 1))
            assert abs(direction.dot(k)) < 1e-6
        at(2)
        assert all(obj.hide_render for obj in polarized)
        at(8)
    if 'string:beam-volume' in objects:
        volume = objects['string:beam-volume']
        assert not volume.hide_render
        assert volume.data.materials[0].node_tree.nodes.get('Gaussian emission') is not None
        copper = objects['string:coil/-1/0'].data.materials[0]
        bsdf = next(n for n in copper.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        assert bsdf.inputs['Metallic'].default_value == 1
        assert bsdf.inputs['Emission Strength'].default_value == 0
        at(2)
        assert volume.hide_render
        at(8)
    else:
        assert all(not objects[f"string:beam/{axis}/{sign}"].hide_render
                   for axis in range(3) for sign in (-1, 1))
    assert objects["string:gradient/0"].hide_render
    at(18)
    assert not objects["string:gradient/0"].hide_render
    assert all(obj.hide_render for obj in atoms if obj not in captured), "Escaped atoms should leave the shot"
    # Scrubbing out of order exercises the baked animation without any callbacks.
    end_positions = at(18)
    at(1)
    assert end_positions == at(18)
    assert all(not obj.animation_data or not obj.animation_data.drivers for obj in scene.objects)
    print(f"PASS: standalone Cycles MOT, {len(atoms)} instanced atoms, cooling, capture, "
          f"{len(polarized)} lab-frame polarization markers and scrubbing", flush=True)


if __name__ == "__main__":
    verify()
