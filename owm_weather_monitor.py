import datetime
import os

try:
    import pyowm
except ImportError:  # pragma: no cover - optional dependency
    pyowm = None

from constants import OWM_ICONS_DIR
from utils import log
from weather_monitor import WeatherMonitor


class OWMWeatherMonitor(WeatherMonitor):
    def __init__(self, args, my_config):
        super(OWMWeatherMonitor, self).__init__(args, my_config)
        if pyowm is None:
            print("OWMWeatherMonitor unavailable: pyowm is not installed")
            return
        try:
            self.service = pyowm.OWM(my_config.get()["owm_weather"]["api_key"])
            self.do_observation()
        except Exception as e:
            print("OWMWeatherMonitor.__init__() Error: %s/%s" % (type(e), str(e)))

    def do_observation(self):
        log(self.args, "retrieving observation")
        if pyowm is None:
            return
        try:
            mgr = self.service.weather_manager()
            obs = mgr.weather_at_place(self.my_config.get()["owm_weather"]["place"])
            scale = self.my_config.get()["owm_weather"]["temperature_scale"]
            obs_weather = obs.get_weather()
            with self._weather_lock:
                self._weather["tempNow"] = obs_weather.get_temperature(scale)["temp"]
                self._weather["iconName"] = obs_weather.get_weather_icon_name()
        except Exception as e:
            print("OWMWeatherMonitor.do_observation() Error: %s/%s" % (type(e), str(e)))

    def icon_path(self, icon_name=None):
        image_path = None
        with self._weather_lock:
            if icon_name is None:
                icon_name = self._weather["iconName"]
            if icon_name is not None:
                image_path = os.path.join(OWM_ICONS_DIR, f"{self._weather['iconName']}.png")
            return image_path

    def do_forecast(self):
        log(self.args, "retrieving forecast")
        dt_now = datetime.datetime.now()
        dt_now = dt_now.replace(hour=12, minute=0, second=0)
        mgr = self.service.weather_manager()
        fc_3h = mgr.three_hours_forecast(self.my_config.get()["owm_weather"]["place"]).get_forecast()
        days = [dict(iconName="", tempMax=None, tempMin=None, timestamp=0, weatherCodes={}) for _ in range(8)]
        for fc_slice in fc_3h:
            time_from = fc_slice.get_reference_time()
            dt = datetime.datetime.utcfromtimestamp(time_from)
            dt = dt.replace(hour=12, minute=0, second=0)
            day_no = int((dt.timestamp() - dt_now.timestamp()) / 86400)
            if day_no < 0 or day_no >= len(days):
                continue
            this_day = days[day_no]
            temp = fc_slice.get_temperature(unit="celsius")
            this_day["timestamp"] = int(dt.timestamp())
            if "temp_max" in temp:
                if this_day["tempMax"] is None:
                    this_day["tempMax"] = temp["temp_max"]
                if temp["temp_max"] > this_day["tempMax"]:
                    this_day["tempMax"] = temp["temp_max"]
            if ("temp_min" in temp) and ((this_day["tempMin"] is None) or (temp["temp_min"] < this_day["tempMin"])):
                this_day["tempMin"] = temp["temp_min"]
            icon_name = fc_slice.get_weather_icon_name()
            if icon_name not in this_day["weatherCodes"]:
                this_day["weatherCodes"][icon_name] = 0
            this_day["weatherCodes"][icon_name] += 1
        with self._weather_lock:
            self._weather["forecast"] = [day for day in days if day["timestamp"] != 0]
