import time
import base64
from datetime import datetime
from threading import Lock

import config_mgr
import stats_mgr
import models_library
import model_persistence.models_factory
import model_persistence.anomaly_calc_factory
import utils.anomalies_handler
import utils.logger
DEBUG = False


class AnomalyDetector:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance(kafka_producer=None):
        if AnomalyDetector.__instance is None:
            AnomalyDetector(kafka_producer)
        return AnomalyDetector.__instance

    def __init__(self, kafka_producer):
        AnomalyDetector.__threads_lock.acquire()
        try:
            if AnomalyDetector.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                if kafka_producer is None:
                    raise Exception("On the first call to this class the kafka producer must be given.")

                AnomalyDetector.__instance = self
                self._kafka_producer = kafka_producer
                self._config_mgr = config_mgr.ConfigMgr.get_instance()
                self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
                self._logger = utils.logger.Logger(__file__, "AnomalyDetector")
                self._models_library = models_library.ModelsLibrary.get_instance()
                self._models_factory = model_persistence.models_factory.ModelFactory()
                self._anomalies_handler = utils.anomalies_handler.AnomaliesHandler.get_instance(self._kafka_producer)
                self._last_logged_message_about_too_many_models = 0
                self.EXIT_ALL_THREADS_FLAG = False
        finally:
            AnomalyDetector.__threads_lock.release()

    def detect_anomaly(self, metric):
        """
        The main method of the service - whenever a metric is received, it is parsed by the parse_metric_message method
        and then sent to this method for feeding the data to the correct model and detect anomalies
        :param metric:
        :return:
        """

        try:
            self._logger.debug("detect_anomaly", "Received the metric mentioned.", metric=str(metric))

            if self._models_library.get_instance().get_models_count() < self._config_mgr.get("max_allowed_models"):
                models_number_below_configured_limit = True
            else:
                models_number_below_configured_limit = False
                if (time.time() - self._last_logged_message_about_too_many_models) > self._config_mgr.get("minimum_seconds_between_model_over_quota_log_messages"):
                    self._logger.warn("detect_anomaly", "Currently the number of models/anomaly_likelihood_calculators loaded is exceeds the configured quota. CANNOT CREATE NEW MODELS.", metric=str(metric))
                    self._last_logged_message_about_too_many_models = time.time()

            anomaly_detection_model = self._models_factory.get_anomaly_model(metric, models_number_below_configured_limit)

            self.__threads_lock.acquire()
            anomaly_likelihood_calc = self._models_factory.get_anomaly_likelihood_calc(metric, models_number_below_configured_limit)
            self.__threads_lock.release()

            prediction_model = self._models_factory.get_prediction_model(metric, models_number_below_configured_limit)
            prediction, prediction_made = self._get_prediction(metric, models_number_below_configured_limit, prediction_model)
            anomaly_detection_made, anomaly_direction, anomaly_likelihood, anomaly_score = self._do_anomaly_detection(anomaly_detection_model, anomaly_likelihood_calc, metric, prediction)
            self._report_found_anomalies(anomaly_detection_made, anomaly_direction, anomaly_likelihood, anomaly_score, metric, models_number_below_configured_limit, prediction, prediction_made)

            if self.EXIT_ALL_THREADS_FLAG:
                return

            self._stats_mgr.set("last_metric_timestamp", int(metric["metric_timestamp"]))
            self._stats_mgr.up("metrics_successfully_processed")

        except Exception as ex:
            self._logger.warn("detect_anomaly", "Failed to analyze that metric due to an exception.", metric=str(base64.b64encode(str(metric))), exception_type=str(type(ex).__name__), exception_message=str(ex.message))

    def _report_found_anomalies(self, anomaly_detection_made, anomaly_direction, anomaly_likelihood, anomaly_score, metric, models_number_below_configured_limit, prediction, prediction_made):
        anomaly_reported = False
        if anomaly_detection_made:
            if anomaly_likelihood is not None \
                    and anomaly_score is not None \
                    and anomaly_likelihood >= self._config_mgr.get("anomaly_likelihood_threshold_for_reporting") \
                    and anomaly_score >= self._config_mgr.get("anomaly_score_threshold_for_reporting") \
                    and (prediction_made is False or prediction["confidence_level"] >= self._config_mgr.get("minimum_confidence_for_reporting")):
                if prediction_made:
                    self._anomalies_handler.report_anomaly(metric=metric, anomaly_info={
                        "htm_anomaly_score": float(anomaly_score),
                        "htm_anomaly_likelihood": float(anomaly_likelihood),
                        "anomaly_score": float(anomaly_likelihood * anomaly_direction * 100),
                        "timestamp: ": datetime.fromtimestamp(metric["metric_timestamp"]).isoformat(),
                        "metric: ": metric["metric_name"],
                        "prediction: ": prediction,
                        "value: ": float(metric["metric_value"])
                    })
                    anomaly_reported = True
                else:
                    self._anomalies_handler.report_anomaly(metric=metric, anomaly_info={
                        "htm_anomaly_score": float(anomaly_score),
                        "htm_anomaly_likelihood": float(anomaly_likelihood),
                        "anomaly_score": float(anomaly_likelihood * anomaly_direction * 100),
                        "timestamp: ": datetime.fromtimestamp(metric["metric_timestamp"]).isoformat(),
                        "metric: ": metric["metric_name"],
                        "prediction: ": None,
                        "value: ": float(metric["metric_value"])
                    })
                    anomaly_reported = True
            else:
                # No alert is needed, no anomaly was detected
                pass
            try:
                self._kafka_producer.send(topic=self._config_mgr.get("anomalies_metrics_kafka_topic"), value=(self._config_mgr.get("metrics_prefix").replace("{{#anomaly_metric}}", "anomaly_score") + "." + metric["metric_name"] + " " + str(anomaly_score) + " " + str(metric["metric_timestamp"])).encode('utf-8'))
                self._kafka_producer.send(topic=self._config_mgr.get("anomalies_metrics_kafka_topic"), value=(self._config_mgr.get("metrics_prefix").replace("{{#anomaly_metric}}", "anomaly_likelihood") + "." + metric["metric_name"] + " " + str(anomaly_likelihood) + " " + str(metric["metric_timestamp"])).encode('utf-8'))
                self._kafka_producer.send(topic=self._config_mgr.get("anomalies_metrics_kafka_topic"), value=(self._config_mgr.get("metrics_prefix").replace("{{#anomaly_metric}}", "anomaly_direction") + "." + metric["metric_name"] + " " + str(anomaly_direction) + " " + str(metric["metric_timestamp"])).encode('utf-8'))
            except Exception as ex:
                self._logger.warn("_report_found_anomalies", "Failed to report anomaly info to kafka  (Value: " + str(metric["metric_value"]) + ", Anomaly score: " + str(anomaly_score) + ", Prediction: " + str(prediction) + ", AnomalyLikelihood: " + str(anomaly_likelihood) + ", AnomalyReported: " + str(anomaly_reported) + ")", metric=str(metric["metric_name"]), exception_message=str(ex.message), exception_type=str(type(ex).__name__))
        else:
            if models_number_below_configured_limit:
                self._logger.error("_report_found_anomalies", "Could not load/create a anomaly detection model for this metric", metric=str(metric))
            else:
                # The number of models is above the limit. Since it is the user who set this threshold, no alert is necessary here
                pass

        return anomaly_reported

    def _do_anomaly_detection(self, anomaly_detection_model, anomaly_likelihood_calc, metric, prediction):
        anomaly_detection_made = False
        anomaly_likelihood = None
        anomaly_score = None
        anomaly_direction = 0
        if anomaly_detection_model:
            anomaly_detection_result = anomaly_detection_model.run({
                "timestamp": datetime.fromtimestamp(metric["metric_timestamp"]),
                "value": metric["metric_value"]
            })

            try:
                anomaly_score = anomaly_detection_result.inferences["anomalyScore"]
                if anomaly_score is None:
                    self._logger.warn("_do_anomaly_detection", "No anomaly_score found. Faking a zero anomaly_score", metric=str(metric))
                    anomaly_score = 0
            except KeyError:
                self._logger.warn("_do_anomaly_detection", "Failed to get an anomaly_score due to a KeyError exception. Faking a zero anomaly_score", metric=str(metric))
                anomaly_score = 0

            anomaly_likelihood = anomaly_likelihood_calc.anomalyProbability(
                value=metric["metric_value"],
                anomalyScore=anomaly_score,
                timestamp=datetime.fromtimestamp(metric["metric_timestamp"])
            )

            if anomaly_likelihood is not None \
                    and anomaly_score is not None \
                    and anomaly_likelihood >= self._config_mgr.get("anomaly_likelihood_threshold_for_reporting") \
                    and anomaly_score >= self._config_mgr.get("anomaly_score_threshold_for_reporting") \
                    and prediction["confidence_level"] >= self._config_mgr.get("minimum_confidence_for_reporting"):
                if prediction["value"] > metric["metric_value"]:
                    anomaly_direction = 1
                else:
                    anomaly_direction = -1

            anomaly_detection_made = True
        return anomaly_detection_made, anomaly_direction, anomaly_likelihood, anomaly_score

    def _get_prediction(self, metric, models_number_below_configured_limit, prediction_model):
        prediction = {"value": 0, "timestamp": (metric["metric_timestamp"] - self._stats_mgr.get("last_metric_timestamp")) * self._config_mgr.get("prediction_steps")}
        prediction_made = False
        if prediction_model:
            prediction_result = prediction_model.run({
                "timestamp": datetime.fromtimestamp(metric["metric_timestamp"]),
                "value": metric["metric_value"]
            })

            try:
                if "multiStepBestPredictions" in prediction_result.inferences and self._stats_mgr.get("last_metric_timestamp") > 0:
                    prediction_value = prediction_result.inferences["multiStepBestPredictions"][self._config_mgr.get("prediction_steps")]
                    prediction = {
                        "timestamp": metric["metric_timestamp"] + ((metric["metric_timestamp"] - self._stats_mgr.get("last_metric_timestamp")) * self._config_mgr.get("prediction_steps")),
                        "value": prediction_value,
                        "confidence_level": prediction_result.inferences["multiStepPredictions"][self._config_mgr.get("prediction_steps")][prediction_value]
                    }
                    prediction_made = True
                else:
                    prediction = None
            except KeyError:
                self._logger.warn("_get_prediction", "Failed to get a prediction due to a KeyError exception. Faking a zero prediction", metric=str(metric))
                prediction = {"value": 0, "timestamp": (metric["metric_timestamp"] - self._stats_mgr.get("last_metric_timestamp")) * self._config_mgr.get("prediction_steps")}

            try:
                self._kafka_producer.send(topic=self._config_mgr.get("predictions_metrics_kafka_topic"), value=(self._config_mgr.get("metrics_prefix").replace("{{#anomaly_metric}}", "prediction") + "." + metric["metric_name"] + " " + str(prediction["value"]) + " " + str(prediction["timestamp"])).encode('utf-8'))
                self._kafka_producer.send(topic=self._config_mgr.get("predictions_metrics_kafka_topic"), value=(self._config_mgr.get("metrics_prefix").replace("{{#anomaly_metric}}", "prediction_confidence") + "." + metric["metric_name"] + " " + str(prediction["confidence_level"]) + " " + str(prediction["timestamp"])).encode('utf-8'))
            except Exception as ex:
                self._logger.warn("_get_prediction", "Failed to report prediction to kafka  (Value: " + str(metric["metric_value"]) + ", Prediction: " + str(prediction) + ")", metric=str(metric["metric_name"]), exception_type=str(type(ex).__name__), exception_message=str(ex.message))

        else:
            if models_number_below_configured_limit:
                self._logger.error("_get_prediction", "Could not load/create a prediction model for this metric", metric=str(metric))
        return prediction, prediction_made
