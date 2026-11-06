(ns amps
  "An Emmy/MathBox notebook for a spin-2 angular momentum probability surface."
  {:nextjournal.clerk/visibility {:code :hide :result :hide}}
  (:require [clojure.java.io :as io]
            [emmy.clerk :as ec]
            [emmy.env :as e]
            [emmy.expression :as x]
            [emmy.leva :as leva]
            [emmy.mathbox :as box]
            [emmy.mathbox.compile :as mc]
            [emmy.mathbox.plot :as plot]
            [emmy.viewer :as ev]
            [emmy.viewer.compile :as vc]
            [nextjournal.clerk :as clerk]))

(ec/install!)

^{::clerk/visibility {:result :show}}
(clerk/md
 "# A tetrahedral spin-2 AMPS

The state is a coherent superposition of the m=2 and m=-1 states:

$$\\lvert\\psi\\rangle=\\cos\\eta\\,\\lvert2,2\\rangle+
e^{i\\delta}\\sin\\eta\\,\\lvert2,-1\\rangle.$$

At the initial mixing angle, $\\tan\\eta=\\sqrt{2}$, its four lobes point
toward the vertices of a regular tetrahedron.

The radius is $r=s\\,P(m_{\\mathbf n}=2)$, with no square root or maximum
normalization. The probability integrates to $4\\pi/5$ over solid angle.
Viridis encodes radius on a fixed scale: purple at 0 and yellow at 1;
larger radii retain yellow. The initial four lobe tips have radius 1.
Drag to orbit and scroll to zoom. Change **phase** to rotate the three lower
lobes, **mixing** to change the state, or **radius-scale** to resize it.
Angles are in radians; theta is measured from +Z and phi from +X toward +Y.")

(def tetrahedral-mixing (Math/atan (Math/sqrt 2.0)))

(defn probability
  "P(m_n=2) for cos(mixing)|2,2> + exp(i phase)sin(mixing)|2,-1>.
   The spin-coherent ket has coefficients
   sqrt(choose(4,2-m))*c^(2+m)*s^(2-m)*exp(i*(2-m)*phi).
   Expressing the modulus squared as two real squares avoids complex values
   in the browser and keeps numerical probabilities nonnegative."
  [mixing phase theta phi]
  (let [c (e/cos (e// theta 2))
        s (e/sin (e// theta 2))
        a (e/* (e/cos mixing) (e/expt c 4))
        b (e/* (e/sin mixing) 2 c (e/expt s 3))
        angle (e/- phase (e/* 3 phi))]
    (e/+ (e/square (e/+ a (e/* b (e/cos angle))))
         (e/square (e/* b (e/sin angle))))))

(defn surface
  "An Emmy-compatible [theta phi] -> [x y z] parameterization.
   Replace probability to plot another real scalar angular expression."
  [mixing phase radius-scale]
  (fn [[theta phi]]
    (let [r (e/* radius-scale (probability mixing phase theta phi))]
      [(e/* r (e/sin theta) (e/cos phi))
       (e/* r (e/sin theta) (e/sin phi))
       (e/* r (e/cos theta))])))

(def viridis
  "17 sRGB samples from Matplotlib's viridis, interpolated in the browser."
  [[0.267004 0.004874 0.329415] [0.282327 0.094955 0.417331]
   [0.278826 0.175490 0.483397] [0.258965 0.251537 0.524736]
   [0.229739 0.322361 0.545706] [0.199430 0.387607 0.554642]
   [0.172719 0.448791 0.557885] [0.149039 0.508051 0.557250]
   [0.127568 0.566949 0.550556] [0.120081 0.622161 0.534946]
   [0.153894 0.680203 0.504172] [0.239374 0.735588 0.455688]
   [0.360741 0.785964 0.387814] [0.506271 0.828786 0.300362]
   [0.668054 0.861999 0.196293] [0.835270 0.886029 0.102646]
   [0.993248 0.906157 0.143936]])

(defn radius-colored-surface
  "Compile an Emmy surface, then sample matching position and RGBA buffers.
   MathBox's high-level parametric-surface only exposes a uniform color, so
   use its underlying Area/Surface primitives for vertex colors instead.
   Colors are based on actual Cartesian radius, clamped to [0, radius-max]."
  [{:keys [radius-max] :or {radius-max 1.0} :as opts}]
  (let [[binding {:keys [f]}] (mc/compile-3d opts :f 2)
        positions (str (gensym "amps-positions-"))
        colors (str (gensym "amps-colors-"))
        sampling {:width 129 :height 193 :items 1 :live false
                  :rangeX [0 Math/PI] :rangeY [0 (* 2 Math/PI)]}
        color-expr
        `(fn [emit# theta# phi#]
           (~f
            (fn [x# y# z#]
              (let [radius# (js/Math.sqrt (+ (* x# x#) (* y# y#) (* z# z#)))
                    t# (* 16 (max 0 (min 1 (/ radius# ~radius-max))))
                    i# (min 15 (js/Math.floor t#))
                    w# (- t# i#)
                    palette# ~viridis
                    a# (nth palette# i#)
                    b# (nth palette# (inc i#))
                    channel# (fn [k#]
                               (+ (* (- 1 w#) (nth a# k#))
                                  (* w# (nth b# k#))))]
                (emit# (channel# 0) (channel# 1) (channel# 2) 1)))
            theta# phi#))]
    (ev/fragment
     (vc/wrap
      [binding]
      (box/group
       (box/area (assoc sampling :id positions :channels 3 :expr f))
       (box/area (assoc sampling :id colors :channels 4 :expr color-expr))
       (box/surface {:points (str "#" positions) :colors (str "#" colors)
                     :color "white" :shaded true :opacity 1
                     :lineX false :lineY false :zOrder 25})))
     plot/scene)))

(def scene-options
  {:range [[-1.25 1.25] [-1.25 1.25] [-1.25 1.25]]
   :scale [1 1 1]
   :camera [0.7 -1.4 0.65]
   :container {:style {:height "520px" :width "100%"}}
   :axes {:x {:ticks false} :y {:ticks false} :z {:ticks false}}
   :grids []})

(defn expression->probability
  "Accept an Emmy scalar expression, a frozen expression, or a constant.
   Only theta and phi may remain free (rename them with :theta/:phi).
   Uses Emmy expression evaluation, not Clojure eval."
  ([expression] (expression->probability expression {}))
  ([expression {:keys [theta phi] :or {theta 'theta phi 'phi}}]
   (when-not (and (symbol? theta) (symbol? phi) (not= theta phi))
     (throw (ex-info ":theta and :phi must be distinct symbols" {})))
   (let [operators (into {} (for [[sym v] (ns-publics 'emmy.env)
                                :when (ifn? @v)]
                            [sym @v]))
         variables (fn [t p]
                     (fn [sym _]
                       (cond (= sym theta) t
                             (= sym phi) p
                             :else (throw (ex-info
                                           "Unbound symbol in AMPS expression; substitute parameters first"
                                           {:symbol sym :theta theta :phi phi})))))]
     ;; Check bindings/operators before sampling. Keep complex arithmetic in
     ;; Emmy on the JVM; its numerical JS compiler accepts real scalars only.
     (x/evaluate expression (variables theta phi) operators)
     (fn [[t p]]
       (let [value (x/evaluate expression (variables t p) operators)
             re (double (e/real-part value))
             im (double (e/imag-part value))]
         (when-not (and (Double/isFinite re) (Double/isFinite im)
                        (<= (Math/abs im) 1e-12) (>= re -1e-12))
           (throw (ex-info "AMPS probability must be finite, real-valued, and nonnegative"
                           {:theta t :phi p :real re :imaginary im})))
         (max 0.0 re))))))

(defn- radius-color [radius radius-max]
  (let [t (* 16 (max 0 (min 1 (/ radius radius-max))))
        i (min 15 (int t)) w (- t i)]
    (conj (mapv (fn [a b] (+ (* (- 1 w) a) (* w b)))
                (nth viridis i) (nth viridis (inc i))) 1.0)))

(defn view
  "Build a viridis AMPS scene directly from an Emmy probability expression.
   Options: :radius-scale (3), :radius-max (1), :theta/:phi (symbols),
   :theta-samples (129), :phi-samples (193), and :scene (camera/range overrides).
   Samples on the JVM so upstream complex intermediates work unchanged."
  ([expression] (view expression {}))
  ([expression {:keys [radius-scale radius-max scene theta-samples phi-samples]
                :or {radius-scale 3.0 radius-max 1.0
                     theta-samples 129 phi-samples 193}
                :as options}]
   (doseq [[k value] [[:radius-scale radius-scale] [:radius-max radius-max]]]
     (when-not (and (number? value) (Double/isFinite (double value)) (pos? value))
       (throw (ex-info "Radius scale and color maximum must be finite and positive"
                       {k value}))))
   (doseq [n [theta-samples phi-samples]]
     (when-not (and (integer? n) (>= n 2))
       (throw (ex-info "Sample counts must be integers of at least 2" {}))))
   (let [p (expression->probability expression options)
         rows (mapv (fn [j]
                      (let [phi (* 2 Math/PI (/ j (dec phi-samples)))]
                        (mapv (fn [i]
                                (let [theta (* Math/PI (/ i (dec theta-samples)))
                                      r (* radius-scale (p [theta phi]))]
                                  {:position [(* r (Math/sin theta) (Math/cos phi))
                                              (* r (Math/sin theta) (Math/sin phi))
                                              (* r (Math/cos theta))]
                                   :color (radius-color r radius-max)}))
                              (range theta-samples))))
                    (range phi-samples))
         positions (str (gensym "amps-positions-"))
         colors (str (gensym "amps-colors-"))
         sampling {:width theta-samples :height phi-samples :items 1 :live false}]
     (plot/scene
      (merge scene-options scene)
      (box/group
       (box/area (assoc sampling :id positions :channels 3
                        :data (mapv #(mapv :position %) rows)))
       (box/area (assoc sampling :id colors :channels 4
                        :data (mapv #(mapv :color %) rows)))
       (box/surface {:points (str "#" positions) :colors (str "#" colors)
                     :color "white" :shaded true :opacity 1
                     :lineX false :lineY false :zOrder 25}))))))

(defonce ^:no-doc !repl-view (atom nil))
(defonce ^:private !repl-server-started? (atom false))

(defn show!
  "Show an Emmy AMPS expression in the browser, starting Clerk if necessary.
   Subsequent calls replace the previous REPL plot. Options are as for view."
  ([expression] (show! expression {}))
  ([expression options]
   ;; Build before replacing the current view, so errors leave it intact.
   (let [scene (view expression options)
         notebook (.getPath (io/file (io/resource "repl_amps.clj")))]
     (reset! !repl-view {:expression expression :scene scene :options options})
     (when-not @!repl-server-started?
       (ec/serve! {:browse? true :port 7777 :index notebook})
       (reset! !repl-server-started? true))
     (clerk/show! notebook))))

^{::clerk/visibility {:result :show} ::clerk/width :wide}
(ev/with-let [!state {:mixing tetrahedral-mixing
                     :phase 0.0
                     :radius-scale 3.0}]
  (plot/scene
   scene-options
   (leva/controls
    {:atom !state
     :folder {:name "Spin-2 state"}
     :schema {:mixing {:min 0 :max (/ Math/PI 2) :step 0.001}
              :phase {:min 0 :max (* 2 Math/PI) :step 0.01}
              :radius-scale {:min 0.5 :max 6 :step 0.05}}})
   (radius-colored-surface
    {:f (ev/with-params
          {:atom !state :params [:mixing :phase :radius-scale]}
          surface)
     :simplify? false
     :radius-max 1.0})))
