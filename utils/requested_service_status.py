from threading import Lock


class RequestedStatus:
    __instance = None
    __threads_lock = Lock()

    @staticmethod
    def get_instance():
        if RequestedStatus.__instance is None:
            RequestedStatus()
        return RequestedStatus.__instance

    def __init__(self):
        RequestedStatus.__threads_lock.acquire()
        try:
            if RequestedStatus.__instance is not None:
                raise Exception("This is a singleton class. Please use the get_instance() method.")
            else:
                RequestedStatus.__instance = self
                self._EXIT_ALL_THREADS = False
        finally:
            RequestedStatus.__threads_lock.release()

    def request_clean_shutdown(self):
        self._EXIT_ALL_THREADS = True

    def clean_shutdown_requested(self):
        return self._EXIT_ALL_THREADS