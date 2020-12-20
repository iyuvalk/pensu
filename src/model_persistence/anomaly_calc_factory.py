import os
from nupic.algorithms.anomaly_likelihood import AnomalyLikelihood
from src import model_persistence, stats_mgr, config_mgr
import src.model_persistence.models_storage


class AnomalyCalcFactory:
    def __init__(self):
        self._config_mgr = config_mgr.ConfigMgr.get_instance()
        self.__anomaly_likelihood_calculator_filename = self._config_mgr.get("anomaly_likelihood_calculator_filename")
        self.__model_storage_manager = model_persistence.models_storage.ModelsStorage.get_instance()
        self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)

    def create_anomaly_likelihood_calc_from_disk(self, metric):
        anomaly_likelihood_calculators_path = self.__model_storage_manager.get_save_path(metric["metric_name"], path_element="anomaly_likelihood_calculator")
        with open(os.path.join(anomaly_likelihood_calculators_path, self.__anomaly_likelihood_calculator_filename), "rb") as anomaly_likelihood_calc_file:
            return AnomalyLikelihood.readFromFile(anomaly_likelihood_calc_file)
