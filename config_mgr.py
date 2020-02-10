import base64
from threading import Lock
from os.path import dirname
import os
import uuid
import re
import time
import copy
import stats_mgr


class ConfigValueInvalidException(Exception):
    pass


class ConfigKeyNotFoundException(Exception):
    pass


class EnvironmentVariableMissingException(Exception):
    pass


class ConfigMgr:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance():
        if ConfigMgr.__instance is None:
            ConfigMgr()
        return ConfigMgr.__instance

    def __init__(self):
        ConfigMgr.__threads_lock.acquire()
        try:
            if ConfigMgr.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                ConfigMgr.__instance = self
                self._instance_id = uuid.uuid4()
                self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
                self._configs_keys = {
                    "autosave_models_interval":                              {"type": "int",    "resolve_placeholders": False, "default": 86400,                                               "environ_var": "PENSU_MODELS_AUTOSAVE_INTERVAL"},
                    "ping_listen_host":                                      {"type": "string", "resolve_placeholders": False, "default": "0.0.0.0",                                           "environ_var": "PENSU_PING_LISTEN_HOST"},
                    "ping_listen_port":                                      {"type": "int",    "resolve_placeholders": False, "default": 6666,                                                "environ_var": "PENSU_PING_LISTEN_PORT"},
                    "log_minimum_severity":                                  {"type": "int",    "resolve_placeholders": False, "default": 1,                                                   "environ_var": "PENSU_LOG_MINIMUM_SEVERITY"},
                    "log_to_console":                                        {"type": "int",    "resolve_placeholders": False, "default": 1,                                                   "environ_var": "PENSU_LOG_TO_CONSOLE"},
                    "log_to_syslog":                                         {"type": "int",    "resolve_placeholders": False, "default": 1,                                                   "environ_var": "PENSU_LOG_TO_SYSLOG"},
                    "prediction_steps":                                      {"type": "int",    "resolve_placeholders": False, "default": 5,                                                   "environ_var": "PENSU_PREDICTION_STEPS"},
                    "anomaly_likelihood_calculator_filename":                {"type": "string", "resolve_placeholders": False, "default": "pensu_anomaly_likelihood_calculator",               "environ_var": "PENSU_ANOMALYCALC_FILENAME"},
                    "metrics_prefix":                                        {"type": "string", "resolve_placeholders": False, "default": "pensu.{{#anomaly_metric}}.metrics_analyzer",        "environ_var": "PENSU_METRIC_NAMES_TEMPLATE"},
                    "kafka_consumer_client_id":                              {"type": "string", "resolve_placeholders": True,  "default": "pensu_consumer_{{#instance_id}}_{{#time_started}}", "environ_var": "PENSU_KAFKA_CONSUMER_CLIENT_ID"},
                    "kafka_consumer_session_timeout":                        {"type": "int",    "resolve_placeholders": False, "default": 5000,                                                "environ_var": "PENSU_KAFKA_CONSUMER_SESSION_TIMEOUT_MS"},
                    "kafka_consumer_server":                                 {"type": "string", "resolve_placeholders": False, "default": "kafka:9092",                                        "environ_var": "PENSU_KAFKA_CONSUMER_SERVER"},
                    "kafka_producer_client_id":                              {"type": "string", "resolve_placeholders": True,  "default": "pensu_producer_{{#instance_id}}_{{#time_started}}", "environ_var": "PENSU_KAFKA_PRODUCER_CLIENT_ID"},
                    "kafka_producer_server":                                 {"type": "string", "resolve_placeholders": False, "default": "kafka:9092",                                        "environ_var": "PENSU_KAFKA_PRODUCER_SERVER"},
                    "topics_list_topic":                                     {"type": "string", "resolve_placeholders": False, "default": "pensu_monitored_topics",                            "environ_var": "PENSU_TOPICS_KAFKA_TOPIC"},
                    "topics_list_report_interval":                           {"type": "int",    "resolve_placeholders": False, "default": 10,                                                  "environ_var": "PENSU_TOPICS_REPORT_INTERVAL"},
                    "raw_metrics_kafka_topic":                               {"type": "string", "resolve_placeholders": False, "default": "metrics",                                           "environ_var": "PENSU_METRICS_KAFKA_TOPIC"},
                    "anomaly_reports_kafka_topic":                           {"type": "string", "resolve_placeholders": False, "default": "pensu.htm.anomaly_metrics",                         "environ_var": "PENSU_REPORTED_ANOMALIES_KAFKA_TOPIC"},
                    "predictions_metrics_kafka_topic":                       {"type": "string", "resolve_placeholders": False, "default": "pensu.htm.predictions",                             "environ_var": "PENSU_PREDICTION_METRICS_KAFKA_TOPIC"},
                    "anomalies_metrics_kafka_topic":                         {"type": "string", "resolve_placeholders": False, "default": "pensu_anomalies",                                   "environ_var": "PENSU_ANOMALIES_METRICS_KAFKA_TOPIC"},
                    "allowed_to_work_on_metrics_pattern":                    {"type": "re",     "resolve_placeholders": False, "default": ".*",                                                "environ_var": "PENSU_ALLOWED_TO_WORK_ON_METRICS"},
                    "logging_format":                                        {"type": "string", "resolve_placeholders": True,  "default": "timestamp=%s;module=smart-onion_%s;method=%s;severity=%s;state=%s;metric/metric_family=%s;exception_msg=%s;exception_type=%s;message=%s", "environ_var": "PENSU_LOGGING_FORMAT"},
                    "anomaly_score_threshold_for_reporting":                 {"type": "float",  "resolve_placeholders": False, "default": 0.99,                                                "environ_var": "PENSU_ANOMALY_SCORE_THRESHOLD"},
                    "anomaly_likelihood_threshold_for_reporting":            {"type": "float",  "resolve_placeholders": False, "default": 0.99999,                                             "environ_var": "PENSU_ANOMALY_LIKELIHOOD_THRESHOLD"},
                    "minimum_confidence_for_reporting":                      {"type": "float",  "resolve_placeholders": False, "default": 0.9,                                                 "environ_var": "PENSU_MINIMUM_CONFIDENCE_FOR_REPORTING"},
                    "max_allowed_models":                                    {"type": "int",    "resolve_placeholders": False, "default": 10,                                                  "environ_var": "PENSU_MAX_ALLOWED_MODELS"},
                    "minimum_seconds_between_model_over_quota_log_messages": {"type": "int",    "resolve_placeholders": False, "default": 300,                                                 "environ_var": "PENSU_MIN_SECONDS_BETWEEN_OVER_QUOTA_LOG_MSG"},
                }

                self._config = {
                    "instance_id": self._instance_id,
                    "models_save_base_path": os.path.join(dirname(__file__), "data_models"),
                    "anomaly_likelihood_detectors_save_base_path": os.path.join(dirname(__file__), "anomaly_likelihood_calculators")
                }
                for config_key in self._configs_keys.keys():
                    if self._configs_keys[config_key]["environ_var"] in os.environ:
                        config_value = os.environ[self._configs_keys[config_key]["environ_var"]]
                    else:
                        if "default" in self._configs_keys[config_key] and self._configs_keys[config_key]["default"] is not None:
                            config_value = self._configs_keys[config_key]["default"]
                        else:
                            raise EnvironmentVariableMissingException("The required environment variable '" + self._configs_keys[config_key]["environ_var"] + "' in MISSING and no default exists for this key. CANNOT CONTINUE.")
                    if self._configs_keys[config_key]["resolve_placeholders"]:
                        config_value = config_value.replace("{{#instance_id}}", str(self._instance_id))
                        config_value = config_value.replace("{{#time_started}}", str(int(time.time())))

                    if self._configs_keys[config_key]["type"] == "string":
                        self._config[config_key] = config_value
                    if self._configs_keys[config_key]["type"] == "int":
                        try:
                            self._config[config_key] = int(config_value)
                        except ValueError:
                            raise ConfigValueInvalidException("The value (b64: " + base64.b64encode(config_value) + ") for " + config_key + " is invalid according to its type " + self._configs_keys[config_key]["type"])
                    if self._configs_keys[config_key]["type"] == "float":
                        try:
                            self._config[config_key] = float(config_value)
                        except ValueError:
                            raise ConfigValueInvalidException("The value (b64: " + base64.b64encode(config_value) + ") for " + config_key + " is invalid according to its type " + self._configs_keys[config_key]["type"])
                    if self._configs_keys[config_key]["type"] == "re":
                        try:
                            self._config[config_key] = re.compile(config_value)
                        except ValueError:
                            raise ConfigValueInvalidException("The value (b64: " + base64.b64encode(config_value) + ") for " + config_key + " is invalid according to its type " + self._configs_keys[config_key]["type"])
        finally:
            ConfigMgr.__threads_lock.release()

    def get(self, key):
        if key in self._config:
            return self._config[key]
        else:
            raise ConfigKeyNotFoundException("The config key (b64:" + base64.b64encode(str(key)) + ") could not be found in the configuration keys")

    def get_gist(self):
        res = {}
        for key in self._configs_keys.keys():
            if isinstance(self._config[key], type(re.compile(".*"))):
                res[key] = self._config[key].pattern
            else:
                res[key] = str(self._config[key])
        return res
