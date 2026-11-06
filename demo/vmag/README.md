# VMAG field-angle project

Run the commands below from the repository root, with the repository configured
as Blender’s Basilisp Project Directory. This project is not installed with the
FawltyPoly library. It depends on `fawltypoly.api.v1`.

The paired presentation uses calculations from `light-matters`, with
bundled cases for magnetic polar angles 0°, 45°, and 90°:

```clojure
(require '[demo.vmag.plot :as vmag])
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
clojure -M /absolute/path/to/fawltypoly/demo/vmag/export.clj /tmp/vmag.edn
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
[data/README.md](data/README.md) for provenance and normalization details. Verify the
numerical probes and density matrices independently with:

```sh
poetry run python demo/vmag/verify.py
```
