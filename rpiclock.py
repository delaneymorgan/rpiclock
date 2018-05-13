#!/usr/bin/python
# coding=utf-8

import sys

argvCopy = sys.argv
sys.argv = sys.argv[:1]

import argparse
import configparser
from kivy.app import App
from kivy.uix.image import Image as Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.core.window import Window

sys.argv = argvCopy

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
kDegreeSign = u"\u00b0"
kConfigFilename = "config.ini"
kOWMIconsDir = "owm_icons"
kBOMIconsDir = "bom_icons"

kMembers_Formats = dict(blink_colon="bool", blink_rate="integer", date='string', date_dom_suffix='bool',
                        display='string', large_font="string", large_font_size="integer", small_font="string",
                        small_font_size="integer", text_color='list', time='string', weather='string',
                        window_size='list')
kMembers_Brightness = dict(high='float', high_tom_start='string', low='float', low_tom_start='string')
kMembers_Weather = dict(api='string', check_interval='integer')
kMembers_BOMWeather = dict(forecast_path='string', forecast_place='string', ftp_host='string', ftp_port='integer',
                           observation_url='string', observation_place='string')
kMembers_OWMWeather = dict(api_key='string', place='string', temperature_scale='string')


# =============================================================================


def IsRPi():
    if platform.machine() == "armv7l":
        return True
    return False


# =============================================================================


if IsRPi():
    import rpi_backlight as bl


# =============================================================================


def Log(args, string):
    if args.verbose:
        print(string)
    return


# =============================================================================


def SuffixNum(n):
    """
    Some major juju by python god xsot

    :param n: the number to be suffixed
    :return: the suffixed number
    """
    func = lambda n: `n` + 'tsnrhtdd'[n % 5 * (n % 100 ^ 15 > 4 > n % 10)::4]
    suffixedNum = func(n)
    return suffixedNum


# =============================================================================


class Config():
    config = {}

    configTypeParsers = {
        'list': lambda self, settings, section, member: eval(settings.get(section, member)),
        'string': lambda self, settings, section, member: settings.get(section, member),
        'integer': lambda self, settings, section, member: settings.getint(section, member),
        'bool': lambda self, settings, section, member: settings.getboolean(section, member),
        'float': lambda self, settings, section, member: settings.getfloat(section, member),
    }

    def __init__(self, args, filename="config.ini"):
        self.filename = filename
        settings = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        settings.read(kConfigFilename)
        self.config["formats"] = self.loadSection(settings, "formats", kMembers_Formats)
        self.config["brightness"] = self.loadSection(settings, "brightness", kMembers_Brightness)
        self.config["weather"] = self.loadSection(settings, "weather", kMembers_Weather)
        self.config["bom_weather"] = self.loadSection(settings, "bom_weather", kMembers_BOMWeather)
        self.config["owm_weather"] = self.loadSection(settings, "owm_weather", kMembers_OWMWeather)
        return

    def parseConfigEntry(self, settings, section, member, memberType):
        return self.configTypeParsers[memberType](self, settings, section, member)

    def loadSection(self, settings, section, sectionMembers):
        redis = {}
        for member in sectionMembers:
            redis[member] = self.parseConfigEntry(settings, section, member, sectionMembers[member])
        return redis

    def get(self):
        return self.config


# =============================================================================


# noinspection PyTypeChecker
class BrightnessMonitor(threading.Thread):
    kMaxBrightness = 255
    kMinBrightness = 0

    def __init__(self, args, myConfig):
        super(BrightnessMonitor, self).__init__()
        self.args = args
        self.myConfig = myConfig
        self.highMoDStart = self.ToDToMoD(self.myConfig.get()["brightness"]["high_tom_start"])
        self.lowMoDStart = self.ToDToMoD(self.myConfig.get()["brightness"]["low_tom_start"])
        self.running = True
        return

    def ToDToMoD(self, tod):
        tod = tod.split(":")
        mod = (int(tod[0]) * 60) + int(tod[1])
        return mod

    def stop(self):
        self.running = False

    def checkBrightness(self):
        # TODO: maybe use weather observation to base dimming on sunrise/sunset
        timeNow = time.time()
        localTime = time.localtime(timeNow)
        minOfDay = (60 * localTime.tm_hour) + localTime.tm_min
        if self.highMoDStart < self.lowMoDStart  and minOfDay > self.highMoDStart and minOfDay < self.lowMoDStart:
            brightness = self.myConfig.get()["brightness"]["high"]
        else:
            brightness = self.myConfig.get()["brightness"]["low"]
        Log(self.args, "Setting brightness: %3.1f%%" % brightness)
        realBrightness = (brightness / 100.0) * (self.kMaxBrightness - self.kMinBrightness) + self.kMinBrightness
        if IsRPi():
            bl.set_brightness(realBrightness)
        return

    def run(self):
        while self.running:
            self.checkBrightness()
            time.sleep(1)  # I'd sleep for more, but it holds up quit
        return


