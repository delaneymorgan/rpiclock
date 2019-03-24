#!/usr/bin/python
# coding=utf-8

import sys

# this allows rpiclock to get command-line arguments after kivy has processed it's.
argvCopy = sys.argv
sys.argv = sys.argv[:1]

import argparse
import configparser
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.image import Image as Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.core.window import Window

sys.argv = argvCopy

import calendar
import dateutil.parser
import json
import os
import platform
import pyowm
import requests
import string
import sys
import time
import threading
import untangle
from ftplib import FTP
import StringIO

# =============================================================================


__version__ = "0.0.1"
DEGREE_SIGN = u"\u00b0"
CONFIG_FILENAME = "config.ini"
OWM_ICONS_DIR = "owm_icons"
BOM_ICONS_DIR = "bom_icons"

MEMBERS_FORMATS = dict(blink_colon="bool", blink_rate="integer", date='string', date_dom_suffix='bool',
                       display='string', forecast_time="integer", large_font="string", large_font_size="integer",
                       small_font="string", small_font_size="integer", text_color='list', time='string',
                       weather='string', window_size='list')
MEMBERS_BRIGHTNESS = dict(high='float', high_tom_start='string', low='float', low_tom_start='string')
MEMBERS_WEATHER = dict(api='string', check_interval='integer')
MEMBERS_BOM_WEATHER = dict(forecast_path='string', forecast_place='string', ftp_host='string', ftp_port='integer',
                           observation_url='string', observation_place='string')
MEMBERS_OWM_WEATHER = dict(api_key='string', place='string', temperature_scale='string')
BLANK_IMAGE = "blank.png"

gRunning = True

# =============================================================================


def is_rpi():
    if platform.machine() == "armv7l":
        return True
    return False


# =============================================================================


def log(args, string):
    if args.verbose:
        print(string)
    return


# =============================================================================


def suffix_num(num):
    """
    Some major juju by python god xsot

    :param num: the number to be suffixed
    :return: the suffixed number
    """
    def func(n): return repr(n) + 'tsnrhtdd'[n % 5 * (n % 100 ^ 15 > 4 > n % 10)::4]
    suffixed_num = func(num)
    return suffixed_num


# =============================================================================


class Config:
    config = {}

    CONFIG_TYPE_PARSERS = {
        'list': lambda self, settings, section, member: eval(settings.get(section, member)),
        'string': lambda self, settings, section, member: settings.get(section, member),
        'integer': lambda self, settings, section, member: settings.getint(section, member),
        'bool': lambda self, settings, section, member: settings.getboolean(section, member),
        'float': lambda self, settings, section, member: settings.getfloat(section, member),
    }

    def __init__(self, filename="config.ini"):
        self.filename = filename
        settings = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        settings.read(CONFIG_FILENAME)
        self.config["formats"] = self.load_section(settings, "formats", MEMBERS_FORMATS)
        self.config["brightness"] = self.load_section(settings, "brightness", MEMBERS_BRIGHTNESS)
        self.config["weather"] = self.load_section(settings, "weather", MEMBERS_WEATHER)
        self.config["bom_weather"] = self.load_section(settings, "bom_weather", MEMBERS_BOM_WEATHER)
        self.config["owm_weather"] = self.load_section(settings, "owm_weather", MEMBERS_OWM_WEATHER)
        return

    def parse_config_entry(self, settings, section, member, member_type):
        return self.CONFIG_TYPE_PARSERS[member_type](self, settings, section, member)

    def load_section(self, settings, section, section_members):
        redis = {}
        for member in section_members:
            redis[member] = self.parse_config_entry(settings, section, member, section_members[member])
        return redis

    def get(self):
        return self.config


# =============================================================================


