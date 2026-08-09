import platform
import time
import threading

import state
from utils import log


class BrightnessMonitor(threading.Thread):
    """Controls display brightness depending on time of day."""

    kMaxBrightness = 255
    kMinBrightness = 0

    def __init__(self, args, my_config):
        super(BrightnessMonitor, self).__init__()
        self.args = args
        self.my_config = my_config
        self.high_mod_start = self.tod_to_mod(self.my_config.get()["brightness"]["high_tom_start"])
        self.low_mod_start = self.tod_to_mod(self.my_config.get()["brightness"]["low_tom_start"])
        self.backlight = None
        if platform.machine() in ["armv7l", "aarch64"]:
            try:
                from rpi_backlight import Backlight
                self.backlight = Backlight()
            except Exception:
                log(self.args, "backlight control not supported")

    @staticmethod
    def tod_to_mod(tod):
        tod = tod.split(":")
        return (int(tod[0]) * 60) + int(tod[1])

    def set_backlight(self, raw_value):
        if self.backlight is None:
            return
        self.backlight.brightness = raw_value

    def run(self):
        while state.running_flag:
            time_now = time.time()
            local_time = time.localtime(time_now)
            current_mod = (local_time.tm_hour * 60) + local_time.tm_min
            if self.low_mod_start <= current_mod < self.high_mod_start:
                power = self.my_config.get()["brightness"]["low"]
            else:
                power = self.my_config.get()["brightness"]["high"]
            raw_value = int(power * self.kMaxBrightness)
            if self.backlight is not None:
                self.set_backlight(raw_value)
            if state.stop_event.wait(60):
                break
