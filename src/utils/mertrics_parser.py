import base64

from src import stats_mgr, config_mgr
import src.utils.logger


class MetricsParser:
    def __init__(self):
        self._config_mgr = config_mgr.ConfigMgr.get_instance()
        self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
        self._logger = src.utils.logger.Logger(__file__, "MetricsParser")

    def parse_metric_message(self, metric_raw_info):
        try:
            self._stats_mgr.up("metrics_received")

            if len(metric_raw_info.split(" ")) == 3:
                metric_name = metric_raw_info.split(" ")[0]
                metric_family_raw = metric_name.split(".")
                if len(metric_family_raw) > 1:
                    metric_family_hierarchy = metric_family_raw[:(len(metric_family_raw) - 1)]
                    metric_family = ".".join(metric_family_hierarchy)
                    metric_item = metric_family_raw[(len(metric_family_raw) - 1)]
                else:
                    self._logger.warn("parse_metric_message", "Failed to parse metric (failed to parse metric family. Less than one dot in the family name)", metric=str(base64.b64encode(str(metric_raw_info))))
                    return
                try:
                    metric_value = float(metric_raw_info.split(" ")[1])
                except:
                    self._logger.warn("parse_metric_message", "Failed to parse metric info (failed to convert metric value to float)", metric=str(base64.b64encode(str(metric_raw_info))))
                    return
                try:
                    metric_timestamp = int(metric_raw_info.split(" ")[2])
                except:
                    self._logger.warn("parse_metric_message", "Failed to parse metric info(b64) (failed to convert timestamp value to int)", metric=str(base64.b64encode(str(metric_raw_info))))
                    return

            else:
                self._logger.warn("parse_metric_message", "Failed to parse metric info(b64) (raw message contains more or less than two spaces)", metric=str(base64.b64encode(str(metric_raw_info))))
                return

            return {"metric_family_hierarchy": metric_family_hierarchy, "metric_family": metric_family, "metric_item": metric_item, "metric_name": metric_name, "metric_value": metric_value, "metric_timestamp": metric_timestamp}

        except Exception as ex:
            self._logger.warn("parse_metric_message", "An unexpected exception has been thrown while parsing the metric message", exception_type=str(type(ex).__name__), exception_message=str(ex.message))
