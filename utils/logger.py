import syslog
from datetime import datetime


import config_mgr
import stats_mgr

NONE = 0
ERROR = 1
WARNING = 2
INFO = 3
DEBUG = 4

Severities = [
    "NONE",
    "ERROR",
    "WARNING",
    "INFO",
    "DEBUG"
]


class Logger:
    def __init__(self, reporting_file, reporting_module):
        self._reporting_file = reporting_file
        self._reporting_module = reporting_module
        self._config_mgr = config_mgr.ConfigMgr.get_instance()
        self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)

    def error(self, method, message, state=None, metric=None, exception_message=None, exception_type=None):
        self.log(ERROR, method, message, state, metric, exception_message, exception_type)

    def warn(self, method, message, state=None, metric=None, exception_message=None, exception_type=None):
        self.log(WARNING, method, message, state, metric, exception_message, exception_type)

    def info(self, method, message, state=None, metric=None, exception_message=None, exception_type=None):
        self.log(INFO, method, message, state, metric, exception_message, exception_type)

    def debug(self, method, message, state=None, metric=None, exception_message=None, exception_type=None):
        self.log(DEBUG, method, message, state, metric, exception_message, exception_type)

    def log(self, severity, method, message, state=None, metric=None, exception_message=None, exception_type=None):
        if severity >= self._config_mgr.get("log_minimum_severity"):
            log_line = self._config_mgr.get("logging_format") % (datetime.now().isoformat(), "pensu." + self._reporting_module + "." + self._reporting_file, method, Severities[severity], str(state), str(metric), str(exception_message), str(exception_type), message)

            if self._config_mgr.get("log_to_syslog") == 1:
                syslog.syslog(log_line)
            if self._config_mgr.get("log_to_console") == 1:
                print(log_line)