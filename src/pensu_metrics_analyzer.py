#!/usr/bin/python2.7
##########################################################################
# Pensu Metrics Analyzer                                                 #
# ----------------------                                                 #
#                                                                        #
# This service is part of the Pensu package. This micro-service is       #
# responsible for creating models and predictions and detecting          #
# anomalies for metrics pulled from a Kafka topic (it uses the graphite  #
# line format for sending in metrics:                                    #
# (e.g. metric.name.hierarchy value timestamp_in_unix_ms)                #
#                                                                        #
# it uses Numenta's HTM algorithm to detect temporal anomalies in the    #
# metric values and make predictions.                                    #
#                                                                        #
##########################################################################


import sys
import signal
import os
import time
import threading
from threading import Lock
from bottle import Bottle
import kafka
import re
from src import model_persistence, stats_mgr, models_library, config_mgr
import src.model_persistence.models_factory
import src.model_persistence.anomaly_calc_factory
import src.ai_handlers.anomaly_detector
import src.utils.global_state
import src.utils.mertrics_parser
import src.utils.anomalies_handler
import src.utils.requested_service_status
import src.utils.monitored_topic_reporter
import src.utils.logger

# Create a separate class as a logger that all classes will use (singleton) that will log to the screen using print

DEBUG = False
create_model_thread_lock = Lock()
create_anomaly_likelihood_calc_thread_lock = Lock()
autosave_thread_lock = Lock()


