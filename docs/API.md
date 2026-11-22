# Public API and compatibility

Use `(require '[fawltypoly.api.v1 :as fp])` in Blender/Basilisp. This is the
supported public entry point; `fp/api-version` is `1`. Package release versions
(e.g. `0.2.0`) identify the implementation, while the namespace identifies the
API contract. Pin the package version in a project's dependency lockfile for
reproducible environments.

Changes to v1 must preserve existing function names, arities, accepted data,
defaults and return conventions. Additive features and bug fixes can ship in
later package releases. An intentional incompatible contract belongs in
`fawltypoly.api.v2`, alongside v1, with migration notes. Keep v1 available while
projects depend on it. Blender/Python compatibility still depends on the tested
runtime and lockfile; namespace versioning does not freeze Blender itself.

The lower-level `fawltypoly.scene`, `geometry`, `layout`, etc. namespaces remain
available, but new applications should depend on v1. Python support modules are
implementation details. Demos, upstream physics, their data schemas and plotting
presets are application code and have their own lifecycle.

## Exports

| Purpose | Public names under `fp/` |
| --- | --- |
| Scene reconciliation | `ensure-scene!` |
| Baked animation and instances | `bake-transforms!`, `share-mesh!` |
| Mesh data and validation | `plane`, `cube`, `validate-mesh!`, `finite?` |
| Surface geometry | `parametric-surface`, `radial-surface`, `radial-grid`, `arrow`, `cylinder` |
| AMPS adapters | `expression->mesh`, `grid->mesh`, `read-amps-json` |
| Symbolic data | `read-data`, `read-expression`, `compile-expression` |
| Layout descriptions | `circular`, `paired-rings`, `field-vector`, `ring-guide`, `compass-sphere`, `poster-compass` |
| Colour data | `colormap-stops`, `sample-color` |

These functions retain the arguments/options documented in the main README
for their underlying namespaces. Layout and geometry functions return data;
`ensure-scene!` is the boundary that applies scene descriptions to Blender.
The reusable compass meshes are shipped with the library; no VMAG data or
calculation is required to load them.

## General and domain layers

`fawltypoly.api.v1` provides context-independent geometry, scenes and animation.
Atomic/quantum-optics objects live in `fawltypoly.quantum-optics.api.v1`, with the
same additive v1 compatibility policy. Its functions return scene-description
vectors; apply them with the general API's `ensure-scene!`:

| Domain export | Arguments and main options |
| --- | --- |
| `atom-cloud` | prefix, positions, options: `:radius`, `:material` |
| `cooling-beams` | prefix, options: `:center`, `:radius`, `:half-length`, `:axis-materials` |
| `cooling-volume` | string ID, options: `:extent` (default 4.8); local-coordinate bounding mesh |
| `gaussian-cooling-material!` | label, options: `:colors`, `:waist`, `:rayleigh-range`, `:half-length`, `:fade-length`, `:strength` |
| `circular-polarization` | direction, options: `:reference`, `:helicity`; returns lab XYZ `:real`, `:imag`, `:k` |
| `circular-polarization-glyph` | prefix, options: `:center`, `:direction`, `:reference`, `:helicity`, `:radius`, `:phase`, `:material` |
| `anti-helmholtz-coils` | prefix, options: `:center`, `:normal`, `:radius`, `:separation`, `:turns`, `:wire-radius`, `:turn-spacing`, `:material` |
| `quadrupole-guides` | prefix, options: `:center`, `:normal`, `:radial-distance`, `:axial-distance`, `:length`, `:material` |
| AMPS adapters | `expression->mesh`, `grid->mesh`, `read-amps-json` |

Prefixes are nonempty strings and scope stable IDs. These functions illustrate
apparatus; they do not compute atomic dynamics or magnetic fields. Beam pairs
are aligned with global XYZ; coils and guides can be oriented along any normal.
Existing AMPS exports in the general v1 API remain for compatibility; the domain
API is the preferred entry point for new atomic-optics applications.

The Gaussian material represents all three pairs in one emissive volume, avoiding
intersecting volume boundaries. Its intensity is proportional to
`exp(-2 r² / w(z)²) / q`, where `q = 1 + (z / rayleigh-range)²` and
`w(z)² = waist² q`. `:waist` is the 1/e² intensity radius at the centre (default
0.9); `:rayleigh-range` defaults to 6 display units. A smooth crop fades the ends
between `half-length - fade-length` and `half-length` (defaults 4.1 and 0.65).
Colours are three linear RGB triples; strength defaults to 0.16. Dimensions must
be positive, `fade-length < half-length`, and strength nonnegative. Defaults are
illustrative; the Rayleigh range is not derived from a wavelength.

