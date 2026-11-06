(ns amps-test
  (:require [amps :as amps]
            [clojure.data.json :as json]
            [clojure.edn :as edn]
            [clojure.test :refer [deftest is run-tests]]
            [emmy.env :as e]))

(defn near? [a b]
  (< (Math/abs (- (double a) (double b))) 1e-10))

(deftest expression-inputs
  (doseq [expr [(e// (e/square (e/sin 'theta)) 2)
                '(/ (expt (sin theta) 2) 2)]]
    (let [p (amps/expression->probability expr)
          compiled (fn [t f] (p [t f]))]
      (is (near? 0 (compiled 0 0)))
      (is (near? 0.5 (compiled (/ Math/PI 2) 1.2)))))
  (is (near? 1/3 ((amps/expression->probability 1/3) [0 0])))
  (is (near? 1/3 ((amps/expression->probability '(complex 1/3 0)) [0 0])))
  (is (near? 1 ((amps/expression->probability
                '(expt (cos (/ t 2)) 4) {:theta 't :phi 'p}) [0 1]))))

(deftest azimuth-and-parameter-substitution
  (let [expr (amps/probability amps/tetrahedral-mixing 0 'theta 'phi)
        p (amps/expression->probability expr)
        compiled (fn [t f] (p [t f]))
        theta (Math/acos (/ -1.0 3))]
    (is (near? (/ 1.0 3) (compiled theta 0)))
    (is (near? (/ 49.0 243) (compiled theta (/ Math/PI 3))))
    (is (near? (compiled theta 0) (compiled theta (/ (* 2 Math/PI) 3))))))

(deftest useful-errors
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"nonnegative"
                       (amps/view -0.1 {:theta-samples 3 :phi-samples 3})))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"real-valued"
                       (amps/view '(complex 1 1) {:theta-samples 3 :phi-samples 3})))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"Unbound symbol"
                       (amps/view '(+ a (sin theta)))))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"distinct symbols"
                       (amps/view 1/3 {:theta 't :phi 't})))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"finite and positive"
                       (amps/view 1/3 {:radius-max 0}))))

(deftest upstream-complex-probability
  (let [expr (:coherent (edn/read-string
                        (slurp "../../tests/fixtures/amps_expressions.edn")))
        grid (json/read-str (slurp "../../tests/fixtures/amps_spin1_coherent.json")
                            :key-fn keyword)
        p (amps/expression->probability expr)
        compiled (fn [t f] (p [t f]))]
    (doseq [[i t] (map-indexed vector (:theta grid))
            [j f] (map-indexed vector (:phi grid))]
      (is (near? (get-in grid [:values i j]) (compiled t f))))))

(defn -main [& _]
  (let [{:keys [fail error]} (run-tests 'amps-test)]
    (shutdown-agents)
    (when (pos? (+ fail error)) (System/exit 1))))
