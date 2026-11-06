# Original compass assets

`compass.blend` contains the original meshes and material node trees from
`physics/Vis./Compass/CompassPoster/Blender/Poster-MainImage.blend`, reused at
the project owner's request.

| Bundled mesh | Original object |
| --- | --- |
| compass/north | ArrowMagnetic-north |
| compass/south | ArrowMagnetic-south |
| compass/shell | MagneticOutline |
| compass/equator | axis-inclination |
| compass/meridian | axis-azimuth |

The original rotations/scales were baked into these mesh copies, translations
were removed to give the parts a common origin, and the assembly was rotated so
the red/north tip points along local +Z. The original sphere has approximately
unit radius. The complete needle length is 1.9902571439743042 local units.
Original material graphs and face shading are preserved. No original file was
modified, and the application does not access it at runtime.

The asset library was written by Blender 5.2.1. Loading older Blender versions
is not verified. The five mesh templates are cached per Blender file, and each
visible instance receives its own mesh copy. Scene transforms control direction,
center, and size. Optional shell-opacity overrides copy only its material;
omitting the override restores the native shader setting.
