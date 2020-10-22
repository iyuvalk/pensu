from threading import Lock

import config_mgr
import stats_mgr
import utils.logger


class GlobalState:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance():
        if GlobalState.__instance is None:
            GlobalState()
        return GlobalState.__instance

    def __init__(self):
        GlobalState.__threads_lock.acquire()
        try:
            if GlobalState.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                GlobalState.__instance = self
                self._config_mgr = config_mgr.ConfigMgr.get_instance()
                self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
                self._logger = utils.logger.Logger(__file__, "GlobalState")
                self._registered_events = {
                    "sigint_received": []
                }
                self._global_statuses = {
                    "sigint_received": False
                }
        finally:
            GlobalState.__threads_lock.release()

    def fire_event(self, event_name, arg=None, set_global_status=False):
        self._logger.debug("fire_event", "Event " + event_name + " with arg=" + str(arg) + " was fired.")
        GlobalState.__threads_lock.acquire()
        try:
            if event_name in self._registered_events:
                for func in self._registered_events[event_name]:
                    try:
                        if arg is not None:
                            func(arg)
                        else:
                            func()
                    except Exception as ex:
                        self._logger.error("fire_event", "Failed to launch function for event " + event_name + ", arg=" + str(arg), exception_type=str(type(ex).__name__), exception_message=str(ex.message))
            if set_global_status:
                if event_name in self._global_statuses:
                    self._global_statuses[event_name] = True
                else:
                    self._logger.error("fire_event", "Failed to set the global status for event " + event_name + " as requested. The event does not exist as a global status.")
        finally:
            GlobalState.__threads_lock.release()

    def register_for_event(self, event_name, func):
        GlobalState.__threads_lock.acquire()
        try:
            if event_name in self._registered_events:
                self._registered_events[event_name].append(func)
                return True
            else:
                return False
        finally:
            GlobalState.__threads_lock.release()

    def get_global_status(self, event_name):
        if event_name in self._global_statuses:
            return self._global_statuses[event_name]
        else:
            self._logger.error("get_global_status", "Failed to return the global status for event " + event_name + " as requested. The event does not exist as a global status.")
