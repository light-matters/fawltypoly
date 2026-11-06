# Emmy / MathBox AMPS example

Run with the Clojure CLI (JVM Clojure, independently of Blender/Basilisp):

```sh
cd demo/mathbox
clojure -M:run
```

Open <http://localhost:7777> if the browser does not open automatically.
Stop with Ctrl-C. The first run downloads Maven dependencies; the browser also
needs network access for Emmy's prebuilt Clerk JavaScript bundle and CSS.
Versions are pinned to Emmy Viewers' documented Clerk setup.

## Pass equations from the REPL

Start `clojure -M` in this directory, then pass an Emmy expression directly:

```clojure
(require '[amps :as amps] '[emmy.env :as e])

;; Spin-1 aligned state. No function definition is needed.
(amps/show! (e// (e/square (e/sin 'theta)) 2))

;; Existing expressions and frozen/quoted expressions work too.
(amps/show! '(expt (cos (/ theta 2)) 4))
(amps/show! 1/3) ; unpolarized spin-1 state

;; The tetrahedral example, supplied as an expression rather than a function:
(amps/show! (amps/probability amps/tetrahedral-mixing 0 'theta 'phi))

;; Optional display settings and alternative variable names:
(amps/show! '(expt (cos (/ t 2)) 4)
            {:theta 't :phi 'p :radius-scale 2 :radius-max 2})
```

The first `show!` starts Clerk on port 7777 and opens the plot. Later calls
replace the plot in the same browser page. Use `view` instead of `show!` to
return a scene for embedding inside another Clerk notebook.
Pass a real, finite, nonnegative probability expression in `theta` and `phi`;
substitute any other free parameters before passing it in. Operator names in
frozen expressions must be exported by `emmy.env`. This helper uses Emmy's
expression evaluator rather than Clojure `eval`.
REPL plots sample the equation on the JVM before sending positions and colors
to MathBox. This supports upstream complex intermediates without requiring
symbolic simplification. Imaginary residuals and negative roundoff up to
`1e-12` are tolerated; other complex, negative, or nonfinite samples fail
before replacing the current plot. Optional `:theta-samples` and `:phi-samples`
control resolution (defaults 129 and 193).

Run the expression and upstream reference-grid checks with `clojure -M -m amps-test`.

`amps.clj` is the notebook. It starts with the spin-2 pure state
`(|2,2> + sqrt(2)|2,-1>)/sqrt(3)`, with tetrahedrally arranged lobes.
Sliders change the relative phase, mixing angle, and radius scale in the browser.
Changing phase by delta rotates the pattern about +Z by delta/3.
Drag to orbit; scroll to zoom. To reset, reload the notebook from the REPL:

```clojure
(require '[nextjournal.clerk :as clerk])
(clerk/show! "amps.clj")
```

The surface uses viridis vertex colors based on Cartesian radius, with a fixed
color range of 0 (purple) to 1 (yellow). The initial tetrahedral state's lobe
tips have radius 1. Values above 1 saturate at yellow, so changing the state or
radius scale does not silently renormalize the colors. Change `:radius-max` in
the notebook to adjust the upper end of the color scale. The palette uses 17
samples of Matplotlib viridis with linear interpolation, retaining 3D shading.

The probability is the maximal-projection probability `P(m_n=2)`, matching the
AMPS convention in the parent project. Radius is `radius-scale * P`; there is
no implicit square root or normalization. Its solid-angle integral is `4*pi/5`.
The formula is written using Emmy operations, and MathBox compiles the
parameterization to JavaScript. No upstream physics service is required.
Use `amps/show!` to experiment with another angular expression.

This is a sampled visualization. The theta/phi parameterization includes the
azimuth seam and collapses at the poles and probability zeros; it is not a
welded mesh intended for manufacturing or mesh export.

API references: [Emmy Viewers setup](https://github.com/mentat-collective/emmy-viewers#quickstart-via-clerk),
[parametric surfaces](https://cljdoc.org/d/org.mentat/emmy-viewers/0.3.2/api/emmy.mathbox.plot).