Assign this material to one `cooling-volume` mesh (or an equivalent containing
mesh with coordinates in display units). The default extent covers the default
ends and Gaussian tails. Larger beam parameters require a larger extent. Animate
the `Gaussian emission` node's `Emission Strength` socket to activate the light.
Reapplying the material replaces its nodes and shader animation. This shows
intensity as radiance for teaching; it does not simulate vacuum scattering,
interference, or atomic forces.

Polarization uses `E(t) = Re[epsilon exp(-i omega t)]`. `circular-polarization`
returns a normalized Cartesian Jones vector: `epsilon = real + i imag`. The
reference vector fixes its real transverse axis. Helicity is +1 or -1, defined
without a viewing-direction ambiguity by `Im(epsilon* cross epsilon) dot k`.
This describes the light in fixed lab coordinates, not sigma transitions relative
to a spatially varying magnetic field. The glyph returns three ordinary mesh
descriptions (circle, rotation arrow, and radial electric-field arrow), oriented
in the plane perpendicular to propagation. Default radius is 0.28 display units.

## Baked animation

`(fp/bake-transforms! object samples options)` accepts an object/name and ordered
samples such as `[{:frame 1 :location [0 0 0]} {:frame 24 :location [1 0 0]}]`.
Each sample needs a finite `:frame` and at least one finite XYZ `:location`,
`:rotation` (XYZ Euler radians), or `:scale`. Frames must increase strictly.
Rotation tracks require the object's XYZ Euler mode. All samples are validated
before mutation. The optional `:interpolation` is `:linear` (default), `:constant`
or `:bezier`. Supplied transform channels are replaced over their entire range;
other channels remain. Omitted transforms at individual samples do not add keys.
Shared actions are copied before modification. Returns the object. Blender
runtime errors are not transactional; run mutations on Blender's main thread.

`(fp/share-mesh! prototype targets)` makes existing mesh objects share the
prototype's mesh, materials and shading; independent transforms and animation
are retained. Returns resolved targets. This is explicit instancing after scene
reconciliation: repeat it after `ensure-scene!`, which replaces described meshes.

`(fp/cylinder {:radius 1 :depth 1 :segments 32})` returns a closed cylinder from
local z=0 to z=depth. Dimensions must be positive and finite; segments at least 3.

Scene materials additionally accept `:emission-color` (linear RGBA, defaults to
`:color`) and `:emission-strength` (finite, nonnegative, defaults to zero). Updating
a material without emission options resets its emission. The illustrative MOT
uses these general material controls for atoms and activation cues.

## Data conventions

- Angles are radians; vectors are `[x y z]` in Blender's coordinate system.
- Meshes contain `:vertices` and `:faces`; faces contain zero-based indices.
- Radial sampling uses polar `theta` from +Z and azimuthal `phi` from +X.
- AMPS radii are `radius-scale * P(theta, phi)`. The generic adapters do not
  normalize probabilities. State normalization belongs to the application.
- A scene description contains `:collection`, `:objects`, optional `:materials`
  and `:prune?`. Objects have stable string/keyword `:id` values and one of
  `:mesh` or a supported `:asset`. Transforms and material references are optional.
- Reconciliation updates objects with the same IDs in an owned collection,
  preserving object identity. Pruning removes omitted owned objects only.
  The result contains `:collection`, `:objects` and `:materials` Blender handles.
- Symbolic forms are data, restricted to the compiler's arithmetic whitelist.
  Parameters bind finite numbers; results must be finite and real within the
  configured tolerance.

## 0.2.0 migration

The former application namespace `fawltypoly.vmag` moved to `demo.vmag.plot`.
Configure the repository as the Basilisp Project Directory to run it. Its data,
exporter and verifier now live in `demo/vmag/`; they are not wheel contents.
The existing bundle format `"fawltypoly.vmag/1"` remains unchanged so saved
exports continue to load. Conditional ground normalization stays the demo's
default. The core library does not depend on the demo.

Run `poetry run python tests/run_blender.py --api-only` to check the library
without loading any demos; omit `--api-only` to also check the applications.