# noinspection PyTypeChecker
class BrightnessMonitor(threading.Thread):
    """
    controls display brightness, depending on time of day
    """
    kMaxBrightness = 255        # display's max raw brightness value
    kMinBrightness = 0          # display's min raw brightness value

    def __init__(self, args, my_config):
        super(BrightnessMonitor, self).__init__()
        self.args = args
        self.my_config = my_config
        self.high_mod_start = self.tod_to_mod(self.my_config.get()["brightness"]["high_tom_start"])
        self.low_mod_start = self.tod_to_mod(self.my_config.get()["brightness"]["low_tom_start"])
        return

    @staticmethod
    def tod_to_mod(tod):
        """
        Time Of Day -> Minute Of Day
        :param tod: the time of day in hh:mm format
        :return: the #minutes past midnight
        """
        tod = tod.split(":")
        mod = (int(tod[0]) * 60) + int(tod[1])
        return mod

    def set_backlight(self, raw_value):
        """
        set the display's backlight brightness
        :param raw_value: 0-255
        :return:
        """
        raw_value = abs(int(raw_value)) % 256  # limit to integers 0-255
        if platform.machine() == "armv7l":
            # noinspection PyUnresolvedReferences
            import rpi_backlight as bl
            bl.set_brightness(raw_value)
            log(self.args, "set brightness: rawValue: %d" % raw_value)
        return

    def check_brightness(self):
        # TODO: maybe use weather observation to base dimming on sunrise/sunset
        time_now = time.time()
        local_time = time.localtime(time_now)
        min_of_day = (60 * local_time.tm_hour) + local_time.tm_min
        if self.high_mod_start < self.low_mod_start and self.high_mod_start < min_of_day < self.low_mod_start:
            brightness = self.my_config.get()["brightness"]["high"]
        else:
            brightness = self.my_config.get()["brightness"]["low"]
        log(self.args, "Setting brightness: %3.1f%%" % brightness)
        # convert brightness % to raw brightness setting
        real_brightness = (brightness / 100.0) * (self.kMaxBrightness - self.kMinBrightness) + self.kMinBrightness
        self.set_backlight(real_brightness)
        return

    def run(self):
        while gRunning:
            self.check_brightness()
            time.sleep(1)  # I'd sleep for more, but it holds up quit
        return


# =============================================================================


# noinspection PyTypeChecker
class WeatherMonitor(threading.Thread):
    """
    base abstract class for monitoring weather
    """
    def __init__(self, args, my_config):
        super(WeatherMonitor, self).__init__()
        self.args = args
        self.my_config = my_config
        self.service = None
        self.last_check = 0
        self._weather_lock = threading.Lock()
        self._weather = dict(
            tempNow=None,   # current temperature in Celcius
            tempMin=None,   # forecast minimum temperature in Celcius
            tempMax=None,   # forecast maximum temperature in Celcius
            iconName=None,  # current weather icon
            forecast=[]     # the five-day forecast
        )
        return

    def weather(self):
        """
        returns a copy of the weather structure
        :return: weather copy
        """
        with self._weather_lock:
            return dict(self._weather)

    def icon_path(self):
        raise NotImplementedError()

    def do_observation(self):
        raise NotImplementedError()

    def do_forecast(self):
        raise NotImplementedError()

    def run(self):
        while gRunning:
            time_now = time.time()
            wait_remaining = self.my_config.get()["weather"]["check_interval"] - (time_now - self.last_check)
            if wait_remaining < 0:
                log(self.args, "polling weather")
                self.last_check = time_now
                self.do_observation()
                self.do_forecast()
            else:
                log(self.args, "secs until next weather poll: %0.1f secs" % wait_remaining)
                time.sleep(1)  # I'd sleep for more, but it holds up quit
        return


# =============================================================================


