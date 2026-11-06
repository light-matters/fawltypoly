(ns repl-amps
  {:nextjournal.clerk/visibility {:code :hide :result :show}
   :nextjournal.clerk/no-cache true}
  (:require [amps]
            [emmy.clerk :as ec]
            [emmy.env :as e]
            [nextjournal.clerk :as clerk]))

^{::clerk/visibility {:result :hide}}
(ec/install!)

(clerk/md "# AMPS from the REPL

Radius is proportional to the supplied probability. Viridis runs from purple
at radius 0 to yellow at the chosen color maximum. Drag to orbit; scroll to zoom.")

(clerk/tex (e/->TeX (:expression @amps/!repl-view)))

^{::clerk/width :wide}
(:scene @amps/!repl-view)
