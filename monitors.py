import datetime
import io
import json
import os
import platform
import re
import time
import threading

import state

try:
    import pyowm
except ImportError:  # pragma: no cover - optional dependency
    pyowm = None

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None

try:
    import untangle
except ImportError:  # pragma: no cover - optional dependency
    untangle = None

try:
    from dateutil import parser as du_parser
except ImportError:  # pragma: no cover - optional dependency
    du_parser = None

from ftplib import FTP
from constants import BOM_ICONS_DIR, OWM_ICONS_DIR
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


class BOMWeatherMonitor(WeatherMonitor):
    kBOMIcons = {
        '1': "sunny",
        '2': "clear",
        '3': "partly-cloudy",
        '3n': "partly-cloudy-night",
        '4': "cloudy",
        '6': "haze",
        '6n': "haze-night",
        '8': "light-rain",
        '9': "wind",
        '10': "fog",
        '10n': "fog-night",
        '11': "showers",
        '11n': "showers-night",
        '12': "rain",
        '13': "dust",
        '14': "frost",
        '15': "snow",
        '16': "storm",
        '17': "light-showers",
        '17n': "light-showers-night",
        '18': "heavy-showers",
        '19': "tropicalcyclone"
    }

    def __init__(self, args, my_config):
        super(BOMWeatherMonitor, self).__init__(args, my_config)
        self.do_observation()
        self.digit_filter = re.compile(r'[^\d]+')

    def do_observation(self):
        log(self.args, "retrieving observation")
        if requests is None:
            return
        url = self.my_config.get()["bom_weather"]["observation_url"]
        place = self.my_config.get()["bom_weather"]["observation_place"]
        observation_url = url % (place, place)
        try:
            resp = requests.get(observation_url, timeout=10)
            if resp.ok:
                log(self.args, "Current observation data:")
                content = json.loads(resp.content)
                observation = content["observations"]["data"][0]
                log(self.args, "tempNow: %s" % observation["air_temp"])
                with self._weather_lock:
                    self._weather["tempNow"] = observation["air_temp"]
            else:
                log(self.args, "No observations retrieved")
        except Exception as e:
            print("BOMWeatherMonitor.do_observation() Error: %s/%s" % (type(e), str(e)))

    def icon_path(self, icon_name=None):
        image_path = None
        with self._weather_lock:
            try:
                if self._weather["iconName"] is not None:
                    if icon_name is None:
                        icon_name = self._weather["iconName"]
                        icon_name = self.digit_filter.sub('', icon_name)
                    icon_name = self.kBOMIcons[icon_name]
                    image_path = os.path.join(BOM_ICONS_DIR, icon_name + ".png")
            except KeyError:
                log(self.args, "invalid icon name: %s" % self._weather["iconName"])
        return image_path

    def add_lines(self, lines):
        return

    def decode_elements(self, forecast_elements, timestamp=None):
        info = {}
        if "type" in forecast_elements:
            if forecast_elements["type"] == "forecast_icon_code":
                log(self.args, "iconName: %s" % forecast_elements.cdata)
                info["iconName"] = forecast_elements.cdata
            elif forecast_elements["type"] == "air_temperature_maximum":
                log(self.args, "tempMax: %s" % forecast_elements.cdata)
                info["tempMax"] = float(forecast_elements.cdata)
            elif forecast_elements["type"] == "air_temperature_minimum":
                log(self.args, "tempMin: %s" % forecast_elements.cdata)
                info["tempMin"] = float(forecast_elements.cdata)
        else:
            for thisElement in forecast_elements:
                if thisElement["type"] == "forecast_icon_code":
                    log(self.args, "iconName: %s" % thisElement.cdata)
                    info["iconName"] = str(thisElement.cdata)
                elif thisElement["type"] == "air_temperature_maximum":
                    log(self.args, "tempMax: %s" % thisElement.cdata)
                    info["tempMax"] = float(thisElement.cdata)
                elif thisElement["type"] == "air_temperature_minimum":
                    log(self.args, "tempMin: %s" % thisElement.cdata)
                    info["tempMin"] = float(thisElement.cdata)
        if timestamp:
            if du_parser is not None:
                d = du_parser.parse(timestamp)
            else:
                try:
                    d = datetime.datetime.fromisoformat(timestamp)
                except ValueError:
                    d = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
            this_time = time.mktime(d.timetuple()) + d.microsecond / 1E6
            info["timestamp"] = this_time
        return info

    def do_forecast(self):
        log(self.args, "retrieving forecast")
        if untangle is None:
            return
        try:
            weather_config = self.my_config.get()["bom_weather"]
            ftp = FTP(weather_config["ftp_host"], timeout=10)
            ftp.login()
            fc_path = weather_config["forecast_path"] % weather_config["forecast_place"]
            out_str = io.StringIO()
            ftp.retrlines('RETR ' + fc_path, out_str.write)
            elements = untangle.parse(out_str.getvalue())
            out_str.close()
            area = elements.product.forecast.area[2]
            todays_forecast = area.forecast_period[0]
            tfc_elements = todays_forecast.element
            info = self.decode_elements(tfc_elements)
            with self._weather_lock:
                for thisKey in info:
                    self._weather[thisKey] = info[thisKey]
            periods_forecast = area.forecast_period
            with self._weather_lock:
                self._weather["forecast"] = []
            for dayForecast in periods_forecast:
                day_elements = dayForecast.element
                info = self.decode_elements(day_elements, dayForecast["start-time-local"])
                log(self.args, "forecast part: %s" % info)
                with self._weather_lock:
                    self._weather["forecast"].append(info)
        except Exception as e:
            print("BOMWeatherMonitor.do_forecast() Error: %s/%s" % (type(e), str(e)))
