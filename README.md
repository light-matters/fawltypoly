# FawltyPoly

> I speak Blender well. I learn it from a book
> - Manuel (1975). 

This library is an alternative API for the [Blender](blender.org) graphics tool. It is built on-top of[basilisp-blender](https://github.com/ikappaki/basilisp-blender), the REPL-enabling tool for blender, which is itself built on the [basilisp](https://github.com/basilisp-lang/basilisp?tab=readme-ov-file) language, a Python implementation of Clojure (ish).


## Status
Entirely exploratory, providing no guarantees at all! I'm currently playing with it for personal projects, but with an eye to reusability.

## Development setup

Use Poetry 2.4 or newer and Python 3.10 or newer:

```sh
poetry install
poetry check --lock
poetry build
```

The lockfile includes Basilisp 0.5.1 and basilisp-blender 0.5.0. Matplotlib
resolves to 3.10.9 on Python 3.10, and 3.11.2 on Python 3.11 and newer.
Keep the lockfile with dependency updates for reproducible installations.

These commands install the development environment; Blender runs its own Python
environment. To use the library interactively, install the
[basilisp-blender extension](https://github.com/ikappaki/basilisp-blender#installation)
in Blender and set its Basilisp Project Directory to this repository before
starting the nREPL server. Dependencies required by your scripts must also be
available to Blender's Python, with versions matching the lockfile. Avoid adding
another Python version's virtualenv to Blender's module search path.

Connect your editor to the server, then evaluate:

```clojure
(require '[fawltypoly.object :as obj])
(obj/add! :type :plane :name "floor" :scale [4 4 1])
(obj/move "floor" [0 0 -1])
```

## Repeatable scenes

Describe meshes and transforms with ordinary data. Stable IDs are scoped to a
named collection; evaluating the same description updates the same objects,
even after you rename them in Blender:

```clojure
(require '[fawltypoly.scene :as scene]
         '[fawltypoly.geometry :as geo])

(def model
  {:collection "Physics demo"
   :materials {:blue {:color [0.12 0.4 0.8 1] :roughness 0.35}}
   :objects [{:id :apparatus/base
              :mesh geo/cube
              :location [0 0 -1]
              :scale [2 2 0.2]
              :material :blue}]})

(scene/ensure-scene! model)
(scene/ensure-scene! (assoc-in model [:objects 0 :scale] [3 3 0.2]))
```

The result contains `:collection`, `:objects` (ID to Blender object), and
`:materials` (ID to Blender material). IDs may be keywords, including qualified
keywords, or nonempty strings. Object descriptions accept `:name`, `:mesh` or `:asset`,
`:location`, `:rotation`, `:scale`, `:material`, and `:smooth?`.
Rotations are XYZ Euler angles in radians. Colors are linear RGBA.

Each supplied object is a complete description: omitted transforms reset to
identity. For procedural meshes, omitted materials clear slots and smoothing
defaults to false. Bundled assets retain their native materials and face shading
unless explicitly overridden.
Unlisted objects remain. Add `:prune? true` to unlink omitted managed objects
from this collection; untagged objects and objects linked to other collections
are preserved. An existing collection not owned by FawltyPoly is refused.
Material names beginning `fawltypoly/<collection>/` are reserved for this API.

Descriptions are validated before reconciliation. This is not a transaction:
unexpected Blender errors can leave partial changes. Mesh replacement preserves
the object, but replaces mesh data, including any per-vertex attributes.
Shared mesh data remains available to its other users. New scene/mesh operations
do not change selection or the active object. Run Blender mutations on Blender's
main thread, as the basilisp-blender server does.

## Procedural geometry and object operations

`geometry` is pure and can run outside Blender. Mesh data has the shape
`{:vertices [[x y z] ...] :faces [[i j k ...] ...]}` with zero-based indices.
Vertices must be finite, and each polygon needs at least three distinct,
in-range indices. Geometric self-intersection and manifoldness are not checked.

```clojure
(require '[fawltypoly.mesh :as mesh]
         '[fawltypoly.object :as obj]
         '[fawltypoly.material :as mat])

(-> (mesh/cube! {:name "Sample"})
    (obj/location! [0 0 1])
    (obj/scale! [2 2 0.5])
    (mat/assign! (mat/ensure! "Sample blue" {:color [0.1 0.3 0.8 1]})))

;; A callable returning XYZ data; the grid becomes quad faces.
(geo/parametric-surface (fn [u v] [u v (* u v)])
                        {:u-range [-1 1] :v-range [-1 1]
                         :u-segments 32 :v-segments 32})
```

Use `mesh/create!` to create a fresh object from mesh data, `mesh/replace!` to
update an existing object, and `mesh/smooth!` for shading. Object mutation
functions accept names or object references and return the object for `->`.
`obj/delete!` deletes an object without relying on the current selection.
The original `move`, `rotate`, `delete`, and material `assign` names remain aliases.
`obj/active!` sets the active object; `select` only changes selection.

## Radius-dependent colouring

Materials can map distance from each object's local origin to a colormap:

```clojure
(def radius-material
  (mat/ensure! "AMPS radius"
               {:radius-color {:colormap :viridis
                               :range [0 2]
                               :origin [0 0 0]}
                :roughness 0.55}))
(mat/assign! (obj/object "Sample") radius-material)
```

The same description works in `scene/ensure-scene!`:

```clojure
{:materials {:radius {:radius-color {:colormap :viridis :range [0 2]}}}
 :objects [{:id :surface :mesh some-mesh :material :radius}]}
```

The shader computes `r = length(object-position - origin)`, maps the explicit
radius range to 0..1, clamps it, and feeds a ColorRamp into Principled Base Color.
This follows the object-coordinate radius calculation in the earlier AMPS
examples. Translation, rotation, and unapplied object scale do not change the
colours: distance is measured in mesh-local units, before object transforms.
Changing mesh coordinates or applying transforms can change the colours.

The default origin is `[0 0 0]`, range `[0 1]`, and colormap Viridis. Use one
shared range across objects for quantitative comparison; nothing automatically
normalizes each mesh to its own maximum. Named Matplotlib colormaps such as
`:plasma`, `:cividis`, and reversed `:viridis_r` also work. Matplotlib is loaded
when colormaps are first used and must be installed in Blender's Python.

Colormaps use 32 linearly interpolated stops, converted from Matplotlib's sRGB
values to Blender's linear RGB. `fawltypoly.color/colormap-stops` and `sample`
expose that same mapping for legends. Render lighting and view transforms still
affect the displayed surface colours. Use Material Preview or Rendered mode to
see the shader in Blender's viewport.

`:radius-color` overrides the constant `:color` input. Reevaluating a material
updates the shader without accumulating nodes; omitting `:radius-color` restores
constant colouring and removes only FawltyPoly's radius nodes. Unrelated artist
nodes are preserved. Invalid ranges and colormap names fail before scene changes.

## AMPS and light-matters

FawltyPoly supplies visualization; calculations remain in light-matters.
The adapter accepts the `lightmatters.api.v1.amps/surface` result:
`{:theta [radians ...] :phi [radians ...] :values [[P ...] ...]}`.
Rows index theta, columns index phi, and both axes include their endpoints.
Theta is measured from Blender's +Z axis; phi runs from +X toward +Y.
The adapter removes the duplicate azimuth seam and welds coincident polar rings.
It applies no implicit Wolfram-to-Blender axis permutations.

Export from the light-matters Clojure REPL:

```clojure
(require '[lightmatters.api.v1.amps :as amps] '[charred.api :as json])
(spit "/tmp/amps.json"
      (json/write-json-str (amps/surface "{{1,0,0},{0,0,0},{0,0,0}}")))
```

Then evaluate in Blender's Basilisp REPL:

```clojure
(require '[fawltypoly.amps :as amps-data])
(def grid (amps-data/read-json "/tmp/amps.json"))
(scene/ensure-scene!
 {:collection "Atomic AMPS"
  :objects [{:id :atom/state
             :mesh (amps-data/grid->mesh grid {:radius-scale 2})
             :smooth? true}]})
```

Radius is `radius-scale * P(theta,phi)`, preserving absolute probabilities for
comparison across states. It is not square-rooted or normalized to its maximum.
The adapter clamps negative roundoff down to -1e-12 to zero; larger negative
values, nonfinite values, malformed grids, and inconsistent seams/poles fail.
Change `:negative-tolerance` to adjust that threshold, or use zero to reject all
negative values. Nodal surfaces can have touching lobes and need not be manifold.

### Symbolic equations

An equation can be supplied directly as a quoted s-expression. Parameters and
mesh resolution can be changed without exporting another upstream grid:

```clojure
(require '[fawltypoly.expression :as expression])
(def equation '(* a (expt (sin theta) 2)))

;; A callable numerical equation, also usable outside Blender:
(def p (expression/compile equation {:parameters {'a 0.5}}))
(p 1.5707963267948966 0) ; => 0.5

(scene/ensure-scene!
 {:collection "Symbolic AMPS"
  :objects [{:id :aligned
             :mesh (amps-data/expression->mesh
                    equation {:parameters {'a 0.5} :radius-scale 2
                              :theta-segments 48 :phi-segments 96})
             :smooth? true}]})
```

For an existing Emmy calculation, freeze the scalar expression in light-matters:

```clojure
(require '[emmy.generic :as g] '[lightmatters.qas.angular :as angular])
;; rho is your density operator; do not substitute numerical angles yet.
(spit "/tmp/amps.edn"
      (pr-str (g/freeze (angular/projection-probability rho 'theta 'phi))))
```

Read it in Basilisp and pass it to `expression->mesh`:

```clojure
(def equation (expression/read-expression "/tmp/amps.edn"))
(amps-data/expression->mesh equation {:theta-segments 48 :phi-segments 96})
```

The adapter compiles arithmetic expressions into numerical functions, then
samples them locally. Blender still receives a mesh. It does not perform
symbolic simplification or differentiation and does not run a JVM inside Blender.
The input form remains available for changing parameters and resampling.
Numerical functions are built from an arithmetic-only Python AST rather than
interpreting every expression node for every vertex. Scientific-notation numbers
and ratios are supported in imported forms; reader macros and tagged literals
are rejected, and no input source is evaluated.

Supported operations include `+ - * / expt`, trigonometry and inverse
trigonometry, `exp log sqrt abs`, complex construction, conjugation, and real/
imaginary parts. Wolfram-style `Sin`, `Cos`, `Power`, `**`, and `Complex` aliases
are accepted. `theta`/`th` and `phi`/`ph` are angle aliases, and `pi`/`Pi`/`PI`,
`E`/`e`, and `I` are constants. Parameter keys are exact symbols; these angle
and constant names are reserved. For raw Wolfram forms, first remove nested
contexts with `lightmatters.convert.wolfram/unqualify` before exporting EDN.
This is a scalar arithmetic subset, not a general Emmy or Wolfram interpreter.
Unsupported operators, unbound parameters, and invalid arities fail explicitly.
Forms are interpreted as data using the whitelist, without `eval`.

Complex intermediate values are supported. Final values must be finite and real
within `:imaginary-tolerance` (default 1e-10 times `max(1,abs(real))`). Negative
probabilities use the same `:negative-tolerance` rule as grid imports.
The evaluator is checked against frozen expressions exported from Qas, including
an azimuth-dependent density matrix with complex coherences.

### Three-state comparison

There is also a self-contained spin-1 comparison, built from symbolic equations:

```clojure
(require '[demo.amps :as demo])
(demo/show!)
(demo/show! {:radius-scale 3 :tilt 0.5 :theta-segments 48})
(demo/show! {:colormap :plasma :radius-range [0 2]})
```

The unpolarized state has `P = 1/3`, the stretched state has
`P = cos(theta/2)^4`, and the aligned `m=0` state has
`P = sin(theta)^2/2`. The stretched state is nearly spherical in its overall
dimensions, with its angular origin near the lower tip. The aligned state has
a ring-shaped profile. This follows light-matters' maximal-projection convention,
not an orbital spherical-harmonic density. The solid-angle integral is `4*pi/3`
for all three spin-1 states. All objects retain their identity when reevaluated.
All three share a Viridis radius material with range `[0, radius-scale]` by
default. This maps `P=0..1` to the same colours for every state. Use
`:radius-range` to fix another interval, or `:colormap` to change the palette.
Ordinary `mesh/create!`, `mesh/cube!`, and `light/area!` calls create new objects
each time; repeatable identity belongs to `scene/ensure-scene!`.

To render a labelled comparison with origin and axis guides:

```sh
poetry run python demo/render_amps.py --output dist/amps-comparison.png
```

This starts a separate Blender process and also writes `amps-comparison.blend`.
The camera uses an orthographic projection; guide axes are diagram overlays
at their projected positions so they remain visible through the surfaces.
The X and Z ticks mark one Blender unit; all states use `r=2P`.
The colour bar shows the shared radius range 0..2, using the shader's mapping.

## Circular layouts and paired optical/atomic rings

`layout/circular` places existing object descriptions around a circle. It
retains their IDs, meshes, materials, and scale, and replaces their locations:

```clojure
(require '[fawltypoly.layout :as layout])
(def placed
  (layout/circular surface-descriptions
                   {:radius 4 :center [0 0 0] :normal [0 0 1]
                    :reference [1 0 0] :phase 0 :orientation :fixed}))
```

The ring plane is perpendicular to `:normal`. Angle zero points along the
projection of `:reference` into that plane; increasing angles follow the
right-hand rule around the normal. A parallel reference uses a Cartesian
fallback. Supply `:angles [radians ...]` for nonuniform sampling, one per object;
otherwise angles are evenly spaced without duplicating the endpoint.

The default `:orientation :fixed` preserves each surface's existing rotation.
`:normal`, `:radial`, or `:tangent` explicitly replaces the rotation, pointing
the surface's local +Z axis in that direction. These are presentation choices,
not a calculation of how the state responds to a field.

For a paired comparison, prepare two equally sized vectors with unique IDs:

```clojure
;; optical-grids and atomic-grids come from your light-matters calculation,
;; in matching azimuth order. Symbolic expressions can use expression->mesh instead.
(defn descriptions [group grids]
  (mapv (fn [i grid]
          {:id (keyword group (str i))
           :mesh (amps-data/grid->mesh grid {:radius-scale 1.2})
           :material :radius :smooth? true})
        (range (count grids)) grids))

(def rings
  (layout/paired-rings (descriptions "optical" optical-grids)
                       (descriptions "atomic" atomic-grids)
                       {:optical-radius 4.8 :atomic-radius 3
                        :normal [0 0 1] :orientation :fixed}))

(scene/ensure-scene!
 {:collection "Optical and atomic comparison"
  :materials {:radius {:radius-color {:colormap :viridis :range [0 1.2]}}
              :field {:color [0.65 0.025 0.025 1]}}
  :objects (vec (concat (:optical rings) (:atomic rings)
                        [(layout/field-vector :field/B [0 0 1]
                                              {:origin [0 0 -1.4] :length 2.8
                                               :material :field})]))})
```

Both rings use matching angles; different lengths or duplicate IDs are rejected.
Use `:optical-orientation` and `:atomic-orientation` for separate orientation
policies. Defaults place optical surfaces outside atomic surfaces. The field
arrow's direction is independent of the ring normal, and its `:length` is a
display length, not an inferred magnetic-field magnitude. `layout/ring-guide`
can add a thin guide for either ring using the same center, normal, reference,
and radius options. All returned values are ordinary scene descriptions and
participate in the existing stable-ID update workflow.

The paired demo reuses the actual poster compass: a double-ended red/white
needle, the partially transparent spherical container, and its two angle guides.
The original meshes and material graphs are bundled in
`fawltypoly/assets/compass.blend`; no previous project needs to be installed.
Its center follows `:center`, while the guides follow the ring's reference frame.
The red/north tip follows `:field-direction`, with the white tip opposite it:

```clojure
(require '[demo.circular :as circular])
(circular/show! {:compass? true :compass-radius 1.65 :compass-opacity 0.05})
(circular/show! {:compass? false})
```

By default it is enabled with radius `0.58 * field-length` and its original
transparency shader setting. `:compass-opacity` optionally overrides the shell's
transparent/surface mix factor; omit it to restore the native setting. Hiding
the container leaves the double-ended needle visible. Sizes and transforms can
be reevaluated without duplicating objects, mesh instances, or materials.

Use the authentic asset assembly in any scene:

```clojure
(layout/poster-compass "compass"
                       {:center [0 0 0] :direction [1 1 0.6]
                        :normal [0 0 1] :radius 1.65 :length 2.8})
```

The result contains native `:asset` descriptions such as
`{:id :needle :asset "compass/north" :scale [1 1 1]}`. Supply exactly one of
`:mesh` and `:asset`. The bundled registry supports `compass/north`,
`compass/south`, `compass/shell`, `compass/equator`, and `compass/meridian`.
Materials and smoothing are retained by default; explicit `:material` and
`:smooth?` override them. Setting `:material nil` clears slots; removing the
override restores the native materials. `:asset-opacity` overrides only the
shell's mix factor. Five hidden mesh templates are cached per Blender file;
visible mesh instances retain their identity across updates. The asset library
was created and verified with Blender 5.2.1; older versions are not verified.

The earlier generated compass remains available with
`(circular/show! {:compass-style :procedural})`. In this mode there is a single
arrow, three great-circle guides, and a simple alpha shell. Its default opacity
is `0.035`, and `:compass-thickness` controls the guide lines.

For a generated wire/shell frame alone, `layout/compass-sphere` returns ordinary
procedural object descriptions:

```clojure
(layout/compass-sphere "compass"
                       {:center [0 0 0] :normal [0 0 1]
                        :radius 1.65 :material :guide
                        :shell-material :shell})
;; Define :guide and :shell in the receiving scene's materials map, for example:
;; :shell {:color [0.3 0.4 0.5 1] :opacity 0.04 :roughness 0.8}
```

Omit `:shell-material` for a wire-only compass. Material `:opacity` controls
Principled Alpha from 0 (transparent) to 1 (opaque); its default is the alpha
component of `:color`. Omitting opacity on a later update restores that default.
The shell and guides use stable string IDs beginning with the supplied prefix.

A standalone presentation is available:

```clojure
(require '[demo.circular :as circular])
(circular/show!)
(circular/show! {:surface-count 8 :normal [1 0 0]
                 :field-direction [0 0 1] :optical-radius 5 :atomic-radius 3})
```

This demo uses illustrative spin-1 aligned states in the outer ring and
stretched states in the inner ring. Optical surfaces point radially outward;
atomic surfaces align with the field direction by default. It does not simulate
optical pumping or a magnetic response. Its `:prune? true` applies only to its
owned collection, so reducing `:surface-count` removes omitted demo objects.

Render the paired preset, including angle labels, B arrow, lighting, camera,
and a shared Viridis legend:

```sh
poetry run python demo/render_amps.py --layout paired
```

This writes `dist/amps-paired.png` and `dist/amps-paired.blend` in a separate
Blender process. Choose `--output` to change the destination.

## Actual VMAG equations at different field angles

The paired presentation can now use calculations from `light-matters`, with
bundled cases for magnetic polar angles 0°, 45°, and 90°:

```clojure
(require '[fawltypoly.vmag :as vmag])
(vmag/show! :polar-0)
(vmag/show! :polar-45)
(vmag/show! :polar-90 {:theta-segments 40 :phi-segments 80})
```

These update the same owned `AMPS paired rings` collection used by the demo,
replacing the illustrative states. Use `:collection "Another comparison"` in
the options to keep a separate scene. Both rings contain eight matching beam
azimuths, 0..315° at 45° intervals. The original compass points along the actual
calculated field direction. All surfaces use a common radius/colour scale.

The bundled calculation uses the Doppler-free SEIT model for 87Rb D2,
F=1 -> F'=0, `Bmag=0.1 G`, field azimuth 0, equal beam intensities
`2 mW/cm²`, ground relaxation `1100 s^-1`, zero detuning and OAM `l1=-1,l2=+1`.
Atomic equations come from the solved ground-state density block. Optical
equations come from the upstream vortex-beam polarization API. They are not
rotated copies of the previous illustrative states.

The equations are already in the laboratory frame, with the propagation axis
along +Z. They retain identity object rotations when placed on the rings;
rotating them onto B again would apply the field transformation twice. Changing
the field changes the computed atomic equations, while the incident optical
states remain the same. By default, the displayed ground block is normalized
to unit trace, showing polarization conditional on ground-manifold occupation.
The exported source data retains the original population for provenance.

This is an explicit normalization convention, not the removal of sublevel
populations. Conditional normalization is the default:

```clojure
(vmag/show! :polar-45)
;; Opt out to retain the overall ground-state occupation, as in the old poster:
(vmag/show! :polar-45 {:normalize-ground? false})
```

It evaluates `P / Tr(rho_ground)`, preserving the angular shape, relative
populations and coherences while removing only the overall manifold weight.
Setting `false` retains the joint probability, as in the poster. For spin 1,
its solid-angle AMPS integral is `4*pi/3` times the ground population; the
conditional surface integrates to `4*pi/3`. Metadata
records `:conditional-ground` or `:ground-population` and the ground populations
for all sampled azimuths. The bundled populations range from about 0.99852 to
0.99999, so this choice changes radii by at most about 0.15% for these settings.

Render one field case or all three with identical camera, lighting and scales:

```sh
poetry run python demo/render_amps.py --layout vmag --field-case polar-45
poetry run python demo/render_amps.py --layout vmag --field-case all --output dist/vmag.png
```

The second command writes `vmag-polar-0`, `vmag-polar-45` and `vmag-polar-90`
PNG and Blender files. Surface resolution can change locally because the input
is a symbolic equation in viewing angles, not a precomputed mesh grid. Physical
field parameters are fixed per exported case; new field values require another
upstream calculation. No interpolation or mere mesh rotation substitutes for it.

To regenerate or export more cases, run this script from the light-matters
project root on its Clojure classpath:

```sh
clojure -M /absolute/path/to/fawltypoly/resources/export_vmag.clj /tmp/vmag.edn
```

An optional second argument is an EDN settings file, for example:

```clojure
{:polar-degrees [0 45 90]
 :field-azimuth-degrees 0
 :beam-count 8
 :parameters {:Bmag 0.1 :int1 2.0 :int2 2.0}}
```

The exporter currently pairs the upstream equal-intensity `l1=-1,l2=+1` vortex
beam with the SEIT solver and rejects other beam conventions. It records full
parameters, density matrices, equations and numerical probes. Saved reference
cells are compared when parameters and sampled azimuths match. Load an export
with `(vmag/load-dataset "/tmp/vmag.edn")`, then use
`(vmag/show! dataset :polar-45 {})`. Missing cases fail explicitly.

The bundled reference comparisons agree within `1.8e-13`. See
`fawltypoly/data/README.md` for provenance and normalization details. Verify the
numerical probes and density matrices independently with:

```sh
poetry run python resources/verify_vmag.py
```

## JVM Clojure / MathBox demo

The standalone [Emmy/MathBox example](demo/mathbox/README.md) accepts symbolic
AMPS equations from a Clojure REPL and displays them in a browser. It includes
an interactive tetrahedral spin-2 state with Viridis radius colouring and runs
independently of Blender/Basilisp.

## Verification

```sh
poetry run python tests/run_blender.py
```

The runner starts a separate factory-startup Blender process, leaving open
files untouched. Poetry's Python major/minor version must match Blender's to
share its dependency environment. Verified with Blender 5.2.1 and Python 3.14.7.
Tests cover scene reevaluation, renaming, bounded mesh/material counts, shared
meshes, pruning, invalid descriptions, geometry sampling, helper compatibility,
and reference grids exported from the actual light-matters AMPS API.
Radius-colour tests cover palette conversion, shared shader settings, repeated
updates, switching back to solid colours, and validation before scene mutation.
Layout tests check arbitrary field directions (including axis-aligned and tiny
vectors), Euler rotations against Blender's mathutils, matching ring azimuths,
arrow topology, invalid layouts, and reevaluation with changing surface counts.
The scene, layout, camera, render, and light namespaces now load normally.

## Etymology
Just for fun.

The name comes from the combination of Basilisp and Blender, but you have to know a few things to get the connection... Basil and Polly are main characters in the British sitcom 'FawltyTowers' and are played by Monty Python actors. Monty Python, not the snake, is actually the original inspiration for the name of the 'Python' programming language. Polygons are fundamental to Blender. And, to cap it off, we're dealing with a bridge between two languages and blender and a lot of the humour in Fawlty Towers comes from the communication problems between the characters, particularly when a certain Spanish waiter is involved.
