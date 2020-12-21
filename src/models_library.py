from threading import Lock
from src import stats_mgr


class ModelsLibrary:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance():
        if ModelsLibrary.__instance is None:
            ModelsLibrary()
        return ModelsLibrary.__instance

    def __init__(self):
        ModelsLibrary.__threads_lock.acquire()
        try:
            if ModelsLibrary.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                ModelsLibrary.__instance = self
                self._models = {}
                self._anomaly_likelihood_detectors = {}
                self._stats_mgr = stats_mgr.StatsMgr.get_instance(__file__)
        finally:
            ModelsLibrary.__threads_lock.release()

    def get_model(self, model_name):
        ModelsLibrary.__threads_lock.acquire()
        res = None
        try:
            if model_name in self._models:
                res = self._models[model_name]
        finally:
            ModelsLibrary.__threads_lock.release()
        return res

    def get_model_by_idx(self, model_idx):
        ModelsLibrary.__threads_lock.acquire()
        res = None
        try:
            if model_idx < len(self._models):
                res = self._models.items()[model_idx]
        finally:
            ModelsLibrary.__threads_lock.release()
        return res

    def model_exists(self, model_name):
        ModelsLibrary.__threads_lock.acquire()
        try:
            res = model_name in self._models
        finally:
            ModelsLibrary.__threads_lock.release()
        return res

    def get_models_count(self):
        ModelsLibrary.__threads_lock.acquire()
        try:
            count = len(self._models)
        finally:
            ModelsLibrary.__threads_lock.release()
        return count

    def get_anomaly_calc(self, model_name):
        ModelsLibrary.__threads_lock.acquire()
        res = None
        try:
            if model_name in self._anomaly_likelihood_detectors:
                res = self._anomaly_likelihood_detectors[model_name]
        finally:
            ModelsLibrary.__threads_lock.release()
        return res

    def get_anomaly_calc_by_idx(self, idx):
        ModelsLibrary.__threads_lock.acquire()
        res = None
        try:
            if idx < len(self._anomaly_likelihood_detectors):
                res = self._anomaly_likelihood_detectors.items()[idx]
        finally:
            ModelsLibrary.__threads_lock.release()
        return res

    def anomaly_calc_exists(self, model_name):
        ModelsLibrary.__threads_lock.acquire()
        try:
            res = model_name in self._anomaly_likelihood_detectors
        finally:
            ModelsLibrary.__threads_lock.release()
        return res

    def get_anomaly_calc_count(self):
        ModelsLibrary.__threads_lock.acquire()
        try:
            count = len(self._anomaly_likelihood_detectors)
        finally:
            ModelsLibrary.__threads_lock.release()
        return count

    def add_anomaly_calc_for_metric(self, key, anomaly_calc):
        ModelsLibrary.__threads_lock.acquire()
        try:
            self._anomaly_likelihood_detectors[key] = anomaly_calc
            self._stats_mgr.set("anomaly_calculators_loaded", len(self._anomaly_likelihood_detectors))
        finally:
            ModelsLibrary.__threads_lock.release()

    def add_model_for_metric(self, key, model):
        ModelsLibrary.__threads_lock.acquire()
        try:
            self._models[key] = model
            self._stats_mgr.up("models_loaded")
            self._stats_mgr.set("models_list", self._models.keys())
        finally:
            ModelsLibrary.__threads_lock.release()

    def add_models_for_metric(self, key, model, anomaly_calc):
        ModelsLibrary.__threads_lock.acquire()
        try:
            self._anomaly_likelihood_detectors[key] = anomaly_calc
            self._models[key] = model
            self._stats_mgr.set("anomaly_calculators_loaded", len(self._anomaly_likelihood_detectors))
            self._stats_mgr.set("models_loaded", len(self._models))
            self._stats_mgr.append_to_list("models_list", key)
        finally:
            ModelsLibrary.__threads_lock.release()

    def get_metrics_loaded(self):
        ModelsLibrary.__threads_lock.acquire()
        try:
            metrics_loaded = self._models.keys()
        finally:
            ModelsLibrary.__threads_lock.release()
        return metrics_loaded
