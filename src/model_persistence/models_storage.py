import os
import time
from threading import Lock

from src import stats_mgr, models_library, config_mgr
import src.utils.global_state
import src.utils.logger

autosave_thread_lock = Lock()
create_model_thread_lock = Lock()
create_anomaly_likelihood_calc_thread_lock = Lock()


class ModelsStorage:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance():
        if ModelsStorage.__instance is None:
            ModelsStorage()
        return ModelsStorage.__instance

    def __init__(self):
        ModelsStorage.__threads_lock.acquire()
        try:
            if ModelsStorage.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                ModelsStorage.__instance = self
                self._config_mgr = config_mgr.ConfigMgr.get_instance()
                self._global_state = src.utils.global_state.GlobalState.get_instance()
                self.__models_library = models_library.ModelsLibrary.get_instance()
                self.EXIT_ALL_THREADS_FLAG = False
                self.models_save_base_path = self._config_mgr.get("models_save_base_path")
                self.anomaly_likelihood_calculator_filename = self._config_mgr.get("anomaly_likelihood_calculator_filename")
                self.anomaly_likelihood_detectors_save_base_path = self._config_mgr.get("anomaly_likelihood_detectors_save_base_path")
                self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
                self._logger = src.utils.logger.Logger(__file__, "ModelsStorage")
        finally:
            ModelsStorage.__threads_lock.release()

    def get_save_path(self, metric, path_element="model"):
        """
        This method returns the save path of the module or anomaly likelihood detector. (based on the current
        configuration and the metric in question)
        :param metric: The metric name (metric.entire.hierarchy) of the metric to return the save path for.
        :param path_element: Whether to return the model save path or the anomaly likelihood detector's path
        :return: String with the save path of the requested metric model/anomaly detector
        """

        if path_element == "model":
            save_path = self.models_save_base_path
            save_path = os.path.join(save_path, metric.replace(".", "/"))

            # If the path exists and contains files or folders but not model.pkl add to the save path a folder named .root
            if os.path.isdir(save_path):
                dir_contents = os.listdir(save_path)
                if len(dir_contents) > 0 and "model.pkl" not in dir_contents:
                    save_path = os.path.join(save_path, ".root")
            return save_path
        elif path_element == "anomaly_likelihood_calculator":
            save_path = self.anomaly_likelihood_detectors_save_base_path
            save_path = os.path.join(save_path, metric.replace(".", "/"))

            # If the path exists and contains files or folders but not model.pkl add to the save path a folder named .root
            if os.path.isdir(save_path):
                dir_contents = os.listdir(save_path)
                if len(dir_contents) > 0 and "model.pkl" not in dir_contents:
                    save_path = os.path.join(save_path, ".root")
            return save_path
        else:
            raise Exception("Unrecognized path element code")

    def auto_save_models(self, interval):
        """
        This method runs on a dedicated thread for automatically saving the currently used loaded_models and anomaly likelihood
        detectors to files.
        :param interval: The number of seconds between each save attempt.
        :return: None
        """

        for i in range(0, interval):
            if self._global_state.get_global_status("sigint_received"):
                return

            time.sleep(1)

        while True:
            if self._global_state.get_global_status("sigint_received"):
                return

            autosave_thread_lock.acquire()
            create_model_thread_lock.acquire()
            models_count = self.__models_library.get_models_count()
            for model_idx in range(0, models_count):
                model_obj = self.__models_library.get_model_by_idx(model_idx)
                metric = model_obj[0]
                model = model_obj[1]
                model_save_path = self.get_save_path(metric=metric, path_element="model")
                try:
                    model.save(model_save_path)
                except Exception as ex:
                    self._logger.warn("auto_save_models", "Could NOT auto save module no." + str(model_idx) + " at " + model_save_path + " due to an exception", metric=str(metric), exception_message=str(ex.message), exception_type=type(ex).__name__)

                if self.EXIT_ALL_THREADS_FLAG:
                    create_model_thread_lock.release()
                    return
            create_model_thread_lock.release()

            create_anomaly_likelihood_calc_thread_lock.acquire()
            anomaly_detectors_count = self.__models_library.get_anomaly_calc_count()
            for anomaly_likelihood_calculator_idx in range(0, anomaly_detectors_count):
                metric, anomaly_likelihood_calculator = self.__models_library.get_anomaly_calc_by_idx(anomaly_likelihood_calculator_idx)
                anomaly_likelihood_calculators_path = self.get_save_path(metric=metric, path_element="anomaly_likelihood_calculator")

                try:
                    if not os.path.exists(anomaly_likelihood_calculators_path):
                        os.makedirs(anomaly_likelihood_calculators_path)
                    with open(os.path.join(anomaly_likelihood_calculators_path, self.anomaly_likelihood_calculator_filename), "w") as anomaly_likelihood_calc_file:
                        anomaly_likelihood_calculator.writeToFile(anomaly_likelihood_calc_file)
                except OSError as ex:
                    self._logger.warn("auto_save_models", "Could NOT auto save anomaly likelihood calc for that metric at " + anomaly_likelihood_calculators_path + " due to an exception", metric=str(metric), exception_message=str(ex.message), exception_type=type(ex).__name__)

                if self.EXIT_ALL_THREADS_FLAG:
                    create_anomaly_likelihood_calc_thread_lock.release()
                    return
            create_anomaly_likelihood_calc_thread_lock.release()
            autosave_thread_lock.release()

            for i in range(0, interval):
                if self.EXIT_ALL_THREADS_FLAG:
                    return

                time.sleep(1)
