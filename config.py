import ast
import configparser
import os

from constants import (
    CONFIG_FILENAME,
    MEMBERS_FORMATS,
    MEMBERS_BRIGHTNESS,
    MEMBERS_WEATHER,
    MEMBERS_BOM_WEATHER,
    MEMBERS_OWM_WEATHER,
    resource_path,
)


class Config:
    def __init__(self, filename=CONFIG_FILENAME):
        self.filename = filename
        settings = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        settings.read(self.filename)
        self.config = {}
        self.config["formats"] = self.load_section(settings, "formats", MEMBERS_FORMATS)
        self.config["brightness"] = self.load_section(settings, "brightness", MEMBERS_BRIGHTNESS)
        self.config["weather"] = self.load_section(settings, "weather", MEMBERS_WEATHER)
        self.config["bom_weather"] = self.load_section(settings, "bom_weather", MEMBERS_BOM_WEATHER)
        self.config["owm_weather"] = self.load_section(settings, "owm_weather", MEMBERS_OWM_WEATHER)
        self.config["formats"]["large_font"] = self.resolve_font_path(self.config["formats"]["large_font"])
        self.config["formats"]["small_font"] = self.resolve_font_path(self.config["formats"]["small_font"])

    def parse_list(self, value):
        try:
            parsed_value = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            raise ValueError("Invalid list value: %s" % value)
        if isinstance(parsed_value, tuple):
            parsed_value = list(parsed_value)
        if not isinstance(parsed_value, list):
            raise ValueError("Expected a list value: %s" % value)
        return parsed_value

    def parse_config_entry(self, settings, section, member, member_type):
        parser = {
            'list': lambda: self.parse_list(settings.get(section, member)),
            'string': lambda: settings.get(section, member),
            'integer': lambda: settings.getint(section, member),
            'bool': lambda: settings.getboolean(section, member),
            'float': lambda: settings.getfloat(section, member),
        }[member_type]
        return parser()

    def load_section(self, settings, section, section_members):
        result = {}
        for member, member_type in section_members.items():
            result[member] = self.parse_config_entry(settings, section, member, member_type)
        return result

    def resolve_font_path(self, font_name):
        if not font_name:
            return None
        if os.path.isabs(font_name) or os.path.dirname(font_name):
            if os.path.exists(font_name):
                return font_name
            print("Font file %r not found. Falling back to the default font." % font_name)
            return None
        resolved = resource_path(font_name)
        if resolved != font_name and os.path.exists(resolved):
            return resolved
        if os.path.exists(font_name):
            return font_name
        if font_name.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
            print("Font file %r not found. Falling back to the default font." % font_name)
            return None
        return font_name

    def get(self):
        return self.config
