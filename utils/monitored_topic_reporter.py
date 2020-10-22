from threading import Lock
import time
import config_mgr
import stats_mgr
import utils.global_state


class MonitoredTopicReporter:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance(kafka_producer):
        if MonitoredTopicReporter.__instance is None:
            MonitoredTopicReporter(kafka_producer)
        return MonitoredTopicReporter.__instance

    def __init__(self, kafka_producer):
        MonitoredTopicReporter.__threads_lock.acquire()
        try:
            if MonitoredTopicReporter.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                MonitoredTopicReporter.__instance = self
                self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
                self._config_mgr = config_mgr.ConfigMgr.get_instance()
                self._global_state = utils.global_state.GlobalState.get_instance()
                self._kafka_producer = kafka_producer
                self._topics_list_topic = self._config_mgr.get("topics_list_topic")
                self._raw_metrics_kafka_topic = self._config_mgr.get("raw_metrics_kafka_topic")
        finally:
            MonitoredTopicReporter.__threads_lock.release()

    def auto_report_monitored_topic(self):
        interval = self._config_mgr.get("topics_list_report_interval")
        if len((str(self._topics_list_topic)).strip()) == 0:
            return

        for i in range(0, interval):
            if self._global_state.get_global_status("sigint_received"):
                return

            time.sleep(1)

        while True:
            if self._global_state.get_global_status("sigint_received"):
                return

            self._kafka_producer.send(topic=self._topics_list_topic, value=self._raw_metrics_kafka_topic)

            for i in range(0, interval):
                if self._global_state.get_global_status("sigint_received"):
                    return

                time.sleep(1)