# =============================================================================


# noinspection PyTypeChecker
class WeatherMonitor(threading.Thread):
    def __init__(self, args, myConfig):
        super(WeatherMonitor, self).__init__()
        self.args = args
        self.myConfig = myConfig
        self.service = None
        self.lastCheck = 0
        self._weatherLock = threading.Lock()
        self._weather = dict(
            tempNow=None,  # current temperature in Celcius
            tempMin=None,  # forecast minimum temperature in Celcius
            tempMax=None,  # forecast maximum temperature in Celcius
            iconName=None  # current weather icon
        )
        self.running = True
        return

    def weather(self):
        with self._weatherLock:
            return self._weather

    def iconPath(self):
        raise NotImplementedError()

    def doObservation(self):
        raise NotImplementedError()

    def doForecast(self):
        raise NotImplementedError()

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            timeNow = time.time()
            waitRemaining = self.myConfig.get()["weather"]["check_interval"] - (timeNow - self.lastCheck)
            if waitRemaining < 0:
                Log(self.args, "polling weather")
                self.lastCheck = timeNow
                self.doObservation()
                self.doForecast()
            else:
                Log(self.args, "secs until next weather poll: %0.1f secs" % waitRemaining)
                time.sleep(1)  # I'd sleep for more, but it holds up quit
        return


# =============================================================================


# noinspection PyTypeChecker
class OWMWeatherMonitor(WeatherMonitor):
    def __init__(self, args, myConfig):
        super(OWMWeatherMonitor, self).__init__(args, myConfig)
        self.service = pyowm.OWM(myConfig.get()["owm_weather"]["api_key"])
        self.doObservation()
        return

    def doObservation(self):
        Log(self.args, "retrieving observation")
        obs = self.service.weather_at_place(self.myConfig.get()["owm_weather"]["place"])
        scale = self.myConfig.get()["owm_weather"]["temperature_scale"]
        obsWeather = obs.get_weather()
        with self._weatherLock:
            self._weather["tempNow"] = obsWeather.get_temperature(scale)['temp']
            self._weather["iconName"] = obsWeather.get_weather_icon_name()
        return

    def iconPath(self):
        imagePath = None
        with self._weatherLock:
            iconName = self._weather["iconName"]
            if iconName is not None:
                imagePath = os.path.join(kOWMIconsDir, self._weather["iconName"] + ".png")
            return imagePath

    def doForecast(self):
        Log(self.args, "retrieving forecast")
        with self._weatherLock:
            pass
        return


# =============================================================================


# noinspection PyTypeChecker
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

    def __init__(self, args, myConfig):
        super(BOMWeatherMonitor, self).__init__(args, myConfig)
        self.doObservation()
        return

    def doObservation(self):
        Log(self.args, "retrieving observation")
        url = self.myConfig.get()["bom_weather"]["observation_url"]
        place = self.myConfig.get()["bom_weather"]["observation_place"]
        observation_url = url % (place, place)
        resp = requests.get(observation_url)
        if resp:
            # observations typically contains many (hundreds, perhaps),
            # lets just print out the current observation.
            Log(self.args, "Current observation data:")
            content = resp.content
            content = json.loads(content)
            observation = content["observations"]["data"][0]
            Log(self.args, "tempNow: %s" % observation["air_temp"])
            with self._weatherLock:
                self._weather["tempNow"] = observation["air_temp"]
        else:
            Log(self.args, "No observations retrieved")
        return

    def iconPath(self):
        imagePath = None
        with self._weatherLock:
            if self._weather["iconName"] is not None:
                iconName = self.kBOMIcons[self._weather["iconName"]]
                imagePath = os.path.join(kBOMIconsDir, iconName + ".png")
        return imagePath

    def addLines(self, lines):
        return

    def doForecast(self):
        Log(self.args, "retrieving forecast")
        ftp = FTP(self.myConfig.get()["bom_weather"]["ftp_host"])
        ftp.login()
        fcPath = self.myConfig.get()["bom_weather"]["forecast_path"] % \
                 self.myConfig.get()["bom_weather"]["forecast_place"]
        outStr = StringIO.StringIO()  # Use a string like a file.
        ftp.retrlines('RETR ' + fcPath, outStr.write)
        elements = untangle.parse(outStr.getvalue())
        outStr.close()
        area = elements.product.forecast.area[2]
        forecast = area.forecast_period[0]
        fcElements = forecast.element
        # NOTE: sometimes this is a single dict, other times it's a list of dicts.
        if "type" in fcElements:
            if fcElements["type"] == "forecast_icon_code":
                Log(self.args, "iconName: %s" % fcElements.cdata)
                with self._weatherLock:
                    self._weather["iconName"] = fcElements.cdata
            elif fcElements["type"] == "air_temperature_maximum":
                Log(self.args, "tempMax: %s" % fcElements.cdata)
                with self._weatherLock:
                    self._weather["tempMax"] = float(fcElements.cdata)
            elif fcElements["type"] == "air_temperature_minimum":
                Log(self.args, "tempMin: %s" % fcElements.cdata)
                with self._weatherLock:
                    self._weather["tempMin"] = float(fcElements.cdata)
        else:
            for thisElement in fcElements:
                if thisElement["type"] == "forecast_icon_code":
                    Log(self.args, "iconName: %s" % thisElement.cdata)
                    with self._weatherLock:
                        self._weather["iconName"] = str(thisElement.cdata)
                elif thisElement["type"] == "air_temperature_maximum":
                    Log(self.args, "tempMax: %s" % thisElement.cdata)
                    with self._weatherLock:
                        self._weather["tempMax"] = float(thisElement.cdata)
                elif thisElement["type"] == "air_temperature_minimum":
                    Log(self.args, "tempMin: %s" % thisElement.cdata)
                    with self._weatherLock:
                        self._weather["tempMin"] = float(thisElement.cdata)
        return


