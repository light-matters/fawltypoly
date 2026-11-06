# AMPS reference grids

These grids were exported from the local `light-matters` working tree using
`lightmatters.api.v1.amps/surface`, with `:n-theta 8 :n-phi 16`.
Each JSON file records its input density matrix in `source.rho`.

The stretched spin-1 state checks the demo against the upstream calculation.
The coherent density matrix has azimuth-dependent probabilities and checks the
adapter's axis and row/column conventions. The files retain the upstream
normalization, duplicated azimuth endpoint, and polarization moments.

`amps_expressions.edn` contains scalar expressions exported using
`(emmy.generic/freeze (lightmatters.qas.angular/projection-probability
rho 'theta 'phi))`, without manual simplification. Its stretched and coherent
states match the JSON density matrices. The aligned state is `|1,0><1,0|`, and
the mixed state is `I/3`. Keeping complex intermediates in these forms exercises
the symbolic adapter's phase and conjugation behavior.

To regenerate inside a light-matters REPL:

```clojure
(require '[lightmatters.api.v1.amps :as amps] '[charred.api :as json])
(def rho "{{1,0,0},{0,0,0},{0,0,0}}") ; or source.rho from the coherent fixture
(spit "/tmp/amps.json"
      (json/write-json-str
       (assoc (amps/surface rho :n-theta 8 :n-phi 16)
              :source {:namespace "lightmatters.api.v1.amps/surface" :rho rho})))
```
