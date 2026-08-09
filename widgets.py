import time

import state
from kivy_compat import Button, Label, Image, BoxLayout, Widget, Clock, Window

from constants import DEGREE_SIGN, BLANK_IMAGE
from utils import suffix_num


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
        Clock.schedule_interval(self.update, 1.0 / 2.0)
        self.update(0)

    def on_request_close(self, *args):
        _ = args
        import state
        state.running_flag = False
        raise SystemExit

    def update(self, dt):
        _ = dt
        import time
        time_now = time.time()
        blank_colon = False
        blink_rate = self.my_config.get()["formats"]["blink_rate"]
        if self.my_config.get()["formats"]["blink_colon"]:
            if (int(time_now) % (2 * blink_rate)) < blink_rate:
                blank_colon = True
        local_time = time.localtime(time_now)
        time_format = self.my_config.get()["formats"]["time"]
        if blank_colon:
            time_format = time_format.replace(":", " ")
        time_str = time.strftime(time_format, local_time)
        if time_str != self.lastTime:
            self.text = time_str
            self.lastTime = time_str


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

    def update(self, dt):
        _ = dt
        import time
        local_time = time.localtime(time.time())
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


class WeatherIconWidget(Image):
    def __init__(self, my_config, weather_monitor):
        super(WeatherIconWidget, self).__init__()
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.source = BLANK_IMAGE
        Clock.schedule_interval(self.update, 5)
        self.update(0)

    def update(self, dt):
        _ = dt
        weather = self.weather_monitor.weather()
        if weather is not None:
            icon_path = self.weather_monitor.icon_path()
            if icon_path is not None:
                self.source = icon_path


class ForecastWidget(Label):
    def __init__(self, my_config, weather_monitor):
        super(ForecastWidget, self).__init__()
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.color = my_config.get()["formats"]["text_color"]
        if my_config.get()["formats"]["small_font"]:
            self.font_name = my_config.get()["formats"]["small_font"]
        self.font_size = self.my_config.get()["formats"]["small_font_size"]
        Clock.schedule_interval(self.update, 5)
        self.update(0)

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
        Clock.schedule_interval(self.update, 5)
        self.show_info()

    def update(self, dt):
        _ = dt
        self.show_info()

    def show_info(self):
        try:
            forecasts = self.weather_monitor.weather()["forecast"]
            forecast = forecasts[self.day_no]
            self.dow_widget.text = time.strftime("%a", time.localtime(forecast["timestamp"]))
            self.temp_widget.text = "%s-%s" % (
                forecast.get("tempMin", "?"),
                forecast.get("tempMax", "?")
            )
            self.icon_widget.source = self.weather_monitor.icon_path(forecast.get("iconName"))
        except Exception:
            self.dow_widget.text = ""
            self.temp_widget.text = ""
            self.icon_widget.source = BLANK_IMAGE


class FiveDayForecastWidget(BoxLayout):
    def __init__(self, my_config, weather_monitor):
        super(FiveDayForecastWidget, self).__init__(orientation='horizontal')
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        for index in range(5):
            self.add_widget(OneDayForecastWidget(my_config, weather_monitor, index))


class TempNowWidget(Label):
    def __init__(self, my_config, weather_monitor):
        super(TempNowWidget, self).__init__()
        self.my_config = my_config
        self.weather_monitor = weather_monitor
        self.color = my_config.get()["formats"]["text_color"]
        if my_config.get()["formats"]["small_font"]:
            self.font_name = my_config.get()["formats"]["small_font"]
        self.font_size = self.my_config.get()["formats"]["small_font_size"]
        Clock.schedule_interval(self.update, 5)
        self.update(0)

    def update(self, dt):
        _ = dt
        weather = self.weather_monitor.weather()
        if weather is not None:
            temp_now = weather['tempNow']
            if temp_now is not None:
                self.text = "%2.1f%s" % (temp_now, DEGREE_SIGN)


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

    def show_forecast(self, *args):
        _ = args
        if not self.showing_five_day:
            self.remove_widget(self.date_widget)
            self.remove_widget(self.temp_now_widget)
            self.remove_widget(self.forecast_widget)
            self.remove_widget(self.icon_widget)
            self.add_widget(self.five_day_widget)
            self.showing_five_day = True
            self.five_day_start = time.time()

    def show_info(self):
        self.remove_widget(self.five_day_widget)
        self.add_widget(self.date_widget)
        self.add_widget(self.temp_now_widget)
        self.add_widget(self.forecast_widget)
        self.add_widget(self.icon_widget)
        self.showing_five_day = False
        self.five_day_start = None

    def update(self, dt):
        _ = dt
        if self.showing_five_day:
            if time.time() - self.five_day_start > self.my_config.get()["formats"]["forecast_time"]:
                self.show_info()


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