# =============================================================================


class TimeWidget(Label):
    def __init__(self, myConfig, size_hint=(None, None)):
        super(TimeWidget, self).__init__(text="00:00", size_hint=size_hint)
        self.myConfig = myConfig
        if myConfig.get()["formats"]["large_font"]:
            self.font_name = myConfig.get()["formats"]["large_font"]
        self.font_size = myConfig.get()["formats"]["large_font_size"]
        self.color = myConfig.get()["formats"]["text_color"]
        self.bold = True
        self.lastTime = ""
        Clock.schedule_interval(self.update, 1.0 / 2.0)  # 1/2 second resolution for 1 second accuracy
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        timeNow = time.time()
        blankColon = False
        blinkRate = self.myConfig.get()["formats"]["blink_rate"]
        if self.myConfig.get()["formats"]["blink_colon"]:
            if (int(timeNow) % (2 * blinkRate)) < blinkRate:
                blankColon = True
        localTime = time.localtime(timeNow)
        timeFormat = self.myConfig.get()["formats"]["time"]
        if blankColon:
            timeFormat = string.replace(timeFormat, ":", " ")
        timeStr = time.strftime(timeFormat, localTime)
        if timeStr != self.lastTime:
            self.text = timeStr
            self.lastTime = timeStr
        return


# =============================================================================


class DateWidget(Label):
    def __init__(self, myConfig):
        super(DateWidget, self).__init__(text="")
        self.myConfig = myConfig
        if myConfig.get()["formats"]["small_font"]:
            self.font_name = myConfig.get()["formats"]["small_font"]
        self.font_size = myConfig.get()["formats"]["small_font_size"]
        self.color = myConfig.get()["formats"]["text_color"]
        self.lastDate = ""
        Clock.schedule_interval(self.update, 1.0 / 2.0)
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        timeNow = time.time()
        localTime = time.localtime(timeNow)
        format = self.myConfig.get()["formats"]["date"]
        if self.myConfig.get()["formats"]["date_dom_suffix"]:
            monthStr = time.strftime("%B", localTime)
            domSuffixed = SuffixNum(localTime.tm_mday)
            dateStr = "%s %s" % (domSuffixed, monthStr)
        else:
            dateStr = time.strftime(format, localTime)
        if dateStr != self.lastDate:
            self.lastDate = dateStr
            self.text = dateStr
        return


# =============================================================================


class WeatherIconWidget(Image):
    def __init__(self, myConfig, weatherMonitor):
        super(WeatherIconWidget, self).__init__()
        self.myConfig = myConfig
        self.weatherMonitor = weatherMonitor
        self.source = "blank.png"
        Clock.schedule_interval(self.update, 5)  # fine for temperature
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        weather = self.weatherMonitor.weather()
        if weather is not None:
            iconPath = self.weatherMonitor.iconPath()
            if iconPath is not None:
                self.source = iconPath
        return


# =============================================================================


