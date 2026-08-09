import datetime
import io
import json
import os
import re
import time
from ftplib import FTP

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

from constants import BOM_ICONS_DIR
from utils import log
from weather_monitor import WeatherMonitor


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
