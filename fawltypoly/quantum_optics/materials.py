"""Gaussian cooling-light fields and their Cycles volume shader.

The shader is an educational visibility aid, not scattering from a vacuum.
All three counter-propagating pairs share one volume, avoiding coincident caps
and overlapping medium boundaries. Coordinates are object-local display units.
"""
import math


def validate(colors, waist, rayleigh_range, half_length, fade_length, strength):
    colors = tuple(tuple(c) for c in colors)
    if (len(colors) != 3 or any(len(c) != 3 for c in colors)
            or not all(math.isfinite(v) and 0 <= v <= 1 for c in colors for v in c)
            or not all(math.isfinite(v) and v > 0
                       for v in (waist, rayleigh_range, half_length, fade_length))
            or fade_length >= half_length or not math.isfinite(strength) or strength < 0):
        raise ValueError('Expected three linear RGB colours and valid Gaussian beam dimensions')
    return colors


def beam_profile(position, axis, waist=0.9, rayleigh_range=6.0,
                 half_length=4.1, fade_length=0.65):
    """Relative I(r,z) = exp(-2r²/w(z)²)/(1+(z/zR)²), with soft endpoint fade.

    waist is the 1/e² intensity radius at the centre. The longitudinal envelope
    is a presentation crop, not an optical boundary. No interference is modelled.
    """
    validate(((1, 1, 1),) * 3, waist, rayleigh_range, half_length, fade_length, 1)
    if axis not in (0, 1, 2) or len(position) != 3 or not all(math.isfinite(v) for v in position):
        raise ValueError('Expected a finite XYZ position and axis 0, 1, or 2')
    z = position[axis]
    r2 = sum(v * v for i, v in enumerate(position) if i != axis)
    q = 1 + (z / rayleigh_range) ** 2
    t = max(0, min(1, (half_length - abs(z)) / fade_length))
    fade = t * t * t * (t * (t * 6 - 15) + 10)
    return math.exp(-2 * r2 / (waist * waist * q)) / q * fade


def gaussian_cooling_material(label, colors, waist=0.9, rayleigh_range=6.0,
                             half_length=4.1, fade_length=0.65, strength=0.16):
    """Create/update a three-axis Gaussian emissive volume material.

    Use one containing mesh with local bounds extending beyond half_length and
    three waist radii. Animate the 'Gaussian emission' node's Emission Strength
    socket. Density is zero: this displays intensity without fog obscuring atoms.
    """
    colors = validate(colors, waist, rayleigh_range, half_length, fade_length, strength)
    if not isinstance(label, str) or not label:
        raise ValueError('Expected a nonempty material name')
    import bpy
    material = bpy.data.materials.get(label) or bpy.data.materials.new(label)
    material.use_nodes = True
    tree = material.node_tree
    tree.animation_data_clear()
    tree.nodes.clear()

    def node(kind, name):
        result = tree.nodes.new(kind)
        result.name = result.label = name
        return result

    def connect(value, socket):
        if isinstance(value, (int, float)):
            socket.default_value = value
        else:
            tree.links.new(value, socket)

    def operation(kind, a, b=None, name=None):
        result = node('ShaderNodeMath', name or kind)
        result.operation = kind
        connect(a, result.inputs[0])
        if b is not None:
            connect(b, result.inputs[1])
        return result.outputs[0]

    coords = node('ShaderNodeTexCoord', 'Local beam coordinates')
    xyz = node('ShaderNodeSeparateXYZ', 'XYZ')
    tree.links.new(coords.outputs['Object'], xyz.inputs[0])
    contributions = []
    for axis, color in enumerate(colors):
        tag = 'XYZ'[axis]
        axial = xyz.outputs[axis]
        radial = [xyz.outputs[i] for i in range(3) if i != axis]
        r2 = operation('ADD', operation('MULTIPLY', radial[0], radial[0]),
                       operation('MULTIPLY', radial[1], radial[1]), f'{tag}: r squared')
        z2 = operation('MULTIPLY', axial, axial)
        q = operation('ADD', 1, operation('DIVIDE', z2, rayleigh_range ** 2), f'{tag}: divergence')
        w2 = operation('MULTIPLY', waist ** 2, q, f'{tag}: waist squared')
        exponent = operation('DIVIDE', operation('MULTIPLY', -2, r2), w2)
        gaussian = operation('EXPONENT', exponent, name=f'{tag}: Gaussian radial profile')
        normalized = operation('DIVIDE', gaussian, q)
        distance = operation('SUBTRACT', half_length, operation('ABSOLUTE', axial))
        taper = node('ShaderNodeMapRange', f'{tag}: soft longitudinal crop')
        taper.interpolation_type = 'SMOOTHERSTEP'
        taper.clamp = True
        for key, value in [('From Min', 0), ('From Max', fade_length), ('To Min', 0), ('To Max', 1)]:
            taper.inputs[key].default_value = value
        connect(distance, taper.inputs['Value'])
        profile = operation('MULTIPLY', normalized, taper.outputs['Result'], f'{tag}: intensity')
        weighted = node('ShaderNodeVectorMath', f'{tag}: coloured intensity')
        weighted.operation = 'SCALE'
        weighted.inputs[0].default_value = color
        tree.links.new(profile, weighted.inputs['Scale'])
        contributions.append(weighted.outputs['Vector'])
    summed = contributions[0]
    for i, contribution in enumerate(contributions[1:]):
        add = node('ShaderNodeVectorMath', f'Add beam pair {i + 2}')
        add.operation = 'ADD'
        tree.links.new(summed, add.inputs[0])
        tree.links.new(contribution, add.inputs[1])
        summed = add.outputs['Vector']
    volume = node('ShaderNodeVolumePrincipled', 'Gaussian emission')
    volume.inputs['Density'].default_value = 0
    volume.inputs['Blackbody Intensity'].default_value = 0
    volume.inputs['Emission Strength'].default_value = strength
    tree.links.new(summed, volume.inputs['Emission Color'])
    output = node('ShaderNodeOutputMaterial', 'Volume output')
    tree.links.new(volume.outputs['Volume'], output.inputs['Volume'])
    material['fawltypoly.gaussian-waist'] = waist
    material['fawltypoly.rayleigh-range'] = rayleigh_range
    return material