# noinspection PyTypeChecker
class OWMWeatherMonitor(WeatherMonitor):
    """
    class for monitoring weather via Open Weather Map API
    """
    def __init__(self, args, my_config):
        super(OWMWeatherMonitor, self).__init__(args, my_config)
        try:
            self.service = pyowm.OWM(my_config.get()["owm_weather"]["api_key"])
            self.do_observation()
        except Exception as e:
            print("OWMWeatherMonitor.__init__() Error: %s/%s" % (type(e), str(e)))
        return

    def do_observation(self):
        log(self.args, "retrieving observation")
        try:
            obs = self.service.weather_at_place(self.my_config.get()["owm_weather"]["place"])
            scale = self.my_config.get()["owm_weather"]["temperature_scale"]
            obs_weather = obs.get_weather()
            with self._weather_lock:
                self._weather["tempNow"] = obs_weather.get_temperature(scale)['temp']
                self._weather["iconName"] = obs_weather.get_weather_icon_name()
        except Exception as e:
            print("OWMWeatherMonitor.doObservation() Error: %s/%s" % (type(e), str(e)))
        return

    def icon_path(self, icon_name=None):
        image_path = None
        with self._weather_lock:
            if icon_name is None:
                icon_name = self._weather["iconName"]
            if icon_name is not None:
                image_path = os.path.join(OWM_ICONS_DIR, self._weather["iconName"] + ".png")
            return image_path

    def do_forecast(self):
        log(self.args, "retrieving forecast")
        with self._weather_lock:
            # TODO: get an API key with forecast rights and do this
            pass
        return


# =============================================================================


# noinspection PyTypeChecker
class BOMWeatherMonitor(WeatherMonitor):
    """
    class for monitoring Australian weather via Bureau of Meteorology
    """
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
        return

    def do_observation(self):
        log(self.args, "retrieving observation")
        url = self.my_config.get()["bom_weather"]["observation_url"]
        place = self.my_config.get()["bom_weather"]["observation_place"]
        observation_url = url % (place, place)
        try:
            resp = requests.get(observation_url)
            if resp:
                # observations typically contains many (hundreds, perhaps),
                # lets just print out the current observation.
                log(self.args, "Current observation data:")
                content = resp.content
                content = json.loads(content)
                observation = content["observations"]["data"][0]
                log(self.args, "tempNow: %s" % observation["air_temp"])
                with self._weather_lock:
                    self._weather["tempNow"] = observation["air_temp"]
            else:
                log(self.args, "No observations retrieved")
        except Exception as e:
            print("BOMWeatherMonitor.doObservation() Error: %s/%s" % (type(e), str(e)))
        return

    def icon_path(self, icon_name=None):
        image_path = None
        with self._weather_lock:
            if self._weather["iconName"] is not None:
                if icon_name is None:
                    icon_name = self._weather["iconName"]
                icon_name = self.kBOMIcons[icon_name]
                image_path = os.path.join(BOM_ICONS_DIR, icon_name + ".png")
        return image_path

    def add_lines(self, lines):
        return

    def decode_elements(self, forecast_elements, timestamp=None):
        info = {}
        # NOTE: sometimes this is a single dict, other times it's a list of dicts.
        if "type" in forecast_elements:
            # it's a single dict
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
            # it's an array of dicts
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
            d = dateutil.parser.parse(timestamp)
            this_time = time.mktime(d.timetuple()) + d.microsecond / 1E6
            info["timestamp"] = this_time
        return info

    def do_forecast(self):
        log(self.args, "retrieving forecast")
        try:
            ftp = FTP(self.my_config.get()["bom_weather"]["ftp_host"])
            ftp.login()
            fc_path = self.my_config.get()["bom_weather"]["forecast_path"] % \
                      self.my_config.get()["bom_weather"]["forecast_place"]
            out_str = StringIO.StringIO()  # Use a string like a file.
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
                with self._weather_lock:
                    self._weather["forecast"].append(info)
        except Exception as e:
            print("BOMWeatherMonitor.doForecast() Error: %s/%s" % (type(e), str(e)))
        return


# =============================================================================


