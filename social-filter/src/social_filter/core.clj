(ns social-filter.core
  (:gen-class)
  (:use
    [twitter.oauth]
    [twitter.callbacks]
    [twitter.callbacks.handlers]
    [twitter.api.restful]
    [twitter.api.search])
  (:import
    (twitter.callbacks.protocols SyncSingleCallback))
  (:require
    [clojure.data.json :as json]))

(defn bind-setting
  [setting]
  (println setting))

(defn load-settings
  [fname]
  (-> (slurp fname)
    (json/read-str :key-fn keyword)))

(defn make-creds
  [settings]
  (let [cred-keys [:app-consumer-key
                   :app-consumer-secret
                   :user-access-token
                   :user-access-token-secret]]
    (->> cred-keys
      (map settings)
      (apply make-oauth-creds))))

(defn handle-search-response
  [response]
  (println "GOT A RESPONSE")
  (clojure.pprint/pprint (:body response)))

(defn -main
  [& args]

  (alter-var-root #'*read-eval* (constantly false))

  (let [settings (load-settings "test.json")
        my-creds (make-creds settings)]
    (search
      :oauth-creds my-creds
      :params {:q (clojure.string/join " " args)}
      :callbacks (SyncSingleCallback.
                   handle-search-response
                   response-throw-error
                   exception-rethrow))))
