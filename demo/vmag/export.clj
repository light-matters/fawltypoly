(ns demo.vmag.export
  "Run from the light-matters project classpath. Export scalar AMPS equations,
   not a sampled surface grid. The physics stays in the upstream SEIT/Qas code."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [emmy.complex :as c]
            [emmy.generic :as g]
            [lightmatters.example.vmag.beam :as beam]
            [lightmatters.light.amps :as optical]
            [lightmatters.matter.seit :as seit]
            [lightmatters.qas.angular :as angular]
            [lightmatters.qas.dirac :as d]
            [lightmatters.qas.operator :as op]
            [tablecloth.api :as tc]))

(def base-parameters
  {:Bmag 0.1 :Bpolar 0.0 :Bazimuth 0.0 :gamma 1100.0 :CapitalDelta10 0.0
   :length 0.075 :density 10000000000 :int1 2.0 :int2 2.0
   :Phi1 'Phi :Phi2 'Phi :l1 -1.0 :l2 1.0})

(def probes [[0.0 0.0] [0.4 0.7] [1.1 2.0] [(/ Math/PI 2) 0.0]
             [(/ Math/PI 2) (/ Math/PI 2)] [2.4 4.1] [Math/PI 1.7]])

(defn- freeze-state [rho rows]
  {:expression (g/freeze (angular/projection-probability rho 'theta 'phi))
   :density-matrix rows
   :trace (double (reduce + (map #(first (get-in rows [% %])) (range 3))))
   :probes (mapv (fn [[theta phi]] [theta phi (double (g/real-part (angular/projection-probability rho theta phi)))]) probes)})

(defn- pair [z] [(double (g/real-part z)) (double (g/imag-part z))])

(defn- optical-states [phis]
  (mapv (fn [row]
          (let [rho (optical/<-stokes [(:s1 row) (:s2 row) (:s3 row)])
                ms (angular/ms 1)
                rows (mapv (fn [a] (mapv #(pair (op/element rho (angular/space 1) a %)) ms)) ms)]
            (freeze-state rho rows)))
        (tc/rows (beam/polarization--b4atoms phis) :as-maps)))

(defn- atomic-state [dv]
  ;; ADM/SEIT basis is (+1,0,-1,excited), quantized along lab +Z, not along B.
  ;; Match the original poster: retain the ground-block population, without
  ;; normalizing away the excited-state population.
  (let [rows (mapv (fn [a] (mapv #(nth dv (+ (* 4 a) %)) (range 3))) (range 3))
        complex-rows (mapv (fn [row] (mapv (fn [[re im]] (c/complex re im)) row)) rows)]
    (freeze-state (d/operator* complex-rows [3]) rows)))

(defn- sha256 [file]
  (let [digest (java.security.MessageDigest/getInstance "SHA-256")]
    (format "%064x" (java.math.BigInteger. 1 (.digest digest (java.nio.file.Files/readAllBytes (.toPath (io/file file))))))))

(defn- reference-check [params phis dv]
  (let [index (long (Math/round (/ (:Bpolar params) (/ Math/PI 12))))
        file (io/file "data/field-rotation"
                      (format "int-%s_bmag-%s_theta-%02d.edn" (:int1 params) (:Bmag params) index))]
    (if (and (.exists file) (= 0.0 (:Bazimuth params)))
      (let [saved (edn/read-string (slurp file))]
        (if (= params (:params saved))
          (let [indices (mapv (fn [phi]
                                (or (first (keep-indexed (fn [i x] (when (< (abs (- x phi)) 1e-12) i)) (:phis saved)))
                                    (throw (ex-info "Requested beam azimuth is absent from saved reference" {:phi phi})))) phis)
                reference (mapv #(nth (:dv saved) %) indices)
                difference (reduce max 0.0 (map #(abs (- %1 %2)) (flatten dv) (flatten reference)))]
            (when (> difference 1e-9) (throw (ex-info "SEIT disagrees with saved reference" {:max-error difference})))
            {:status :matched :engine (get saved :engine :wolfram-adm)
             :file (str file) :sha256 (sha256 file) :max-abs-difference difference})
          {:status :parameters-differ}))
      {:status :not-available})))

(defn export!
  [{:keys [output polar-degrees field-azimuth-degrees beam-count parameters]
    :or {polar-degrees [0 45 90] field-azimuth-degrees 0 beam-count 8 parameters {}}}]
  (when-not (and output (integer? beam-count) (pos? beam-count) (seq polar-degrees)
                 (every? #(and (number? %) (<= 0 % 180)) polar-degrees))
    (throw (ex-info "Invalid export settings" {})))
  (let [base (assoc (merge base-parameters parameters) :Bazimuth (Math/toRadians field-azimuth-degrees))
        _ (when-not (and (= (:int1 base) (:int2 base)) (= -1.0 (:l1 base)) (= 1.0 (:l2 base)))
            (throw (ex-info "This exporter pairs the existing equal-intensity, l1=-1/l2=+1 vortex-beam API" {})))
        phis (mapv #(* 2 Math/PI (/ % beam-count)) (range beam-count))
        dataset {:format "fawltypoly.vmag/1" :frame :lab-z :normalization :ground-population
                 :source {:model 'lightmatters.matter.seit/simulate
                          :amps 'lightmatters.qas.angular/projection-probability
                          :optical 'lightmatters.example.vmag.beam/polarization--b4atoms
                          :transition "87Rb D2 F=1 -> F'=0" :regime :doppler-free-steady-state
                          :light-matters-commit (System/getProperty "fawltypoly.light-matters-commit" "unrecorded")}
                 :beam-azimuths phis :optical (optical-states phis)
                 :cases (mapv (fn [degrees]
                                (let [params (assoc base :Bpolar (Math/toRadians degrees))
                                      dv (seit/simulate params phis)
                                      result {:id (keyword (str "polar-" degrees)) :polar-degrees degrees
                                              :params params :atomic (mapv atomic-state dv)
                                              :reference (reference-check params phis dv)}]
                                  (println "Calculated field polar angle" degrees (:reference result))
                                  result)) polar-degrees)}]
    (io/make-parents output)
    (spit output (pr-str dataset))
    (println "Exported" output)
    dataset))

(when (seq *command-line-args*)
  (let [[output config-file] *command-line-args*]
    (export! (assoc (if config-file (edn/read-string (slurp config-file)) {}) :output output))))