class TimeWidget(Button):
    def __init__(self, my_config, size_hint=(None, None)):
        super(TimeWidget, self).__init__(text="00:00", size_hint=size_hint)
        self.my_config = my_config
        if my_config.get()["formats"]["large_font"]:
            self.font_name = my_config.get()["formats"]["large_font"]
        self.font_size = my_config.get()["formats"]["large_font_size"]
        self.color = my_config.get()["formats"]["text_color"]
        self.background_color = [0, 0, 0, 0]
        self.bold = True
        self.lastTime = ""
        self.bind(on_press=self.on_request_close)
        # self.bind(on_touch_down=self.on_request_close)
        Clock.schedule_interval(self.update, 1.0 / 2.0)  # 1/2 second resolution for 1 second accuracy
        self.update(0)
        return

    # noinspection PyUnreachableCode
    # noinspection PyMethodMayBeStatic
    def on_request_close(self, *args):
        _ = args
        global gRunning
        gRunning = False
        # return False		# TODO: this should be enough to end things, but doesn't work
        sys.exit()  # brute force will do it
        return

    def update(self, dt):
        _ = dt
        time_now = time.time()

        # blink the colon if required
        blank_colon = False
        blink_rate = self.my_config.get()["formats"]["blink_rate"]
        if self.my_config.get()["formats"]["blink_colon"]:
            if (int(time_now) % (2 * blink_rate)) < blink_rate:
                blank_colon = True

        local_time = time.localtime(time_now)
        time_format = self.my_config.get()["formats"]["time"]
        if blank_colon:
            time_format = string.replace(time_format, ":", " ")
        time_str = time.strftime(time_format, local_time)
        if time_str != self.lastTime:
            # only update on change (save some CPU maybe?)
            self.text = time_str
            self.lastTime = time_str
        return


# =============================================================================


class DateWidget(Label):
    def __init__(self, my_config):
        super(DateWidget, self).__init__(text="")
        self.my_config = my_config
        if my_config.get()["formats"]["small_font"]:
            self.font_name = my_config.get()["formats"]["small_font"]
        self.font_size = my_config.get()["formats"]["small_font_size"]
        self.color = my_config.get()["formats"]["text_color"]
        self.last_date = ""
        Clock.schedule_interval(self.update, 1.0 / 2.0)
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        time_now = time.time()
        local_time = time.localtime(time_now)
        fmt = self.my_config.get()["formats"]["date"]
        if self.my_config.get()["formats"]["date_dom_suffix"]:
            month_str = time.strftime("%B", local_time)
            dom_suffixed = suffix_num(local_time.tm_mday)
            date_str = "%s %s" % (dom_suffixed, month_str)
        else:
            date_str = time.strftime(fmt, local_time)
        if date_str != self.last_date:
            self.last_date = date_str
            self.text = date_str
        return


# =============================================================================


class WeatherIconWidget(Image):
    def __init__(self, my_config, weather_monitor):
        super(WeatherIconWidget, self).__init__()
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.source = BLANK_IMAGE
        Clock.schedule_interval(self.update, 5)  # fine for temperature
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        weather = self.weather_monitor.weather()
        if weather is not None:
            icon_path = self.weather_monitor.icon_path()
            if icon_path is not None:
                self.source = icon_path
        return


# =============================================================================


class ForecastWidget(Label):
    def __init__(self, my_config, weather_monitor):
        super(ForecastWidget, self).__init__()
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.color = my_config.get()["formats"]["text_color"]
        if my_config.get()["formats"]["small_font"]:
            self.font_name = my_config.get()["formats"]["small_font"]
        self.font_size = self.my_config.get()["formats"]["small_font_size"]
        Clock.schedule_interval(self.update, 5)  # fine for temperature
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        weather = self.weather_monitor.weather()
        if weather is not None:
            temp_min = weather['tempMin']
            temp_max = weather['tempMax']
            if temp_min is not None and temp_max is not None:
                self.text = "%2.1f%s-%2.1f%s" % (temp_min, DEGREE_SIGN, temp_max, DEGREE_SIGN)
            elif temp_min is None and temp_max is not None:
                self.text = "Max: %2.1f%s" % (temp_max, DEGREE_SIGN)
            elif temp_min is not None and temp_max is None:
                self.text = "Min: %2.1f%s" % (temp_min, DEGREE_SIGN)
        return


