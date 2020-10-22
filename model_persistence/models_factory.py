from nupic.frameworks.opf.model_factory import ModelFactory as NupicModelFactory
from nupic.algorithms.anomaly_likelihood import AnomalyLikelihood
from threading import Lock
import importlib
import os

import model_persistence.models_storage
import model_persistence.anomaly_calc_factory
import models_library
import config_mgr
import stats_mgr
import utils.logger

DEBUG = False


class ModelFactory:
    def __init__(self):
        self._config_mgr = config_mgr.ConfigMgr.get_instance()
        self.__loaded_models = models_library.ModelsLibrary.get_instance()
        self.__create_model_thread_lock = Lock()
        self.__model_storage_manager = model_persistence.models_storage.ModelsStorage.get_instance()
        self.__anomaly_likelihood_calculator_factory = model_persistence.anomaly_calc_factory.AnomalyCalcFactory()
        self._anomaly_likelihood_calculator_filename = self._config_mgr.get("anomaly_likelihood_calculator_filename")
        self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
        self._logger = utils.logger.Logger(__file__, "ModelFactory")

    @staticmethod
    def __create_model(model_params, prediction_steps):
        """
        Given a model params dictionary, create a CLA Model. Automatically enables
        inference for value.
        :param model_params: Model params dict
        :param prediction_steps: The steps ahead to configure this model to predict
        :return: OPF Model object
        """
        if model_params:
            model_params["modelParams"]["clParams"]["steps"] = "1," + str(prediction_steps)
            model = NupicModelFactory.create(model_params)
            model.enableInference({"predictedField": "value"})
            return model
        return None

    def __get_model(self, metric, model_type, models_number_below_configured_limit):
        model_prefix = "_" + model_type
        result_model = None
        model_fqdn = model_prefix + "." + metric["metric_name"]
        if not self.__loaded_models.model_exists(model_fqdn):
            self.__create_model_thread_lock.acquire()
            try:
                if not self.__loaded_models.model_exists(model_fqdn) and os.path.isdir(self.__model_storage_manager.get_save_path(model_fqdn)):
                    if models_number_below_configured_limit:
                        try:
                            self.__loaded_models.add_model_for_metric(model_fqdn, NupicModelFactory.loadFromCheckpoint(self.__model_storage_manager.get_save_path(model_fqdn)))
                            self._logger.debug("__get_model", "LOADED " + model_type.upper() + " MODEL FROM DISK")
                        except Exception as ex:
                            self.__loaded_models.add_model_for_metric(model_fqdn, self.__create_model(self.get_model_params_from_metric_name(metric["metric_family"], model_type), self._config_mgr.get("prediction_steps")))
                            self._logger.warn("__get_model", "Failed to create a " + model_type + " model from disk", exception_message=str(ex.message), exception_type=str(type(ex).__name__))

                if not self.__loaded_models.model_exists(model_fqdn) and not os.path.isdir(self.__model_storage_manager.get_save_path(model_fqdn)):
                    if models_number_below_configured_limit:
                        model_params = self.get_model_params_from_metric_name(metric["metric_family"], model_type)
                        prediction_steps = self._config_mgr.get("prediction_steps")
                        model_to_add = self.__create_model(model_params, prediction_steps)
                        self.__loaded_models.add_model_for_metric(model_fqdn, model_to_add)
                        self._logger.debug("__get_model", model_type.capitalize() + " model created from params", metric=str(metric["metric_name"]))
            finally:
                self.__create_model_thread_lock.release()
        if self.__loaded_models.model_exists(model_fqdn):
            result_model = self.__loaded_models.get_model(model_fqdn)
            self._logger.debug("__get_model", model_type.capitalize() + " model loaded from cache", metric=str(metric["metric_name"]))
        return result_model

    def get_model_params_from_metric_name(self, metric_family, model_type):
        """
        Given a gym name, assumes a matching model params python module exists within
        the model_params directory and attempts to import it.
        :param metric_family: Gym name, used to guess the model params module name.
        :param model_type: A prefix to the actual model name. Can be used to indicate whether it's a prediction model or one for anomaly detection
        :return: OPF Model params dictionary
        """

        import_name = model_type + "_model_params.%s" % (
            metric_family.replace(" ", "_").replace("-", "_")
        )
        self._logger.debug("get_model_params_from_metric_name", "Importing model params from " + str(import_name), metric=str(metric_family))
        try:
            imported_model_params = importlib.import_module(import_name).MODEL_PARAMS
        except ImportError:
            # Using default model params
            import_name = "model_params." + model_type + "_model_params.default"
            imported_model_params = importlib.import_module(import_name).MODEL_PARAMS
            self._logger.debug("get_model_params_from_metric_name", "No model params exist for that metric family. Using default module params.", metric=str(metric_family))

        return imported_model_params

    def get_anomaly_likelihood_calc(self, metric, models_number_below_configured_limit):
        anomaly_likelihood_calc = None
        if not self.__loaded_models.anomaly_calc_exists(metric["metric_name"]):
            anomaly_likelihood_calculators_path = self.__model_storage_manager.get_save_path(metric["metric_name"], path_element="anomaly_likelihood_calculator")

            if os.path.isfile(os.path.join(anomaly_likelihood_calculators_path, self._anomaly_likelihood_calculator_filename)):
                if models_number_below_configured_limit:
                    try:
                        if models_number_below_configured_limit:
                            self.__loaded_models.add_anomaly_calc_for_metric(metric["metric_name"], self.__anomaly_likelihood_calculator_factory.create_anomaly_likelihood_calc_from_disk(metric))
                            self._logger.debug("get_anomaly_likelihood_calc", "LOADED ANOMALY_LIKELIHOOD_CALC FROM FILE", metric=str(metric["metric_name"]))

                    except Exception as ex:
                        if models_number_below_configured_limit:
                            self.__loaded_models.add_anomaly_calc_for_metric(metric["metric_name"], AnomalyLikelihood())
                            self._logger.warn("get_anomaly_likelihood_calc", "Failed to create an anomaly likelihood calc from disk", metric=str(metric["metric_name"]), exception_type=str(type(ex).__name__), exception_message=str(ex.message))

            else:
                if models_number_below_configured_limit:
                    self.__loaded_models.add_anomaly_calc_for_metric(metric["metric_name"], AnomalyLikelihood())
        if self.__loaded_models.anomaly_calc_exists(metric["metric_name"]):
            anomaly_likelihood_calc = self.__loaded_models.get_anomaly_calc(metric["metric_name"])
        return anomaly_likelihood_calc

    def get_anomaly_model(self, metric, models_number_below_configured_limit):
        model_type = "anomaly"
        return self.__get_model(metric, model_type, models_number_below_configured_limit)

    def get_prediction_model(self, metric, models_number_below_configured_limit):
        model_type = "prediction"
        return self.__get_model(metric, model_type, models_number_below_configured_limit)
