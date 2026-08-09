import sys

# this allows rpiclock to get command-line arguments after kivy has processed its own.
argvCopy = sys.argv
sys.argv = sys.argv[:1]

try:
    from kivy.app import App
    from kivy.uix.button import Button
    from kivy.uix.image import Image as Image
    from kivy.uix.label import Label
    from kivy.uix.widget import Widget
    from kivy.uix.boxlayout import BoxLayout
    from kivy.clock import Clock
    from kivy.core.window import Window
    KIVY_AVAILABLE = True
except ImportError:
    class _KivyFallbackBase(object):
        def __init__(self, *args, **kwargs):
            self.size = kwargs.get("size")
            self.size_hint = kwargs.get("size_hint")
            self.text = kwargs.get("text", "")
            self.source = kwargs.get("source", "")
            self.color = kwargs.get("color")
            self.font_name = kwargs.get("font_name")
            self.font_size = kwargs.get("font_size")
            self.background_color = kwargs.get("background_color")
            self.bold = kwargs.get("bold", False)

        def bind(self, *args, **kwargs):
            return None

        def add_widget(self, *args, **kwargs):
            return None

        def remove_widget(self, *args, **kwargs):
            return None

    class App(_KivyFallbackBase):
        pass

    class Button(_KivyFallbackBase):
        pass

    class Image(_KivyFallbackBase):
        pass

    class Label(_KivyFallbackBase):
        pass

    class Widget(_KivyFallbackBase):
        pass

    class BoxLayout(_KivyFallbackBase):
        pass

    class Clock(object):
        @staticmethod
        def schedule_interval(*args, **kwargs):
            return None

    class Window(object):
        size = (800, 480)
        borderless = False
        fullscreen = False

        @staticmethod
        def bind(*args, **kwargs):
            return None

    KIVY_AVAILABLE = False
finally:
    sys.argv = argvCopy