class ForecastWidget(Label):
    def __init__(self, myConfig, weatherMonitor):
        super(ForecastWidget, self).__init__()
        self.myConfig = myConfig
        self.weatherMonitor = weatherMonitor
        self.color = myConfig.get()["formats"]["text_color"]
        if myConfig.get()["formats"]["small_font"]:
            self.font_name = myConfig.get()["formats"]["small_font"]
        self.font_size = self.myConfig.get()["formats"]["small_font_size"]
        Clock.schedule_interval(self.update, 5)  # fine for temperature
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        weather = self.weatherMonitor.weather()
        if weather is not None:
            tempMin = weather['tempMin']
            tempMax = weather['tempMax']
            if tempMin is not None and tempMax is not None:
                self.text = "%2.1f%s-%2.1f%s" % (tempMin, kDegreeSign, tempMax, kDegreeSign)
            elif tempMin is None and tempMax is not None:
                self.text = "Max: %2.1f%s" % (tempMax, kDegreeSign)
            elif tempMin is not None and tempMax is None:
                self.text = "Min: %2.1f%s" % (tempMin, kDegreeSign)
        return


# =============================================================================


class TempNowWidget(Label):
    def __init__(self, myConfig, weatherMonitor):
        super(TempNowWidget, self).__init__()
        self.myConfig = myConfig
        self.weatherMonitor = weatherMonitor
        self.color = myConfig.get()["formats"]["text_color"]
        if myConfig.get()["formats"]["small_font"]:
            self.font_name = myConfig.get()["formats"]["small_font"]
        self.font_size = self.myConfig.get()["formats"]["small_font_size"]
        Clock.schedule_interval(self.update, 5)  # fine for temperature
        self.update(0)
        return

    def update(self, dt):
        _ = dt
        weather = self.weatherMonitor.weather()
        if weather is not None:
            tempNow = weather['tempNow']
            if tempNow is not None:
                self.text = "%2.1f%s" % (tempNow, kDegreeSign)
        return


# =============================================================================


class InfoWidget(BoxLayout):
    def __init__(self, myConfig, weatherMonitor):
        super(InfoWidget, self).__init__()
        self.dateWidget = DateWidget(myConfig)
        self.TempNowWidget = TempNowWidget(myConfig, weatherMonitor)
        self.forecastWidget = ForecastWidget(myConfig, weatherMonitor)
        self.iconWidget = WeatherIconWidget(myConfig, weatherMonitor)
        self.add_widget(self.dateWidget)
        self.add_widget(self.TempNowWidget)
        self.add_widget(self.forecastWidget)
        self.add_widget(self.iconWidget)
        return


# =============================================================================


class RPiClockWidget(Widget):
    def __init__(self, myConfig, weatherMonitor):
        super(RPiClockWidget, self).__init__()
        timeWidget = TimeWidget(myConfig, size_hint=(1, .8))
        timeWidget.size_hint_y = .8
        infoWidget = InfoWidget(myConfig, weatherMonitor)
        infoWidget.size_hint_y = .2
        vertLayout = BoxLayout(orientation='vertical', size=Window.size)
        vertLayout.add_widget(timeWidget)
        vertLayout.add_widget(infoWidget)
        self.add_widget(vertLayout)
        return


# =============================================================================


class RPiClockApp(App):
    def __init__(self, args, myConfig):
        super(RPiClockApp, self).__init__()
        self.myConfig = myConfig
        Window.size = myConfig.get()["formats"]["window_size"]
        Window.bind(on_request_close=self.on_request_close)
        Window.bind(on_mouse_down=self.on_request_close)
        Window.bind(on_touch_down=self.on_request_close)
        if myConfig.get()["weather"]["api"] == "owm":
            self.weatherMonitor = OWMWeatherMonitor(args, myConfig)
            self.weatherMonitor.start()
        elif myConfig.get()["weather"]["api"] == "bom":
            self.weatherMonitor = BOMWeatherMonitor(args, myConfig)
            self.weatherMonitor.start()
        self.brightnesssMonitor = BrightnessMonitor(args, myConfig)
        self.brightnesssMonitor.start()
        return

    def on_request_close(self, *args):
        self.weatherMonitor.stop()
        self.brightnesssMonitor.stop()
        # return False		# TODO: this should be enough to end things, but doesn't work
        sys.exit()  # brute force will do it

    def build(self):
        clockWidget = RPiClockWidget(self.myConfig, self.weatherMonitor)
        return clockWidget


# =============================================================================


def argParser():
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
    args = argParser()
    Log(args, "rpiclock start")
    config = Config(args)
    clockApp = RPiClockApp(args, config)
    clockApp.run()
    Log(args, "rpiclock end")
    return


# ===============================================================================================


if __name__ == "__main__":
    main()
