from kivy_compat import App, Window

from monitors import BOMWeatherMonitor, BrightnessMonitor, OWMWeatherMonitor
from widgets import RPiClockWidget
import state


class ConsoleClock(object):
    def __init__(self, args, my_config, weather_monitor):
        self.args = args
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.last_display = None

    def format_weather(self):
        if self.weather_monitor is None:
            return ""
        weather = self.weather_monitor.weather()
        temp_now = weather.get("tempNow")
        temp_min = weather.get("tempMin")
        temp_max = weather.get("tempMax")
        parts = []
        if temp_now is not None:
            parts.append("temp=%2.1f%s" % (temp_now, "\u00b0"))
        if temp_min is not None and temp_max is not None:
            parts.append("range=%2.1f%s-%2.1f%s" % (temp_min, "\u00b0", temp_max, "\u00b0"))
        elif temp_max is not None:
            parts.append("max=%2.1f%s" % (temp_max, "\u00b0"))
        elif temp_min is not None:
            parts.append("min=%2.1f%s" % (temp_min, "\u00b0"))
        return " | ".join(parts)

    def render(self):
        import sys
        import time

        time_now = time.localtime(time.time())
        time_str = time.strftime(self.my_config.get()["formats"]["time"], time_now)
        date_str = time.strftime(self.my_config.get()["formats"]["date"], time_now)
        display = "\n".join([time_str, date_str, self.format_weather()])
        if display != self.last_display:
            sys.stdout.write("\033[2J\033[H")
            print(display)
            sys.stdout.flush()
            self.last_display = display

    def run(self):
        import time
        while state.running_flag:
            self.render()
            time.sleep(1)


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

    def on_request_close(self, *args):
        _ = args
        state.running_flag = False
        state.stop_event.set()
        raise SystemExit

    def build(self):
        Window.borderless = True
        clock_widget = RPiClockWidget(self.myConfig, self.weatherMonitor)
        return clock_widget