# =============================================================================


class OneDayForecastWidget(BoxLayout):
    def __init__(self, my_config, weather_monitor, day_no):
        super(OneDayForecastWidget, self).__init__(orientation='vertical')
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.day_no = day_no
        self.dow_widget = Label()
        self.dow_widget.color = my_config.get()["formats"]["text_color"]
        if my_config.get()["formats"]["small_font"]:
            self.dow_widget.font_name = my_config.get()["formats"]["small_font"]
        self.dow_widget.font_size = self.my_config.get()["formats"]["small_font_size"]
        self.temp_widget = Label()
        self.temp_widget.color = my_config.get()["formats"]["text_color"]
        if my_config.get()["formats"]["small_font"]:
            self.temp_widget.font_name = my_config.get()["formats"]["small_font"]
        self.temp_widget.font_size = self.my_config.get()["formats"]["small_font_size"]
        self.icon_widget = Image()
        self.icon_widget.source = BLANK_IMAGE
        self.add_widget(self.dow_widget)
        self.add_widget(self.icon_widget)
        self.add_widget(self.temp_widget)
        Clock.schedule_interval(self.update, 5)  # fine for temperature
        self.show_info()
        return

    def update(self, dt):
        _ = dt
        self.show_info()
        return

    def show_info(self):
        try:
            forecasts = self.weather_monitor.weather()["forecast"]
            forecast = forecasts[self.day_no]
            if any(forecast):
                if "timestamp" in forecast:
                    time_now = time.localtime(forecast['timestamp'])
                    dow_name = calendar.day_abbr[time_now.tm_wday]
                    self.dow_widget.text = dow_name
                if "tempMax" in forecast:
                    temp = forecast['tempMax']
                    self.temp_widget.text = "%2.1f%s" % (temp, DEGREE_SIGN)
                if "iconName" in forecast:
                    icon_path = self.weather_monitor.icon_path(forecast["iconName"])
                    if icon_path is not None:
                        self.icon_widget.source = icon_path
            else:
                # otherwise wipe any lingering info
                self.dow_widget.text = ""
                self.icon_widget.source = BLANK_IMAGE
                self.temp_widget.text = ""
        except IndexError:
            # there is no forecast for this day
            pass
        return


# =============================================================================


class FiveDayForecastWidget(BoxLayout):
    def __init__(self, my_config, weather_monitor):
        super(FiveDayForecastWidget, self).__init__()
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.days = []
        for dayNo in range(0, 5):
            new_day = OneDayForecastWidget(my_config, weather_monitor, dayNo)
            self.days.append(new_day)
            self.add_widget(new_day)
        return


# =============================================================================


class TempNowWidget(Label):
    def __init__(self, my_config, weather_monitor):
        super(TempNowWidget, self).__init__()
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.color = my_config.get()["formats"]["text_color"]
        if my_config.get()["formats"]["small_font"]:
            self.font_name = my_config.get()["formats"]["small_font"]
        self.font_size = self.my_config.get()["formats"]["small_font_size"]
        Clock.schedule_interval(self.update, 5)  # fine for temperature
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        weather = self.weather_monitor.weather()
        if weather is not None:
            temp_now = weather['tempNow']
            if temp_now is not None:
                self.text = "%2.1f%s" % (temp_now, DEGREE_SIGN)
        return


# =============================================================================


