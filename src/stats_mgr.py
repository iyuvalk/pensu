import ctypes
import hashlib
import time
from threading import Lock
from multiprocessing import Value


class StatsMetricNotFoundException(Exception):
    pass

class StatsMetricIsNotListException(Exception):
    pass


class StatsMgr:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance(requesting_module_file):
        if StatsMgr.__instance is None:
            StatsMgr()

        if requesting_module_file not in StatsMgr.__instance._stats["files"]:
            StatsMgr.__instance._stats["files"][requesting_module_file] = hashlib.md5(StatsMgr._file_as_bytes(requesting_module_file)).hexdigest()

        return StatsMgr.__instance

    def __init__(self):
        StatsMgr.__threads_lock.acquire()
        try:
            if StatsMgr.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                StatsMgr.__instance = self
                self._stats = {
                    "time_loaded": time.time(),
                    "anomalies_reported": Value('i', 0),
                    "metrics_received": Value('i', 0),
                    "metrics_successfully_processed": Value('i', 0),
                    "raw_metrics_downloaded_from_kafka": Value('i', 0),
                    "anomalies_reports_attempted": Value('i', 0),
                    "last_metric_timestamp": Value('i', -1),
                    "models_loaded": Value('i', 0),
                    "models_list": [],
                    "anomaly_calculators_loaded": Value('i', 0),
                    "files": {}
                }
        finally:
            StatsMgr.__threads_lock.release()

    @staticmethod
    def _file_as_bytes(filename):
        with open(filename, 'rb') as file:
            return file.read()

    def up(self, stats_metric):
        StatsMgr.__threads_lock.acquire()
        try:
            if stats_metric in self._stats:
                self._stats[stats_metric].value += 1
            else:
                raise StatsMetricNotFoundException()
        finally:
            StatsMgr.__threads_lock.release()

    def set(self, stats_metric, value):
        StatsMgr.__threads_lock.acquire()
        try:
            if stats_metric in self._stats:
                if isinstance(value, list):
                    self._stats[stats_metric].value = value
            else:
                raise StatsMetricNotFoundException()
        finally:
            StatsMgr.__threads_lock.release()

    def append_to_list(self, stats_metric, value):
        StatsMgr.__threads_lock.acquire()
        try:
            if stats_metric in self._stats:
                if isinstance(self._stats[stats_metric], list):
                    self._stats[stats_metric].append(value)
                else:
                    raise StatsMetricIsNotListException()
            else:
                raise StatsMetricNotFoundException()

        finally:
            StatsMgr.__threads_lock.release()

    def get(self, stats_metric):
        StatsMgr.__threads_lock.acquire()
        try:
            if stats_metric in self._stats:
                return self._stats[stats_metric].value
            else:
                raise StatsMetricNotFoundException()
        finally:
            StatsMgr.__threads_lock.release()

    def get_stats(self):
        return {
            "time_loaded": self._stats["time_loaded"],
            "uptime": time.time() - self._stats["time_loaded"],
            "anomalies_reports_attempted": self._stats["anomalies_reports_attempted"].value,
            "anomalies_reported": self._stats["anomalies_reported"].value,
            "metrics_received": self._stats["metrics_received"].value,
            "metrics_successfully_processed": self._stats["metrics_successfully_processed"].value,
            "raw_metrics_downloaded_from_kafka": self._stats["raw_metrics_downloaded_from_kafka"].value,
            "models_loaded": self._stats["models_loaded"].value,
            "models_list": self._stats["models_list"],
            "anomaly_likelihood_calculators_loaded": self._stats["anomaly_calculators_loaded"].value,
            "files": self._stats["files"]
        }
