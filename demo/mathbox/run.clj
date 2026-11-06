(ns run
  (:require [emmy.clerk :as ec]
            [nextjournal.clerk :as clerk]))

(defn -main [& _]
  (ec/serve! {:browse? true :index "amps.clj"
              :watch-paths ["amps.clj"] :port 7777})
  (clerk/show! "amps.clj")
  (println "AMPS notebook: http://localhost:7777 (Ctrl-C to stop)")
  @(promise))
