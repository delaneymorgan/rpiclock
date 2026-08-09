import threading
import time

import state
from utils import log


class WeatherMonitor(threading.Thread):
    def __init__(self, args, my_config):
        super(WeatherMonitor, self).__init__()
        self.args = args
        self.my_config = my_config
        self.service = None
        self.last_check = 0
        self._weather_lock = threading.Lock()
        self._weather = dict(
            tempNow=None,
            tempMin=None,
            tempMax=None,
            iconName=None,
            forecast=[]
        )

    def weather(self):
        with self._weather_lock:
            return dict(self._weather)

    def icon_path(self):
        raise NotImplementedError()

    def do_observation(self):
        raise NotImplementedError()

    def do_forecast(self):
        raise NotImplementedError()

    def run(self):
        while state.running_flag:
            log(self.args, "%s running" % self.__class__.__name__)
            time_now = time.time()
            wait_remaining = self.my_config.get()["weather"]["check_interval"] - (time_now - self.last_check)
            if wait_remaining <= 0:
                log(self.args, "polling weather")
                self.last_check = time_now
                self.do_observation()
                self.do_forecast()
            else:
                if state.stop_event.wait(wait_remaining):
                    break
