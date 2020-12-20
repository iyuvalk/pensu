import json
import uuid
from threading import Lock

from src import stats_mgr, config_mgr
import src.utils.logger


class AnomaliesHandler:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance(kafka_producer):
        if AnomaliesHandler.__instance is None:
            AnomaliesHandler(kafka_producer)
        return AnomaliesHandler.__instance

    @staticmethod
    def get_current_instance():
        return AnomaliesHandler.__instance

    def __init__(self, kafka_producer):
        AnomaliesHandler.__threads_lock.acquire()
        try:
            if AnomaliesHandler.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                AnomaliesHandler.__instance = self
                self._config_mgr = config_mgr.ConfigMgr.get_instance()
                self._kafka_producer = kafka_producer
                self._anomaly_reports_kafka_topic = self._config_mgr.get("anomaly_reports_kafka_topic")
                self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
                self._logger = src.utils.logger.Logger(__file__, "AnomaliesHandler")
        finally:
            AnomaliesHandler.__threads_lock.release()

    def report_anomaly(self, metric, anomaly_info):
        self._stats_mgr.up("anomalies_reports_attempted")
        anomaly_report = {
            "report_id": str(uuid.uuid4()),
            "metric": metric,
            "reporter": "pensu",
            "meta_data": anomaly_info
        }
        try:
            self._kafka_producer.send(topic=self._anomaly_reports_kafka_topic, value=json.dumps(anomaly_report).encode('utf-8'))
            self._logger.info("report_anomaly", "Reported the following anomaly to kafka: " + json.dumps(anomaly_report), metric=str(metric))
            self._stats_mgr.up("anomalies_reported")

        except Exception as ex:
            self._logger.warn("report_anomaly", "Failed to report the following anomaly to Kafka due to an exception. These are the anomaly details: " + json.dumps(anomaly_report), metric=str(metric), exception_type=type(ex).__name__, exception_message=str(ex.message))
