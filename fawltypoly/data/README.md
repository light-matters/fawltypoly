# VMAG field-angle equations

`vmag_field_angles.edn` contains equations computed from the actual
`light-matters` SEIT model, exported with `resources/export_vmag.clj`.
It is not a mesh grid or a rotation of the illustrative demo states.

- Field polar angles: 0, 45, 90 degrees from beam +Z; field azimuth 0.
- Field magnitude: 0.1 G; equal sigma+/sigma- intensities: 2 mW/cm² each.
- Eight beam azimuths, 0 through 315 degrees at 45-degree intervals.
- 87Rb D2 F=1 -> F'=0, Doppler-free steady state, gamma=1100 s^-1,
  zero one-photon detuning, OAM l1=-1 and l2=+1. Full parameters are in each case.
- Atomic ground blocks retain their population (no unit-trace renormalization),
  matching the poster's direct use of the three ground-state rows/columns.
  This describes the stored equations: VMAG visualization conditionally
  normalizes them to unit ground trace by default. Use `:normalize-ground? false`
  to display the original population-weighted surfaces.
- Both optical and atomic equations use the laboratory frame with +Z along
  the beam. Neither is rotated again when placed around the ring.

Each state includes its complex density matrix as [re,im] entries, its trace,
a frozen Emmy AMPS expression, and seven Qas numerical reference probes.
The equations remain symbolic in surface angles theta and phi; the physical
parameters determining their coefficients are fixed for each case.

The exporter uses `lightmatters.matter.seit/simulate` (the Commons Math reference
implementation) and `lightmatters.qas.angular/projection-probability`. The
optical states come from `vmag.beam/polarization--b4atoms` and
`lightmatters.light.amps/<-stokes`, unchanged from the upstream visualization.
Metadata records the light-matters commit and SHA-256 hashes of reference cells.

The three computed density-matrix sweeps were compared with saved upstream
`native-fastmath` cells at identical parameters. Maximum absolute differences:
2.33e-15 (0°), 1.45e-13 (45°), 1.74e-13 (90°). This export comparison did not
start Wolfram; the upstream native implementation has its own ADM regressions.

`poetry run python resources/verify_vmag.py` checks positive semidefiniteness,
Hermiticity, traces and every numerical probe without Blender or a JVM.
The Blender integration suite additionally checks case changes, lab-frame
orientation, optical invariance, atomic changes and stable object counts.