class InfoWidget(BoxLayout):
    def __init__(self, my_config, weather_monitor):
        super(InfoWidget, self).__init__()
        self.showing_five_day = None
        self.five_day_start = None
        self.my_config = my_config
        self.date_widget = DateWidget(my_config)
        self.temp_now_widget = TempNowWidget(my_config, weather_monitor)
        self.forecast_widget = ForecastWidget(my_config, weather_monitor)
        self.icon_widget = WeatherIconWidget(my_config, weather_monitor)
        self.five_day_widget = FiveDayForecastWidget(my_config, weather_monitor)
        self.bind(on_touch_down=self.show_forecast)
        Clock.schedule_interval(self.update, 0.5)
        self.show_info()
        return

    def show_forecast(self, *args):
        """
        momentarily show 5-day forecast
        :return:
        """
        _ = args
        if not self.showing_five_day:
            self.remove_widget(self.date_widget)
            self.remove_widget(self.temp_now_widget)
            self.remove_widget(self.forecast_widget)
            self.remove_widget(self.icon_widget)
            self.add_widget(self.five_day_widget)
            self.showing_five_day = True
            self.five_day_start = time.time()
        return

    def show_info(self):
        self.remove_widget(self.five_day_widget)
        self.add_widget(self.date_widget)
        self.add_widget(self.temp_now_widget)
        self.add_widget(self.forecast_widget)
        self.add_widget(self.icon_widget)
        self.showing_five_day = False
        self.five_day_start = None
        return

    def update(self, dt):
        _ = dt
        if self.showing_five_day:
            # turn off momentary five-day forecast display
            time_now = time.time()
            duration = time_now - self.five_day_start
            if duration > self.my_config.get()["formats"]["forecast_time"]:
                self.show_info()
        return


# =============================================================================


class RPiClockWidget(Widget):
    def __init__(self, my_config, weather_monitor):
        super(RPiClockWidget, self).__init__()
        time_widget = TimeWidget(my_config, size_hint=(1, .8))
        time_widget.size_hint_y = .8
        info_widget = InfoWidget(my_config, weather_monitor)
        info_widget.size_hint_y = .2
        vert_layout = BoxLayout(orientation='vertical', size=Window.size)
        vert_layout.add_widget(time_widget)
        vert_layout.add_widget(info_widget)
        self.add_widget(vert_layout)
        return


# =============================================================================


class RPiClockApp(App):
    def __init__(self, args, my_config):
        super(RPiClockApp, self).__init__()
        self.myConfig = my_config
        Window.size = my_config.get()["formats"]["window_size"]
        Window.bind(on_request_close=self.on_request_close)
        if my_config.get()["weather"]["api"] == "owm":
            self.weatherMonitor = OWMWeatherMonitor(args, my_config)
            self.weatherMonitor.start()
        elif my_config.get()["weather"]["api"] == "bom":
            self.weatherMonitor = BOMWeatherMonitor(args, my_config)
            self.weatherMonitor.start()
        self.brightnesssMonitor = BrightnessMonitor(args, my_config)
        self.brightnesssMonitor.start()
        return

    # noinspection PyMethodMayBeStatic
    def on_request_close(self, *args):
        _ = args
        global gRunning
        gRunning = False
        # return False		# TODO: this should be enough to end things, but doesn't work
        sys.exit()  # brute force will do it

    def build(self):
        clock_widget = RPiClockWidget(self.myConfig, self.weatherMonitor)
        return clock_widget


# =============================================================================


def arg_parser():
    """
    parse arguments
    :return: the parsed arguments
    """
    parser = argparse.ArgumentParser(description='rpiclock - time/date/weather display appliance.')
    parser.add_argument("-v", "--verbose", help="verbose mode", action="store_true")
    parser.add_argument("-d", "--diagnostic", help="diagnostic mode (includes verbose)", action="store_true")
    parser.add_argument("--version", action="version", version='%(prog)s {version}'.format(version=__version__))
    args = parser.parse_args()
    return args


# ===============================================================================================


def main():
    args = arg_parser()
    log(args, "rpiclock start")
    config = Config()
    clock_app = RPiClockApp(args, config)
    clock_app.run()
    log(args, "rpiclock end")
    return


# ===============================================================================================


if __name__ == "__main__":
    main()