class MetricsRealtimeAnalyzer:

    def __init__(self):
        self._ping_listening_host = None
        self._ping_listening_port = None
        self._analyzer_thread = None
        self._http_server_thread = None
        self._monitored_topic_reporting_thread = None

        self._config_mgr = config_mgr.ConfigMgr.get_instance()
        self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
        self._global_state = src.utils.global_state.GlobalState.get_instance()
        self._logger = src.utils.logger.Logger(__file__, "MetricsRealtimeAnalyzer")
        self._model_storage = src.model_persistence.models_storage.ModelsStorage.get_instance()
        self._metrics_parser = src.utils.mertrics_parser.MetricsParser()
        self._models_library = models_library.ModelsLibrary.get_instance()
        self._models_factory = src.model_persistence.models_factory.ModelFactory()
        self._anomaly_calc_factory = src.model_persistence.anomaly_calc_factory.AnomalyCalcFactory()

        self._requested_service_status_handler = src.utils.requested_service_status.RequestedStatus.get_instance()
        self._last_logged_message_about_too_many_models = 0

        self._logger.info("__init__", "Launching Pensu - Starting the bottle server...")
        self._app = Bottle()
        self._route()
        self._kafka_producer = None
        self._kafka_consumer = None
        self._logger.info("__init__", "Launching Pensu - Generating the kafka producer...")
        self.generate_kafka_producer()
        self._logger.info("__init__", "Launching Pensu - Building the anomalies handler...")
        self._anomalies_handler = src.utils.anomalies_handler.AnomaliesHandler.get_instance(self._kafka_producer)
        self._logger.info("__init__", "Launching Pensu - Building the anomaly detector...")
        self._anomaly_detector = src.ai_handlers.anomaly_detector.AnomalyDetector.get_instance(self._kafka_producer)
        self._logger.info("__init__", "Launching Pensu - Building the heartbeats sender...")
        self._monitored_topic_reporter = src.utils.monitored_topic_reporter.MonitoredTopicReporter.get_instance(self._kafka_producer)
        self._logger.info("__init__", "Launching Pensu - Done.")

    def generate_kafka_producer(self):
        while self._kafka_producer is None:
            if self._global_state.get_global_status("sigint_received"):
                return

            try:
                self._kafka_producer = kafka.producer.KafkaProducer(
                    bootstrap_servers=self._config_mgr.get("kafka_producer_server"),
                    client_id=self._config_mgr.get("kafka_producer_client_id")
                )
            except Exception as ex:
                self._logger.warn("generate_kafka_producer", "Waiting (indefinitely in 10 sec intervals) for the Producer Kafka service to become available... (kafka_producer_server=" + self._config_mgr.get("kafka_producer_server") + ", kafka_producer_client_id=" + self._config_mgr.get("kafka_producer_client_id") + ")", exception_type=type(ex).__name__, exception_message=str(ex.message))
                time.sleep(10)

    def _route(self):
        self._app.route('/ping', method="GET", callback=self._ping)

    def _ping(self):
        return {
            "response": "PONG",
            "instance_id": str(self._config_mgr.get("instance_id")),
            "service_specific_info": self._stats_mgr.get_stats(),
            "config": self._config_mgr.get_gist()
        }

    def _run_http_server(self):
        self._app.run(host=self._ping_listening_host, port=self._ping_listening_port)

    def run(self, models_save_base_path=None, models_params_base_path=None, anomaly_likelihood_detectors_save_base_path=None):
        try:
            self._ping_listening_host = self._config_mgr.get("ping_listen_host")
            self._ping_listening_port = self._config_mgr.get("ping_listen_port")
            self._analyzer_thread = threading.Thread(target=self.run_analyzer)
            self._logger.info("run", "Launching the analyzer thread (save_interval=" + str(self._config_mgr.get("autosave_models_interval")) + ";models_save_base_path=" + str(models_save_base_path) + ";models_params_base_path=" + str(models_params_base_path) + ";anomaly_likelihood_detectors_save_base_path=" + str(anomaly_likelihood_detectors_save_base_path) + ")")
            self._analyzer_thread.start()
            self._http_server_thread = threading.Thread(target=self._run_http_server)
            self._http_server_thread.daemon = True
            self._http_server_thread.start()
            while True:
                if self._global_state.get_global_status("sigint_received"):
                    return
                time.sleep(5)
        except Exception as ex:
            self._logger.error("run", "Failed to launch the analyzer thread.", exception_type=type(ex).__name__, exception_message=str(ex.message))
            raise ex

    def run_analyzer(self):
        save_interval = self._config_mgr.get("autosave_models_interval")
        while self._kafka_consumer is None:
            if self._global_state.get_global_status("sigint_received"):
                return
            try:
                self._kafka_consumer = kafka.KafkaConsumer(self._config_mgr.get("raw_metrics_kafka_topic"),
                                                           bootstrap_servers=self._config_mgr.get("kafka_consumer_server"),
                                                           client_id=self._config_mgr.get("kafka_consumer_client_id"),
                                                           consumer_timeout_ms=self._config_mgr.get("kafka_consumer_session_timeout"))
                self._logger.info("run_analyzer", "Loaded a Kafka consumer successfully. (self._metrics_kafka_topic=" + str(self._config_mgr.get("raw_metrics_kafka_topic")) + ";bootstrap_servers=" + str(self._config_mgr.get("kafka_consumer_server")) + ";client_id=" + str(self._config_mgr.get("kafka_consumer_client_id")) + ")")
            except Exception as ex:
                self._logger.warn("run_analyzer", "Waiting on a dedicated thread for the Kafka server to be available  (kafka_consumer_server=" + self._config_mgr.get("kafka_consumer_server") + ", kafka_consumer_client_id=" + self._config_mgr.get("kafka_consumer_client_id") + ")... Going to sleep for 10 seconds", exception_message=str(ex.message), exception_type=str(type(ex).__name__))
                time.sleep(10)

        if save_interval > 0:
            # launch the auto-save thread
            autosave_thread = threading.Thread(target=self._model_storage.auto_save_models, args=[save_interval])
            autosave_thread.daemon = True
            self._logger.info("run_analyzer", "Launching auto-save thread (save_interval=" + str(save_interval) + ")")
            autosave_thread.start()
        else:
            self._logger.info("run_analyzer", "Models auto-save is disabled.")

        # launch the thread that will inform the sender on which topic we're listening on
        self._monitored_topic_reporting_thread = threading.Thread(target=self._monitored_topic_reporter.auto_report_monitored_topic)
        self._monitored_topic_reporting_thread.daemon = True
        self._logger.info("run_analyzer", "Launching listened topic reporter thread")
        self._monitored_topic_reporting_thread.start()

        # handle received metrics
        self._logger.info("run_analyzer", "Starting the metrics handling loop")
        self.metrics_handling_loop(self._kafka_consumer)

    def metrics_handling_loop(self, kafka_consumer):
        while not self._global_state.get_global_status("sigint_received"):
            for metric in kafka_consumer:
                if self._global_state.get_global_status("sigint_received"):
                    return
                autosave_thread_lock.acquire()
                # noinspection PyBroadException
                try:
                    self._stats_mgr.up("raw_metrics_downloaded_from_kafka")
                    self._logger.debug("run_analyzer", "Received the following metric from Kafka: " + str(metric))

                    # If this is an anomaly metric created by this service then there's no need to process it again...
                    if metric.value is None or metric.value.strip() == "" or len(metric.value.split(" ")) != 3:
                        self._logger.debug("run_analyzer", "Received this malformed metric. Ignoring")
                        continue

                    metric_name = metric.value.split(" ")[0]
                    if re.match(self._config_mgr.get("allowed_to_work_on_metrics_pattern"), str(metric_name)):
                        self._logger.debug("run_analyzer", "Handling this metric since it matches the regex " + self._config_mgr.get("allowed_to_work_on_metrics_pattern").pattern)
                        parsed_metric = self._metrics_parser.parse_metric_message(metric_raw_info=metric.value)
                        self._anomaly_detector.detect_anomaly(parsed_metric)
                    else:
                        self._logger.debug("run_analyzer", "Ignoring this metric since it DOES NOT match the regex " + self._config_mgr.get("allowed_to_work_on_metrics_pattern").pattern)
                except Exception as ex:
                    self._logger.warn("run_analyzer", "The following error occurred while parsing the following metric that was pulled from Kafka: " + str(metric), exception_type=str(type(ex).__name__), exception_message=str(ex.message))
                finally:
                    autosave_thread_lock.release()

    def signal_handler(self, signal_caught, frame):
        self._logger.info("run_analyzer", "The signal " + str(signal_caught) + " was caught from frame " + str(frame))
        self._global_state.fire_event(event_name="sigint_received", set_global_status=True)


analyzer_object = MetricsRealtimeAnalyzer()
signal.signal(signal.SIGINT, analyzer_object.signal_handler)
env_models_save_base_path = None
env_models_params_base_path = None
env_anomaly_likelihood_detectors_save_base_path = None

script_path = os.path.dirname(os.path.realpath(__file__))

sys.argv = [sys.argv[0]]
analyzer_object.run(
    models_save_base_path=env_models_save_base_path,
    models_params_base_path=env_models_params_base_path,
    anomaly_likelihood_detectors_save_base_path=env_anomaly_likelihood_detectors_save_base_path
)
